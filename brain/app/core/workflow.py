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
    memories = memory_service.query_memory(last_message, n_results=3)
    
    context = state.get("context", "")
    if memories:
        memory_text = "\n相关历史记忆：\n" + "\n".join([m['content'] for m in memories])
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
    # 简单实现：目前仅作为占位，未来可引入 LLM 进行语义对齐分析
    return {
        "alignment_score": 0.85,
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

def create_graph() -> StateGraph:
    """
    创建 LangGraph 工作流
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

graph = create_graph()
