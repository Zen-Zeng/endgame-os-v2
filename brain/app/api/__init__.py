# Endgame OS - API 路由层
# Brain API Package

from fastapi import APIRouter

# 创建主路由器
api_router = APIRouter(prefix="/api/v1")

# 导入子路由
from .auth import router as auth_router
from .chat import router as chat_router
from .h3 import router as h3_router
from .calibration import router as calibration_router
from .dashboard import router as dashboard_router
from .archives import router as archives_router
from .memory import router as memory_router
from .persona import router as persona_router
from .goals import router as goals_router
from .links import router as links_router

# 注册子路由
@api_router.get("/", tags=["基础"])
async def api_root():
    return {"message": "Endgame OS Brain API v1", "status": "running"}

@api_router.get("/health", tags=["健康检查"])
async def health_check():
    return {"status": "healthy", "version": "2.0.0"}

api_router.include_router(auth_router, prefix="/auth", tags=["认证"])
api_router.include_router(chat_router, prefix="/chat", tags=["对话"])
api_router.include_router(h3_router, prefix="/h3", tags=["H3能量"])
api_router.include_router(calibration_router, prefix="/calibration", tags=["校准"])
api_router.include_router(dashboard_router, prefix="/dashboard", tags=["仪表盘"])
api_router.include_router(archives_router, prefix="/archives", tags=["档案库"])
api_router.include_router(memory_router, prefix="/memory", tags=["记忆"])
api_router.include_router(persona_router, prefix="/persona", tags=["人格"])
api_router.include_router(goals_router, prefix="/goals", tags=["目标管理"])
api_router.include_router(links_router, prefix="/links", tags=["神经链接"])

__all__ = ["api_router"]

