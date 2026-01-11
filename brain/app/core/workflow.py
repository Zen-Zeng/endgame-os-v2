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

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_path)

from app.services.memory.memory_service import MemoryService
from app.services.evolution import get_evolution_service
from app.core.config import SYSTEM_PROMPT_TEMPLATE, ENDGAME_VISION
from app.models.user import PersonaConfig, UserVision

# 初始化记忆服务
memory_service = MemoryService()

class AgentState(TypedDict):
    """
    Agent 状态定义
    包含消息列表、上下文信息、H3 状态、对齐分、人格配置和用户愿景
    """
    user_id: str
    messages: Annotated[Sequence[BaseMessage], operator.add]
    context: str
    current_date: str  # 新增：当前系统时间
    h3_state: Dict[str, int]
    alignment_score: float
    next_step: str
    persona: PersonaConfig
    vision: Optional[UserVision]

def retrieve_memory_node(state: AgentState) -> AgentState:
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
    # 扩大关键词范围，确保更准确的触发
    graph_keywords = ["项目", "任务", "进度", "工作", "目标", "计划", "实现", "愿景", "记得", "哪些", "清单"]
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
    
    # 构建对齐检查的提示词
    alignment_prompt = f"""
    作为用户的“数字分身”，请评估以下用户输入是否与其“5年终局愿景”对齐。
    
    终局愿景 ({vision_title})：
    {vision_desc}
    
    用户输入：
    {last_message}
    
    请输出一个 0 到 1 之间的对齐分数（Score），并给出简短的理由（Reason）。
    格式要求：
    Score: [分数]
    Reason: [原因]
    """
    
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
        logger.error(f"对齐检查失败: {e}")
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
    base_prompt = f"""你是 {persona_name}，用户的数字分身与终局合伙人。
系统时间 (当前时刻): {current_date}。

你的语气风格是: {persona_tone}。
你的特征包括: {', '.join(persona_traits) if isinstance(persona_traits, list) else persona_traits}。
你的主动性级别是: {persona_proactive}/5，挑战模式: {'开启' if persona_challenge else '关闭'}。

## 时间感知与事实对齐 (CRITICAL)
1. **当前时刻锚点**：你必须以系统时间 {current_date} 为唯一的“现在”锚点。
2. **区分历史与当下**：对话历史中的每一条消息都带有 [HH:MM] 时间戳，且有“日期变更”标记。请利用这些标记构建精确的时间线，不要将昨天的计划误认为是今天的任务。
3. **记忆权重**：优先引用 Context 中时间戳最接近当前的结构化信息。如果用户提到“今天”、“明天”或“下周”，请务必根据当前系统时间进行逻辑推演。
4. **进度连续性**：如果检索到正在进行中的项目，请主动询问或参考其最新状态。

## 核心职责
你的使命是作为用户的“首席架构师”和“忠实合伙人”，协助用户管理当下并走向终局愿景。
1. **时间极其敏感**：你必须对时间保持高度敏感。优先处理和引用最近的项目进度、对话记录。根据当前日期来评估任务的紧迫性和相关性。
2. **进度伙伴**：主动追踪和管理用户的项目进度、工作任务。你要像对待自己的事业一样关注这些细节。
3. **事实驱动**：回答必须基于检索到的数据。如果检索到相关项目/任务，请直接引用它们并注明时间，展示你“记得”且“在乎”。
4. **建设性对齐**：即使某些任务看起来与愿景关联较弱，也不要生硬否定。尝试从“维持系统稳定”、“积累必要资源”或“为愿景腾出空间”的角度给予肯定，并引导用户思考如何更高效地完成它们。
5. **拒绝空洞**：不要只谈愿景，要谈具体的下一步。如果用户问“我该做什么”，请结合当前的项目进度和今天的日期给出建议。
{'5. **挑战模式**：在肯定现状的基础上，敏锐地指出潜在的时间浪费，鼓励用户向高杠杆任务迁移。' if persona_challenge else '5. **支持模式**：提供情绪价值与实用的组织建议，帮助用户在繁杂事务中保持清晰。'}

## 交互准则
- 优先展示你对当前项目/任务状态的掌握情况。
- 如果用户提到新信息，请表现出“已记录”并能自动关联到相关项目。
- 语气应始终保持 {persona_tone}，像一个值得信赖的、认知水平极高的老友。

## 当前愿景
"""
    if vision:
        base_prompt += f"目标: {vision_title}\n描述: {vision_desc}\n核心价值观: {', '.join(vision_values) if isinstance(vision_values, list) else vision_values}"
    else:
        base_prompt += f"愿景: {ENDGAME_VISION}"

    base_prompt += f"""

## 当前状态 (H3)
- 心智 (Mind): {h3.get('mind', 50)}%
- 身体 (Body): {h3.get('body', 50)}%
- 精神 (Spirit): {h3.get('spirit', 50)}%
- 志业 (Vocation): {h3.get('vocation', 50)}%

请基于以上设定，以 {persona_name} 的身份与用户对话。"""
    
    return base_prompt

def architect_node(state: AgentState) -> AgentState:
    """
    Architect 节点函数
    使用 ChatGemini 模型处理用户输入并生成响应
    """
    # 构建系统提示词
    system_prompt = _generate_dynamic_system_prompt(state)
    
    # 增加对事实回答的强制要求
    system_prompt += """
## 回答原则
1. **事实为王**：如果 Context 中有具体的项目/任务/愿景数据，必须优先列出。严禁说“我没有权限”或“我不记得”。
2. **行动导向**：不仅要列出进度，还要根据上下文建议“下一步该做什么”。
3. **温暖的理性**：在引用对齐分析时，要把分析结果转化为对用户的理解。例如，如果对齐分低，你可以说：“虽然这些琐事目前占据了你的精力，但我理解它们是必经之路。我们可以尝试快速搞定它们，为你真正的核心项目『认知重构』腾出空间。”
"""

    # 获取进化指导 (Self-Navigating)
    try:
        evolution_service = get_evolution_service()
        last_message = state["messages"][-1].content
        guidance = evolution_service.get_guidance(last_message)
        
        if guidance:
            system_prompt += f"""
### 💡 历史经验指导 (Evolutionary Guidance)
根据过往的交互反思，针对当前情况，请参考以下策略：
{guidance}
"""
            logger.info(f"已注入进化指导: {guidance[:50]}...")
    except Exception as e:
        logger.error(f"获取进化指导失败: {e}")

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

def create_endgame_graph():
    """
    创建并编译 LangGraph 工作流
    """
    workflow = StateGraph(AgentState)

    workflow.add_node("retrieve_memory", retrieve_memory_node)
    workflow.add_node("check_alignment", check_alignment_node)
    workflow.add_node("architect", architect_node)

    workflow.add_edge(START, "retrieve_memory")
    workflow.add_edge("retrieve_memory", "check_alignment")
    workflow.add_edge("check_alignment", "architect")
    workflow.add_edge("architect", END)

    return workflow.compile()
