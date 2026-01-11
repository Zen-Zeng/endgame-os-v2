"""
LangGraph 思考流
构建左脑的核心思考流程
"""
from typing import TypedDict, Annotated, Sequence, Dict, Any, List, Optional
from langgraph.graph import StateGraph, START, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
import operator
import os
import logging
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from functools import partial

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_path)

from app.services.memory.memory_service import MemoryService
from app.services.evolution import get_evolution_service
from app.core.config import SYSTEM_PROMPT_TEMPLATE, ENDGAME_VISION, MemoryConfig
from app.core.prompts import (
    ALIGNMENT_CHECK_PROMPT, BASE_SYSTEM_PROMPT, 
    ANSWER_PRINCIPLES_PROMPT, EVOLUTION_GUIDANCE_PROMPT
)
from app.models.user import PersonaConfig, UserVision

class AgentState(TypedDict):
    """
    Agent 状态定义
    包含消息列表、上下文信息、H3 状态、对齐分、人格配置和用户愿景
    """
    user_id: str
    messages: Annotated[Sequence[BaseMessage], operator.add]
    context: str
    strategy_context: str # 新增：策略上下文
    current_date: str  # 新增：当前系统时间
    h3_state: Dict[str, int]
    alignment_score: float
    next_step: str
    persona: PersonaConfig
    vision: Optional[UserVision]

