"""
FastAPI 主应用入口
提供基础的服务启动和路由配置
"""
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from langchain_core.messages import HumanMessage
from app.services.memory.memory_service import MemoryService
from app.core.config import UVICORN_CONFIG, UPLOAD_DIR
from app.api import api_router
import logging
import uvicorn
import argparse
import shutil
import uuid
from datetime import datetime
from enum import Enum
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

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

def run_ingestion_task(task_id: str, file_paths: List[str]):
    """
    后台执行记忆摄取任务的包装函数
    """
    try:
        tasks_db[task_id].status = TaskStatus.IN_PROGRESS
        tasks_db[task_id].updated_at = datetime.now()
        tasks_db[task_id].message = f"正在摄取 {len(file_paths)} 个文件..."
        
        # 实际调用同步的记忆摄取方法
        for file_path in file_paths:
            memory_service.ingest_file(file_path)
        
        tasks_db[task_id].status = TaskStatus.COMPLETED
        tasks_db[task_id].progress = 100
        tasks_db[task_id].message = "记忆训练完成"
        tasks_db[task_id].updated_at = datetime.now()
        
    except Exception as e:
        logger.error(f"任务 {task_id} 失败: {str(e)}")
        tasks_db[task_id].status = TaskStatus.FAILED
        tasks_db[task_id].message = f"错误: {str(e)}"
        tasks_db[task_id].updated_at = datetime.now()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Endgame OS Brain API",
    description="基于 LangGraph 和 LangChain 的智能大脑服务",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
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

# 挂载前端静态文件 (如果存在)
FRONTEND_DIST = Path(__file__).parent.parent.parent / "face" / "dist"
if FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="frontend")
    logger.info(f"已挂载前端静态文件: {FRONTEND_DIST}")
else:
    logger.warning(f"未找到前端静态文件目录: {FRONTEND_DIST}，将只提供 API 服务")
    @app.get("/")
    async def root():
        return {
            "message": "Endgame OS Brain API",
            "status": "running",
            "version": "2.0.0",
            "frontend": "Not mounted (run 'npm run build' in face directory)"
        }

memory_service = MemoryService()
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
