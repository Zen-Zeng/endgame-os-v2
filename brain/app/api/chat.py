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
from ..services.memory.memory_service import get_memory_service, MemoryService
from ..services.evolution import get_evolution_service
from ..core.db import db_manager

router = APIRouter()

# 移除全局实例
# memory_service = get_memory_service()
# endgame_graph = create_endgame_graph()


# ============ 数据存储 (JSON 持久化) ============
from ..core.config import DATA_DIR

CONVERSATIONS_FILE = DATA_DIR / "conversations.json"
MESSAGES_FILE = DATA_DIR / "messages.json"

def _load_data(file_path, default_value):
    if file_path.exists():
        try:
            return json.loads(file_path.read_text(encoding='utf-8'))
        except:
            return default_value
    return default_value

def _save_data(file_path, data):
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

_conversations_db: dict[str, dict] = _load_data(CONVERSATIONS_FILE, {})
_messages_db: dict[str, List[dict]] = _load_data(MESSAGES_FILE, {})


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
    
    # 保存数据
    _save_data(CONVERSATIONS_FILE, _conversations_db)
    _save_data(MESSAGES_FILE, _messages_db)
    
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
        _save_data(CONVERSATIONS_FILE, _conversations_db)
    
    _save_data(MESSAGES_FILE, _messages_db)
    
    return msg


import logging

logger = logging.getLogger(__name__)

async def _generate_ai_response(
    messages: List[dict],
    user: User,
    conversation_id: str,
    memory_service: MemoryService
) -> AsyncGenerator[str, None]:
    """
    生成 AI 响应 (流式)
    使用 LangGraph 工作流集成记忆和对齐检查
    """
    try:
        logger.info(f"开始通过工作流生成响应，会话: {conversation_id}")
        
        # 转换历史消息为 LangChain 格式，并注入时间戳以解决时间混乱问题
        history = []
        last_date = None
        for msg in messages[:-1]:
            role = msg.get("role", "")
            content = msg.get("content", "")
            created_at = msg.get("created_at")
            
            # 格式化时间戳
            time_str = ""
            if created_at:
                if isinstance(created_at, str):
                    try:
                        dt = datetime.fromisoformat(created_at)
                        curr_date = dt.strftime("%Y-%m-%d")
                        # 如果日期变更，添加日期分割线
                        if curr_date != last_date:
                            history.append(SystemMessage(content=f"--- 日期变更: {curr_date} ---"))
                            last_date = curr_date
                        time_str = f"[{dt.strftime('%H:%M')}] "
                    except: pass
                elif isinstance(created_at, datetime):
                    curr_date = created_at.strftime("%Y-%m-%d")
                    if curr_date != last_date:
                        history.append(SystemMessage(content=f"--- 日期变更: {curr_date} ---"))
                        last_date = curr_date
                    time_str = f"[{created_at.strftime('%H:%M')}] "
            
            # 注入时间信息到内容中，帮助模型建立时间轴
            if role == "user":
                history.append(HumanMessage(content=f"{time_str}{content}"))
            elif role == "assistant":
                history.append(AIMessage(content=f"{time_str}{content}"))
        
        last_user_message = messages[-1].get("content", "")
        # 同样为当前消息添加时间
        current_time_str = f"[{datetime.now().strftime('%H:%M')}] "
        history.append(HumanMessage(content=f"{current_time_str}{last_user_message}"))
        
        # 获取最新的 H3 能量状态
        h3_history = db_manager.get_h3_energy_history(user.id, 1)
        h3_state = {"mind": 50, "body": 50, "spirit": 50, "vocation": 50} # 默认 50%
        if h3_history:
            h3_data = h3_history[0]
            h3_state = {
                "mind": h3_data.get("mind", 50),
                "body": h3_data.get("body", 50),
                "spirit": h3_data.get("spirit", 50),
                "vocation": h3_data.get("vocation", 50)
            }
        
        # 准备初始状态
        initial_state = {
            "user_id": user.id,
            "messages": history, # 已经包含了最后一条
            "h3_state": h3_state,
            "persona": user.persona,
            "vision": user.vision,
            "context": "",
            "current_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "alignment_score": 0.0,
            "next_step": "retrieve"
        }
        
        # 动态创建工作流图，注入 memory_service
        endgame_graph = create_endgame_graph(memory_service)
        
        # 运行工作流并流式获取事件
        full_ai_content = ""
        
        try:
            async for event in endgame_graph.astream(initial_state, config={"configurable": {"thread_id": conversation_id}}):
                logger.info(f"工作流事件: {list(event.keys())}")
                # 检查是否有消息更新（通常来自 architect 节点）
                if "architect" in event:
                    node_output = event["architect"]
                    if "messages" in node_output and node_output["messages"]:
                        new_msg = node_output["messages"][-1]
                        content = new_msg.content
                        
                        # 只有当新内容比已发送内容长时才发送增量 (LangGraph 状态是累积的)
                        if content and len(content) > len(full_ai_content):
                            new_content = content[len(full_ai_content):]
                            logger.info(f"Architect生成新内容: {new_content[:50]}...")
                            
                            # 改进流式 yield 逻辑，支持中文
                            chunk_size = 2 if any('\u4e00' <= char <= '\u9fff' for char in new_content) else 5
                            for i in range(0, len(new_content), chunk_size):
                                chunk = new_content[i:i+chunk_size]
                                yield chunk
                                full_ai_content += chunk
                                await asyncio.sleep(0.01) # 稍微延迟模拟真实感
                
                elif "check_alignment" in event:
                    alignment = event["check_alignment"]
                    score = alignment.get("alignment_score", 0.5)
                    logger.info(f"对齐检查分数: {score}")
        except Exception as graph_err:
            logger.error(f"图执行内部错误: {graph_err}", exc_info=True)
            yield f"\n[思考中断: {str(graph_err)}]"

        # 处理完成后，将对话存入记忆（包含向量库和图谱提取）
        if full_ai_content:
            # 异步处理记忆提取，不阻塞响应
            asyncio.create_task(
                memory_service.process_chat_interaction(
                    user_id=user.id,
                    conversation_id=conversation_id,
                    user_message=last_user_message,
                    ai_response=full_ai_content
                )
            )

            # 异步触发进化分析 (Self-Attributing)
            evolution_service = get_evolution_service()
            asyncio.create_task(
                evolution_service.evolve(
                    user_id=user.id,
                    user_query=last_user_message,
                    current_response=full_ai_content
                )
            )

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
    user: User = Depends(require_user),
    memory_service: MemoryService = Depends(get_memory_service)
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
            async for chunk in _generate_ai_response(messages, user, conversation_id, memory_service):
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
            
            # 更新会话元数据并保存
            if conversation_id in _conversations_db:
                conv = _conversations_db[conversation_id]
                conv["message_count"] = len(_messages_db[conversation_id])
                conv["updated_at"] = datetime.now().isoformat()
                conv["last_message_at"] = datetime.now().isoformat()
                _save_data(CONVERSATIONS_FILE, _conversations_db)
            
            _save_data(MESSAGES_FILE, _messages_db)
            
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
        async for chunk in _generate_ai_response(messages, user, conversation_id, memory_service):
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
    
    _save_data(CONVERSATIONS_FILE, _conversations_db)
    _save_data(MESSAGES_FILE, _messages_db)
    
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
    _save_data(CONVERSATIONS_FILE, _conversations_db)
    
    return {"message": "会话已归档"}
