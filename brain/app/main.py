"""
FastAPI 主应用入口
提供基础的服务启动和路由配置
"""
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from langchain_core.messages import HumanMessage
from app.services.memory.memory_service import MemoryService
from app.services.evolution import get_evolution_service # 引入进化服务
from app.core.config import UVICORN_CONFIG, UPLOAD_DIR
from app.api import api_router
import logging
import uvicorn
import argparse
import shutil
import uuid
import asyncio
from datetime import datetime
from enum import Enum
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler # 引入调度器

# 初始化线程池用于 CPU 密集型任务
executor = ThreadPoolExecutor(max_workers=1)

# 内存任务数据库 (生产环境应使用 Redis 或数据库)
tasks_db = {}

class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

class TaskInfo(BaseModel):
    id: str
    status: TaskStatus
    progress: int = 0
    message: str = ""
    created_at: datetime
    updated_at: Optional[datetime] = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- 定时任务配置 ---
scheduler = AsyncIOScheduler()

async def nightly_evolution_job():
    """夜间进化任务"""
    logger.info("⏰ 触发定时任务: Nightly Evolution Cycle")
    evolution_service = get_evolution_service()
    await evolution_service.run_nightly_cycle()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时
    logger.info("🚀 系统启动中...")
    
    # 启动定时任务调度器
    # 设定每日凌晨 04:00 执行
    scheduler.add_job(nightly_evolution_job, 'cron', hour=4, minute=0)
    scheduler.start()
    logger.info("📅 定时任务调度器已启动 (Next run at 04:00)")
    
    yield
    
    # 关闭时
    logger.info("🛑 系统关闭中...")
    scheduler.shutdown()

app = FastAPI(
    title="Endgame OS Brain API",
    description="基于 LangGraph 和 LangChain 的智能大脑服务",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan # 注册生命周期
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册 API 路由
app.include_router(api_router)

@app.get("/")
async def root():
    return {
        "message": "Endgame OS Brain API",
        "status": "running",
        "version": "2.0.0"
    }

# 移除全局 MemoryService，使用 Depends 注入
# memory_service = MemoryService() 
UPLOAD_DIR.mkdir(exist_ok=True)

@app.get("/api/health")
async def health_check():
    """
    健康检查接口
    """
    return {"status": "healthy"}

def main():
    """
    主函数：解析命令行参数并启动 uvicorn 服务器
    """
    parser = argparse.ArgumentParser(description="Endgame OS Brain API Server")
    parser.add_argument("--host", type=str, default=UVICORN_CONFIG["host"], help="服务器主机地址")
    parser.add_argument("--port", type=int, default=UVICORN_CONFIG["port"], help="服务器端口")
    args = parser.parse_args()

    logger.info(f"启动服务器: host={args.host}, port={args.port}")
    
    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=args.port,
        log_level=UVICORN_CONFIG["log_level"],
        reload=UVICORN_CONFIG.get("reload", False)
    )

if __name__ == "__main__":
    main()
