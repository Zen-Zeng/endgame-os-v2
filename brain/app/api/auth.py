"""
认证 API 路由
处理用户登录、注册、会话管理
"""
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import uuid

from ..models.user import User, UserCreate, UserUpdate, UserVision, PersonaConfig
from ..services.user.user_service import user_service
from ..services.memory.memory_service import get_memory_service
from ..core.db import db_manager
from ..core.config import DATA_DIR
import logging

logger = logging.getLogger(__name__)

router = APIRouter()
security = HTTPBearer(auto_error=False)


# ============ Request/Response Models ============

class LoginRequest(BaseModel):
    email: str
    password: str


class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: User


class TokenVerifyResponse(BaseModel):
    valid: bool
    user: Optional[User] = None


class ResetRequest(BaseModel):
    items: List[str] # ['onboarding', 'chat', 'h3', 'memory']


# ============ 模拟用户存储 ============
import json
from pathlib import Path

SESSION_FILE = DATA_DIR / "sessions.json"
SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)

def _load_sessions():
    if SESSION_FILE.exists():
        try:
            return json.loads(SESSION_FILE.read_text())
        except:
            return {}
    return {}

def _save_sessions(sessions):
    SESSION_FILE.write_text(json.dumps(sessions))

_sessions: dict[str, str] = _load_sessions()

# 初始化数据库
_users_db: dict[str, dict] = user_service.get_all_users()

def _create_mock_user(email: str, name: str) -> User:
    """创建唯一的主用户 bancozy"""
    if email != "bancozy@126.com":
        raise ValueError("仅允许为 bancozy@126.com 创建用户")
        
    return User(
        id="user_bancozy",
        email=email,
        name=name,
        created_at=datetime.now(),
        last_active_at=datetime.now()
    )


def _generate_token() -> str:
    """生成访问令牌"""
    return f"eos_{uuid.uuid4().hex}"


# ============ 依赖函数 ============

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Optional[User]:
    """获取当前用户"""
    if not credentials:
        return None
    
    token = credentials.credentials
    user_id = _sessions.get(token)
    
    if not user_id or user_id not in _users_db:
        return None
    
    user_data = _users_db[user_id]
    return User(**user_data)


async def require_user(
    user: Optional[User] = Depends(get_current_user)
) -> User:
    """要求用户已登录"""
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未登录或登录已过期",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return user


# ============ API 端点 ============

@router.post("/register", response_model=AuthResponse)
async def register(request: RegisterRequest):
    """
    用户注册
    
    仅允许 bancozy@126.com 注册
    """
    if request.email != "bancozy@126.com":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="当前系统为私有系统，仅支持主用户注册"
        )

    # 检查邮箱是否已存在
    for user_data in _users_db.values():
        if user_data["email"] == request.email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="该邮箱已被注册"
            )
    
    # 创建用户
    user = _create_mock_user(request.email, request.name)
    user_json = user.model_dump(mode='json')
    _users_db[user.id] = user_json
    user_service.update_user(user.id, user_json)
    
    # 生成令牌
    token = _generate_token()
    _sessions[token] = user.id
    _save_sessions(_sessions)
    
    return AuthResponse(access_token=token, user=user)


@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest):
    """
    用户登录
    
    仅允许 bancozy@126.com 登录
    """
    if request.email != "bancozy@126.com":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="当前系统为私有系统，仅支持主用户登录"
        )

    # 查找用户
    target_user = None
    for user_data in _users_db.values():
        if user_data["email"] == request.email:
            target_user = User(**user_data)
            break
    
    if not target_user:
        # 开发阶段：自动创建用户
        target_user = _create_mock_user(request.email, request.email.split("@")[0])
        _users_db[target_user.id] = target_user.model_dump(mode='json')
    
    # 生成令牌
    token = _generate_token()
    _sessions[token] = target_user.id
    _save_sessions(_sessions)
    
    # [Strategic Brain] 同步 User 到 Self 节点
    try:
        memory_service = get_memory_service()
        vision_data = target_user.vision.model_dump() if target_user.vision else None
        persona_data = target_user.persona.model_dump() if target_user.persona else None
        memory_service.graph_store.sync_user_to_self_node(target_user.id, vision_data, persona_data)
    except Exception as e:
        print(f"Sync Self Node Error during login: {e}")

    return AuthResponse(access_token=token, user=target_user)


@router.post("/logout")
async def logout(user: User = Depends(require_user)):
    """
    用户登出
    
    销毁当前会话
    """
    # 移除该用户的所有会话
    tokens_to_remove = [
        token for token, uid in _sessions.items() if uid == user.id
    ]
    for token in tokens_to_remove:
        del _sessions[token]
    
    _save_sessions(_sessions)
    
    return {"message": "已成功登出"}


@router.get("/me", response_model=User)
async def get_me(user: User = Depends(require_user)):
    """
    获取当前用户信息
    """
    return user


