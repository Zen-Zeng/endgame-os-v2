"""
LangGraph 思考流
构建左脑的核心思考流程
"""
from typing import TypedDict, Annotated, Sequence, Dict, Any, List
from langgraph.graph import StateGraph, START, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
import operator
import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# 显式取消代理设置，确保 Gemini API 直连
import os
for var in ['http_proxy', 'https_proxy', 'all_proxy', 'HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY']:
    if var in os.environ:
        del os.environ[var]

from app.services.memory.memory_service import MemoryService
from app.core.config import SYSTEM_PROMPT_TEMPLATE, ENDGAME_VISION

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_path)

# 初始化记忆服务
memory_service = MemoryService()

class AgentState(TypedDict):
    """
    Agent 状态定义
    包含消息列表、上下文信息、H3 状态和对齐分
    """
    messages: Annotated[Sequence[BaseMessage], operator.add]
    context: str
    h3_state: Dict[str, int]
    alignment_score: float
    next_step: str

def retrieve_memory_node(state: AgentState) -> AgentState:
    """
    记忆检索节点
    从向量库检索相关记忆
    """
    last_message = state["messages"][-1].content
    logger.info(f"正在检索记忆: {last_message[:50]}...")
    
    # 检索语义记忆
    memories = memory_service.vector_store.similarity_search(last_message, n_results=3)
    
    context = state.get("context", "")
    if memories:
        memory_text = "\n相关历史记忆：\n" + "\n".join([m.get('content', '') for m in memories])
        context += memory_text
    
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
    
    # 构建对齐检查的提示词
    alignment_prompt = f"""
    作为用户的“数字分身”，请评估以下用户输入是否与其“5年终局愿景”对齐。
    
    终局愿景：
    {ENDGAME_VISION}
    
    用户输入：
    {last_message}
    
    请输出一个 0 到 1 之间的对齐分数（Score），并给出简短的理由（Reason）。
    格式要求：
    Score: [分数]
    Reason: [原因]
    """
    
    try:
        llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)
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

def architect_node(state: AgentState) -> AgentState:
    """
    Architect 节点函数
    使用 ChatGemini 模型处理用户输入并生成响应
    """
    h3 = state.get("h3_state", {"mind": 5, "body": 5, "spirit": 5, "vocation": 5})
    
    # 构建系统提示词
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
        vision=ENDGAME_VISION,
        mind=h3.get("mind", 5),
        body=h3.get("body", 5),
        spirit=h3.get("spirit", 5),
        vocation=h3.get("vocation", 5)
    )

    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0.7
    )

    # 注入上下文
    context_message = f"\n当前对话上下文：\n{state.get('context', '')}"
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