def retrieve_memory_node(state: AgentState, memory_service: MemoryService) -> AgentState:
    """
    记忆检索节点
    从向量库和知识图谱检索相关记忆
    """
    last_message = state["messages"][-1].content
    user_id = state.get("user_id", "default_user")
    current_date = state.get("current_date", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    logger.info(f"正在为用户 {user_id} 检索记忆: {last_message[:50]}...")
    
    context = state.get("context", "")
    context += f"\n[当前系统时间]：{current_date}\n"
    
    # 1. 检索语义记忆 (向量库)
    query_vector = memory_service.neural_processor.embed_batch([last_message])[0]
    
    user_memories = memory_service.vector_store.similarity_search(
        query_vector=query_vector,
        user_id=user_id,
        n_results=10
    )
    
    if user_memories:
        # 尝试按时间戳排序，使最近的记忆更靠前（如果元数据中有 timestamp）
        def get_timestamp(m):
            ts = m.get('metadata', {}).get('timestamp') or m.get('metadata', {}).get('created_at', '1970-01-01')
            return ts
        
        sorted_memories = sorted(user_memories, key=get_timestamp, reverse=True)
        
        memory_text = "\n[从历史记录检索到的相关背景]：\n"
        for m in sorted_memories:
            content = m.get('content', '')
            ts = m.get('metadata', {}).get('timestamp') or m.get('metadata', {}).get('created_at', '')
            time_str = f" ({ts[:10]})" if ts else ""
            memory_text += f"- {content}{time_str}\n"
        context += memory_text
    
    # 2. 检索结构化记忆 (知识图谱)
    graph_keywords = MemoryConfig.GRAPH_SEARCH_KEYWORDS
    if any(keyword in last_message for keyword in graph_keywords) or len(last_message) > 2:
        graph_data = memory_service.graph_store.get_all_graph_data(user_id=user_id)
        nodes = graph_data.get("nodes", [])
        
        # 提取不同类型的实体及其内容
        def format_node_with_dossier(n):
            label = n['label']
            content = n.get('content', '暂无详情')
            attrs = n.get('attributes', {})
            dossier = attrs.get('dossier', {})
            created_at = n.get('created_at', '')
            
            time_suffix = f" (创建于: {created_at[:10]})" if created_at else ""
            
            if not dossier:
                return f"{label}: {content}{time_suffix}"
            
            # 格式化档案信息
            dossier_lines = []
            for k, v in dossier.items():
                if isinstance(v, list):
                    v_str = ", ".join(v)
                else:
                    v_str = str(v)
                dossier_lines.append(f"  - {k}: {v_str}")
            
            dossier_text = "\n".join(dossier_lines)
            return f"{label}: {content}{time_suffix}\n{dossier_text}"

        projects = [format_node_with_dossier(n) for n in nodes if n.get('type') == 'Project']
        tasks = [format_node_with_dossier(n) for n in nodes if n.get('type') == 'Task']
        goals = [format_node_with_dossier(n) for n in nodes if n.get('type') == 'Goal']
        
        # 针对 Concept 节点，进行深度关键词匹配（兼容旧数据）
        relevant_concepts = []
        for n in nodes:
            if n.get('type') == 'Concept':
                label = n.get('label', '')
                content = n.get('content', '')
                # 如果用户问“项目”，也从概念中寻找可能相关的项目名
                if any(k in label or k in content for k in [last_message] + graph_keywords):
                    relevant_concepts.append(f"{label}{': ' + content if content else ''}")
        
        graph_context = "\n[从记忆图谱检索到的结构化信息]：\n"
        if projects: graph_context += "### 当前项目档案：\n" + "\n".join([f"- {p}" for p in projects[:15]]) + "\n"
        if tasks: graph_context += "### 当前任务清单：\n" + "\n".join([f"- {t}" for t in tasks[:20]]) + "\n"
        if goals: graph_context += "### 战略目标：\n" + "\n".join([f"- {g}" for g in goals[:5]]) + "\n"
        
        if projects or tasks or goals:
            context += graph_context
        elif relevant_concepts:
            context += "\n[检索到相关概念/潜在项目]：\n" + "\n".join([f"- {c}" for c in relevant_concepts[:10]]) + "\n"
    
    return {
        "context": context,
        "next_step": "inject_strategy" # 修改下一步为 inject_strategy
    }

def inject_strategy_node(state: AgentState, memory_service: MemoryService) -> AgentState:
    """
    策略注入节点 (Phase 1)
    检索历史策略并注入上下文
    """
    last_message = state["messages"][-1].content
    logger.info(f"正在进行策略检索: {last_message[:20]}...")
    
    try:
        query_vector = memory_service.neural_processor.embed_batch([last_message])[0]
        strategies = memory_service.vector_store.search_experiences(query_vector, n_results=3)
        
        strategy_context = ""
        if strategies:
            strategy_context = "\n[历史策略经验参考]：\n" + "\n".join([f"- {s}" for s in strategies])
            logger.info(f"检索到 {len(strategies)} 条相关策略")
            
        return {
            "strategy_context": strategy_context,
            "next_step": "check_alignment"
        }
    except Exception as e:
        logger.error(f"策略检索失败: {e}")
        return {
            "strategy_context": "",
            "next_step": "check_alignment"
        }

def check_alignment_node(state: AgentState) -> AgentState:
    """
    目标对齐检查节点
    判断用户意图是否偏离终局愿景
    """
    last_message = state["messages"][-1].content
    logger.info(f"正在进行目标对齐检查: {last_message[:50]}...")
    
    # 获取用户愿景和安全性检查
    vision = state.get("vision")
    if vision:
        if isinstance(vision, dict):
            vision_title = vision.get("title", "5年终局愿景")
            vision_desc = vision.get("description", ENDGAME_VISION)
        else:
            vision_title = getattr(vision, "title", "5年终局愿景")
            vision_desc = getattr(vision, "description", ENDGAME_VISION)
    else:
        vision_title = "5年终局愿景"
        vision_desc = ENDGAME_VISION
    
    # 使用集中管理的 Prompt 模板
    alignment_prompt = ALIGNMENT_CHECK_PROMPT.format(
        vision_title=vision_title,
        vision_desc=vision_desc,
        last_message=last_message
    )
    
    try:
        llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0)
        response = llm.invoke([HumanMessage(content=alignment_prompt)])
        content = response.content
        
        # 简单解析输出
        score = 0.5
        reason = "无法确定对齐度"
        
        for line in content.split("\n"):
            if line.startswith("Score:"):
                try:
                    score = float(line.split(":")[1].strip())
                except: pass
            elif line.startswith("Reason:"):
                reason = line.split(":")[1].strip()
        
        logger.info(f"对齐检查完成: 分数={score}, 理由={reason}")
        
        # 将理由注入上下文，供后续 architect 节点使用
        context = state.get("context", "")
        context += f"\n[目标对齐分析]\n对齐得分: {score}\n分析理由: {reason}\n"
        
        return {
            "alignment_score": score,
            "context": context,
            "next_step": "architect"
        }
    except Exception as e:
        logger.error(f"对齐检查失败: {e}", exc_info=True)
        return {
            "alignment_score": 0.5,
            "next_step": "architect"
        }