@router.post("/reset")
async def reset_system_data(
    request: ResetRequest,
    user: User = Depends(require_user)
):
    """根据选项重置系统数据"""
    from .chat import clear_user_chat_history
    results = {}
    
    if "onboarding" in request.items:
        user_service.reset_user_data(user.id)
        db_manager.clear_persona_config(user.id)
        results["onboarding"] = True
        
    if "chat" in request.items:
        clear_user_chat_history(user.id)
        results["chat"] = True
        
    if "h3" in request.items:
        db_manager.clear_h3_data(user.id)
        results["h3"] = True
        
    if "memory" in request.items:
        memory_service = get_memory_service()
        memory_service.clear_graph_memories(user_id=user.id)
        results["memory"] = True

    if "files" in request.items:
        import shutil
        from ..core.config import UPLOAD_DIR
        user_upload_dir = UPLOAD_DIR / user.id
        if user_upload_dir.exists():
            shutil.rmtree(user_upload_dir)
            user_upload_dir.mkdir(parents=True, exist_ok=True)
        results["files"] = True
        
    return {
        "message": "数据清除完成",
        "cleared": results
    }


@router.patch("/me", response_model=User)
async def update_me(
    update: UserUpdate,
    user: User = Depends(require_user)
):
    """
    更新当前用户信息
    """
    user_data = _users_db[user.id]
    
    update_dict = update.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        if value is not None:
            if isinstance(value, (UserVision, PersonaConfig)):
                user_data[key] = value.model_dump()
            else:
                user_data[key] = value
    
    user_data["last_active_at"] = datetime.now().isoformat()
    _users_db[user.id] = user_data
    user_service.update_user(user.id, user_data)
    
    # [Strategic Brain] 同步 User 到 Self 节点 (当愿景或人格更新时)
    if "vision" in update_dict or "persona" in update_dict:
        try:
            memory_service = get_memory_service()
            vision_data = user_data.get("vision")
            persona_data = user_data.get("persona")
            memory_service.graph_store.sync_user_to_self_node(user.id, vision_data, persona_data)
        except Exception as e:
            print(f"Sync Self Node Error during update: {e}")

    return User(**user_data)


@router.post("/initialize", response_model=User)
async def initialize_identity(
    init_data: UserUpdate,
    user: User = Depends(require_user)
):
    """
    初始化用户身份（愿景与人格）
    """
    user_data = _users_db[user.id]
    
    # 强制标记引导完成
    user_data["onboarding_completed"] = True
    
    update_dict = init_data.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        if value is not None:
            if isinstance(value, (UserVision, PersonaConfig)):
                user_data[key] = value.model_dump()
            else:
                user_data[key] = value
    
    user_data["last_active_at"] = datetime.now().isoformat()
    _users_db[user.id] = user_data
    user_service.update_user(user.id, user_data)
    
    # 同步到图谱
    try:
        memory_service = get_memory_service()
        vision_data = user_data.get("vision")
        persona_data = user_data.get("persona")
        memory_service.graph_store.sync_user_to_self_node(user.id, vision_data, persona_data)
    except Exception as e:
        logger.error(f"Sync Self Node Error during initialization: {e}")
        
    return User(**user_data)

@router.post("/verify", response_model=TokenVerifyResponse)
async def verify_token(user: Optional[User] = Depends(get_current_user)):
    """
    验证令牌有效性
    """
    return TokenVerifyResponse(valid=user is not None, user=user)


class SystemResetRequest(BaseModel):
    confirm_text: str  # 必须输入 "DELETE" 才能执行
    clear_vector: bool = True
    clear_graph: bool = True
    clear_user: bool = True
    clear_sessions: bool = True
    clear_uploads: bool = False

@router.post("/system/reset")
async def system_reset(
    request: SystemResetRequest,
    user: User = Depends(require_user)
):
    """
    系统重置接口 (危险操作)
    """
    if request.confirm_text != "DELETE":
        raise HTTPException(status_code=400, detail="确认文本错误，操作已取消")

    memory_service = get_memory_service()
    
    # 1. 清空向量库
    if request.clear_vector:
        try:
            memory_service.vector_store.clear_all_data()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"向量库重置失败: {str(e)}")

    # 2. 清空图谱与 H3 数据
    if request.clear_graph:
        try:
            memory_service.graph_store.clear_all_data(user_id=user.id)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"图谱重置失败: {str(e)}")

    # 3. 清空会话和消息记录 (JSON 文件)
    if request.clear_graph:
        try:
            from ..api.chat import _conversations_db, _messages_db, _save_db
            # 找出属于该用户的会话 ID
            user_conv_ids = [cid for cid, c in _conversations_db.items() if c["user_id"] == user.id]
            
            # 删除会话和对应的消息
            for cid in user_conv_ids:
                if cid in _conversations_db:
                    del _conversations_db[cid]
                if cid in _messages_db:
                    del _messages_db[cid]
            
            # 持久化更改
            _save_db()
            logger.info(f"用户 {user.id} 的会话历史已清空")
        except Exception as e:
            logger.error(f"清空会话历史失败: {e}")
            # 非核心逻辑失败不中断重置流程，仅记录日志

    # 4. 清空上传文件
    if request.clear_uploads:
        pass # 暂未实现文件物理删除，仅逻辑清理

    # 4. 清空用户配置 (慎用，会导致需要重新配置愿景)
    if request.clear_user:
        if user.id in _users_db:
            # 重置为默认状态，保留基本信息
            default_user = _create_mock_user(user.email, user.name)
            _users_db[user.id] = default_user.model_dump(mode='json')
            user_service.update_user(user.id, _users_db[user.id])

    # 5. 清空当前会话 (强制登出)
    if request.clear_sessions:
        tokens_to_remove = [t for t, u in _sessions.items() if u == user.id]
        for t in tokens_to_remove:
            del _sessions[t]
        _save_sessions(_sessions)

    return {"message": "系统重置成功，请重新登录", "redirect": "/login"}

