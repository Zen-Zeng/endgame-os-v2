"""
认证 API 路由
处理用户登录、注册、会话管理
"""
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import uuid

from ..models.user import User, UserCreate, UserUpdate, UserVision, PersonaConfig

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


# ============ 模拟用户存储 (后续替换为 Supabase) ============

# 预置测试账户
_test_user = User(
    id="user_test_123",
    email="test@endgame.ai",
    name="测试账户",
    created_at=datetime.now(),
    last_active_at=datetime.now()
)

_users_db: dict[str, dict] = {
    _test_user.id: _test_user.model_dump(mode='json')
}
_sessions: dict[str, str] = {
    "test_token_999": _test_user.id
}  # token -> user_id


def _create_mock_user(email: str, name: str) -> User:
    """创建模拟用户"""
    user_id = f"user_{uuid.uuid4().hex[:8]}"
    return User(
        id=user_id,
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
    
    创建新用户账号并返回访问令牌
    """
    # 检查邮箱是否已存在
    for user_data in _users_db.values():
        if user_data["email"] == request.email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="该邮箱已被注册"
            )
    
    # 创建用户
    user = _create_mock_user(request.email, request.name)
    _users_db[user.id] = user.model_dump(mode='json')
    
    # 生成令牌
    token = _generate_token()
    _sessions[token] = user.id
    
    return AuthResponse(access_token=token, user=user)


@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest):
    """
    用户登录
    
    验证凭据并返回访问令牌
    """
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
    
    return {"message": "已成功登出"}


@router.get("/me", response_model=User)
async def get_me(user: User = Depends(require_user)):
    """
    获取当前用户信息
    """
    return user


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
    
    return User(**user_data)


@router.post("/verify", response_model=TokenVerifyResponse)
async def verify_token(user: Optional[User] = Depends(get_current_user)):
    """
    验证令牌有效性
    """
    return TokenVerifyResponse(valid=user is not None, user=user)


@router.post("/refresh", response_model=AuthResponse)
async def refresh_token(user: User = Depends(require_user)):
    """
    刷新访问令牌
    """
    # 生成新令牌
    new_token = _generate_token()
    _sessions[new_token] = user.id
    
    return AuthResponse(access_token=new_token, user=user)

