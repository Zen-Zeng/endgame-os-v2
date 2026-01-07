"""
对话 API 路由
处理 AI 对话、SSE 流式响应
"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, AsyncGenerator
from datetime import datetime
import uuid
import json
import asyncio
import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from ..models.chat import (
    Message, Conversation, ChatRequest, ChatResponse,
    StreamChunk, ConversationSummary, MessageRole, MessageType
)
from ..models.user import User
from .auth import require_user, get_current_user
from ..core.config import SYSTEM_PROMPT_TEMPLATE, ENDGAME_VISION
from ..core.workflow import create_endgame_graph
from ..services.memory.memory_service import get_memory_service

router = APIRouter()

# 获取记忆服务单例
memory_service = get_memory_service()
# 创建工作流图
endgame_graph = create_endgame_graph()


# ============ 模拟数据存储 (暂时保留用于会话元数据，后续应迁移至数据库) ============

_conversations_db: dict[str, dict] = {}
_messages_db: dict[str, List[dict]] = {}


# ============ Request Models ============

class ConversationListParams(BaseModel):
    limit: int = 20
    offset: int = 0
    include_archived: bool = False


# ============ 辅助函数 ============

def _create_conversation(user_id: str, title: Optional[str] = None) -> Conversation:
    """创建新会话"""
    conv_id = f"conv_{uuid.uuid4().hex[:8]}"
    conv = Conversation(
        id=conv_id,
        user_id=user_id,
        title=title or f"对话 {datetime.now().strftime('%m/%d %H:%M')}",
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    _conversations_db[conv_id] = conv.model_dump(mode='json')
    _messages_db[conv_id] = []
    return conv


def _add_message(
    conversation_id: str,
    role: MessageRole,
    content: str,
    message_type: MessageType = MessageType.TEXT
) -> Message:
    """添加消息到会话"""
    msg_id = f"msg_{uuid.uuid4().hex[:8]}"
    msg = Message(
        id=msg_id,
        conversation_id=conversation_id,
        role=role,
        content=content,
        message_type=message_type,
        created_at=datetime.now()
    )
    
    if conversation_id not in _messages_db:
        _messages_db[conversation_id] = []
    
    _messages_db[conversation_id].append(msg.model_dump(mode='json'))
    
    # 更新会话
    if conversation_id in _conversations_db:
        conv = _conversations_db[conversation_id]
        conv["message_count"] = len(_messages_db[conversation_id])
        conv["updated_at"] = datetime.now().isoformat()
        conv["last_message_at"] = datetime.now().isoformat()
    
    return msg


import logging

logger = logging.getLogger(__name__)

async def _generate_ai_response(
    messages: List[dict],
    user: User,
    conversation_id: str
) -> AsyncGenerator[str, None]:
    """
    生成 AI 响应 (流式)
    使用 LangGraph 工作流集成记忆和对齐检查
    """
    try:
        logger.info(f"开始通过工作流生成响应，会话: {conversation_id}")
        
        # 转换历史消息为 LangChain 格式
        history = []
        for msg in messages[:-1]:  # 排除最后一条（当前输入）
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "user":
                history.append(HumanMessage(content=content))
            elif role == "assistant":
                history.append(AIMessage(content=content))
        
        last_user_message = messages[-1].get("content", "")
        
        # 准备初始状态
        initial_state = {
            "messages": history + [HumanMessage(content=last_user_message)],
            "h3_state": user.h3_state.model_dump() if hasattr(user, 'h3_state') else {"mind": 5, "body": 5, "spirit": 5, "vocation": 5},
            "context": "",
            "memory_query": last_user_message,
            "next_step": "retrieve"
        }
        
        # 运行工作流并流式获取事件
        # 注意：这里我们使用 astream 模式来获取节点运行信息
        chunk_count = 0
        full_ai_content = ""
        
        async for event in endgame_graph.astream(initial_state, config={"configurable": {"thread_id": conversation_id}}):
            # 检查是否有消息更新（通常来自 architect 节点）
            if "architect" in event:
                node_output = event["architect"]
                if "messages" in node_output and node_output["messages"]:
                    new_msg = node_output["messages"][-1]
                    content = new_msg.content
                    
                    # 为了模拟流式效果（因为 invoke/node 通常是一次性返回），
                    # 我们将内容切分并 yield。
                    # 未来如果 architect 节点支持内部流式，这里可以更精细。
                    words = content.split(' ')
                    for i, word in enumerate(words):
                        space = ' ' if i < len(words) - 1 else ''
                        yield word + space
                        full_ai_content += word + space
                        await asyncio.sleep(0.01) # 微小延迟模拟流式
            
            # 可以在这里 yield 节点状态更新，例如“正在检索记忆...”、“正在分析目标对齐...”
            elif "retrieve_memory" in event:
                # yield "\n[系统：正在检索相关记忆...]\n"
                pass
            elif "check_alignment" in event:
                alignment = event["check_alignment"]
                score = alignment.get("alignment_score", 0.5)
                # if score < 0.4:
                #     yield f"\n[警示：当前讨论内容与终局愿景对齐度较低 ({score})]\n"

        # 处理完成后，将对话存入记忆图谱
        if full_ai_content:
            # 异步存入，不阻塞响应
            asyncio.create_task(asyncio.to_thread(
                memory_service.graph_store.add_log,
                log_id=f"chat_{uuid.uuid4().hex[:6]}",
                content=f"User: {last_user_message}\nAI: {full_ai_content}",
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                log_type="chat_history"
            ))

    except Exception as e:
        logger.error(f"工作流执行出错: {str(e)}", exc_info=True)
        # 提供更友好的错误信息
        error_msg = str(e)
        if "model" in error_msg.lower() and "not found" in error_msg.lower():
            yield f"\n[系统错误: AI 模型配置有误 (Gemini 2.5 可能不可用)，请检查 API Key 权限或模型版本设置。]"
        else:
            yield f"\n[系统错误: 思考过程被中断 - {error_msg}]"


# ============ API 端点 ============

@router.post("/send")
async def send_message(
    request: ChatRequest,
    user: User = Depends(require_user)
):
    """
    发送消息并获取 AI 响应
    
    支持流式和非流式两种模式
    """
    # 获取或创建会话
    conversation_id = request.conversation_id
    if not conversation_id:
        conv = _create_conversation(user.id)
        conversation_id = conv.id
    elif conversation_id not in _conversations_db:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    # 添加用户消息
    user_msg = _add_message(
        conversation_id,
        MessageRole.USER,
        request.message
    )
    
    if request.stream:
        # 流式响应
        async def stream_response():
            msg_id = f"msg_{uuid.uuid4().hex[:8]}"
            full_content = ""
            
            # 发送开始标记
            yield f"data: {json.dumps({'type': 'start', 'message_id': msg_id, 'conversation_id': conversation_id})}\n\n"
            
            # 获取历史消息
            messages = _messages_db.get(conversation_id, [])
            
            # 流式生成响应
            async for chunk in _generate_ai_response(messages, user, conversation_id):
                full_content += chunk
                yield f"data: {json.dumps({'type': 'content', 'content': chunk})}\n\n"
            
            # 保存完整消息
            ai_msg = Message(
                id=msg_id,
                conversation_id=conversation_id,
                role=MessageRole.ASSISTANT,
                content=full_content,
                message_type=MessageType.TEXT,
                created_at=datetime.now()
            )
            _messages_db[conversation_id].append(ai_msg.model_dump(mode='json'))
            
            # 发送完成标记
            yield f"data: {json.dumps({'type': 'done', 'message': ai_msg.model_dump(mode='json')})}\n\n"
        
        return StreamingResponse(
            stream_response(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )
    else:
        # 非流式响应
        messages = _messages_db.get(conversation_id, [])
        full_content = ""
        async for chunk in _generate_ai_response(messages, user, conversation_id):
            full_content += chunk
        
        ai_msg = _add_message(
            conversation_id,
            MessageRole.ASSISTANT,
            full_content
        )
        
        return ChatResponse(
            message=ai_msg,
            conversation_id=conversation_id,
            suggestions=["告诉我更多", "今天的目标是什么？", "帮我回顾一下"]
        )


@router.get("/conversations", response_model=List[ConversationSummary])
async def list_conversations(
    limit: int = 20,
    offset: int = 0,
    user: User = Depends(require_user)
):
    """
    获取用户的会话列表
    """
    user_convs = [
        conv for conv in _conversations_db.values()
        if conv["user_id"] == user.id and not conv.get("is_archived", False)
    ]
    
    # 按更新时间排序
    user_convs.sort(key=lambda x: x["updated_at"], reverse=True)
    
    # 分页
    paginated = user_convs[offset:offset + limit]
    
    summaries = []
    for conv in paginated:
        msgs = _messages_db.get(conv["id"], [])
        last_msg = msgs[-1]["content"][:50] if msgs else None
        
        summaries.append(ConversationSummary(
            id=conv["id"],
            title=conv.get("title"),
            last_message=last_msg,
            message_count=len(msgs),
            created_at=conv["created_at"],
            updated_at=conv["updated_at"]
        ))
    
    return summaries


@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    user: User = Depends(require_user)
):
    """
    获取会话详情和消息历史
    """
    if conversation_id not in _conversations_db:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    conv_data = _conversations_db[conversation_id]
    if conv_data["user_id"] != user.id:
        raise HTTPException(status_code=403, detail="无权访问此会话")
    
    messages = _messages_db.get(conversation_id, [])
    
    return {
        "conversation": conv_data,
        "messages": messages
    }


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    user: User = Depends(require_user)
):
    """
    删除会话
    """
    if conversation_id not in _conversations_db:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    conv_data = _conversations_db[conversation_id]
    if conv_data["user_id"] != user.id:
        raise HTTPException(status_code=403, detail="无权删除此会话")
    
    del _conversations_db[conversation_id]
    if conversation_id in _messages_db:
        del _messages_db[conversation_id]
    
    return {"message": "会话已删除"}


@router.post("/conversations/{conversation_id}/archive")
async def archive_conversation(
    conversation_id: str,
    user: User = Depends(require_user)
):
    """
    归档会话
    """
    if conversation_id not in _conversations_db:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    conv_data = _conversations_db[conversation_id]
    if conv_data["user_id"] != user.id:
        raise HTTPException(status_code=403, detail="无权操作此会话")
    
    conv_data["is_archived"] = True
    _conversations_db[conversation_id] = conv_data
    
    return {"message": "会话已归档"}