def _generate_dynamic_system_prompt(state: AgentState) -> str:
    """根据人格配置和愿景动态生成系统提示词"""
    persona = state.get("persona")
    vision = state.get("vision")
    h3 = state.get("h3_state", {"mind": 5, "body": 5, "spirit": 5, "vocation": 5})
    current_date = state.get("current_date", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    strategy_context = state.get("strategy_context", "")
    
    # 防御性获取属性 (兼容 dict 和 object)
    def get_attr(obj, attr, default=""):
        if obj is None: return default
        if isinstance(obj, dict): return obj.get(attr, default)
        return getattr(obj, attr, default)

    persona_name = get_attr(persona, "name", "Architect")
    persona_tone = get_attr(persona, "tone", "partner")
    if hasattr(persona_tone, 'value'): persona_tone = persona_tone.value
    persona_traits = get_attr(persona, "traits", ["helpful"])
    persona_proactive = get_attr(persona, "proactive_level", 3)
    persona_challenge = get_attr(persona, "challenge_mode", False)

    vision_title = get_attr(vision, "title", "5年终局愿景")
    vision_desc = get_attr(vision, "description", ENDGAME_VISION)
    vision_values = get_attr(vision, "core_values", [])

    if not persona:
        # 回退到默认模板
        return SYSTEM_PROMPT_TEMPLATE.format(
            vision=vision_desc,
            mind=h3.get("mind", 5),
            body=h3.get("body", 5),
            spirit=h3.get("spirit", 5),
            vocation=h3.get("vocation", 5)
        )

    # 动态构建
    challenge_text = '5. **挑战模式**：在肯定现状的基础上，敏锐地指出潜在的时间浪费，鼓励用户向高杠杆任务迁移。' if persona_challenge else '5. **支持模式**：提供情绪价值与实用的组织建议，帮助用户在繁杂事务中保持清晰。'
    
    vision_section = ""
    if vision:
        vision_section = f"目标: {vision_title}\n描述: {vision_desc}\n核心价值观: {', '.join(vision_values) if isinstance(vision_values, list) else vision_values}"
    else:
        vision_section = f"愿景: {ENDGAME_VISION}"

    base_prompt = BASE_SYSTEM_PROMPT.format(
        persona_name=persona_name,
        current_date=current_date,
        persona_tone=persona_tone,
        persona_traits=', '.join(persona_traits) if isinstance(persona_traits, list) else persona_traits,
        persona_proactive=persona_proactive,
        persona_challenge='开启' if persona_challenge else '关闭',
        challenge_mode_text=challenge_text,
        vision_section=vision_section,
        mind=h3.get('mind', 50),
        body=h3.get('body', 50),
        spirit=h3.get('spirit', 50),
        vocation=h3.get('vocation', 50)
    )
    
    # 注入策略上下文
    if strategy_context:
        base_prompt += f"\n{strategy_context}\n"
        base_prompt += "请参考以上历史策略经验，避免重复过去的错误，并应用已验证的成功策略。"

    return base_prompt

def architect_node(state: AgentState) -> AgentState:
    """
    Architect 节点函数
    使用 ChatGemini 模型处理用户输入并生成响应
    """
    # 构建系统提示词
    system_prompt = _generate_dynamic_system_prompt(state)
    
    # 增加对事实回答的强制要求
    system_prompt += ANSWER_PRINCIPLES_PROMPT

    # 获取进化指导 (Self-Navigating) - 注意：这里与 inject_strategy 功能有重叠，
    # inject_strategy 是 LangGraph 节点，这里是原来的 hack 实现。
    # 为了保持架构清晰，我们优先使用 inject_strategy 节点注入的内容。
    # 如果 inject_strategy 已经注入了，这里可以不再重复调用 get_guidance，
    # 或者将这里的逻辑迁移到 inject_strategy 节点。
    # 既然我们已经实现了 inject_strategy 节点，这里的逻辑可以简化或移除。
    # 但为了兼容旧代码可能存在的直接调用，暂时保留异常处理，但不再重复注入，因为 _generate_dynamic_system_prompt 已经包含了 strategy_context
    
    # ... 原有的 evolution_service.get_guidance 调用移除，避免重复 ...

    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        temperature=0.7
    )

    # 注入上下文
    context_message = f"\n### 检索到的记忆与上下文信息：\n{state.get('context', '')}\n"
    messages = [SystemMessage(content=system_prompt + context_message)] + state["messages"]

    response = llm.invoke(messages)

    return {
        "messages": [response],
        "next_step": "end"
    }

def create_endgame_graph(memory_service: MemoryService):
    """
    创建并编译 LangGraph 工作流
    """
    workflow = StateGraph(AgentState)

    # 使用 partial 绑定依赖
    bound_retrieve_memory = partial(retrieve_memory_node, memory_service=memory_service)
    bound_inject_strategy = partial(inject_strategy_node, memory_service=memory_service)

    workflow.add_node("retrieve_memory", bound_retrieve_memory)
    workflow.add_node("inject_strategy", bound_inject_strategy) # 新增节点
    workflow.add_node("check_alignment", check_alignment_node)
    workflow.add_node("architect", architect_node)

    workflow.add_edge(START, "retrieve_memory")
    workflow.add_edge("retrieve_memory", "inject_strategy") # 插入中间步骤
    workflow.add_edge("inject_strategy", "check_alignment")
    workflow.add_edge("check_alignment", "architect")
    workflow.add_edge("architect", END)

    return workflow.compile()
