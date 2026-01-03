"""
FastAPI 主应用入口
提供基础的服务启动和路由配置
"""
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from langchain_core.messages import HumanMessage
from app.core.workflow import graph
from app.services.memory.memory_service import MemoryService
from app.core.config import UVICORN_CONFIG, UPLOAD_DIR
import logging
import uvicorn
import argparse
import shutil
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Endgame OS Brain API",
    description="基于 LangGraph 和 LangChain 的智能大脑服务",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

memory_service = MemoryService()
UPLOAD_DIR.mkdir(exist_ok=True)

class H3State(BaseModel):
    """
    H3 能量状态模型
    """
    mind: int = 5
    body: int = 5
    spirit: int = 5
    vocation: int = 5

class ChatRequest(BaseModel):
    """
    聊天请求模型
    """
    query: str
    context: Optional[str] = ""
    h3_state: Optional[H3State] = H3State()

class ChatResponse(BaseModel):
    """
    聊天响应模型
    """
    response: str
    context: str

class TrainRequest(BaseModel):
    """
    训练请求模型
    """
    file_paths: List[str]

class QueryRequest(BaseModel):
    """
    查询请求模型
    """
    query: str
    n_results: int = 5
    filter_metadata: Optional[dict] = None

class H3Log(BaseModel):
    """
    H3 日志模型
    """
    mind: int
    body: int
    spirit: int
    vocation: int
    note: Optional[str] = ""

@app.get("/")
async def root():
    """
    根路径健康检查接口
    """
    return {
        "message": "Endgame OS Brain API",
        "status": "running",
        "version": "0.1.0",
        "endpoints": {
            "health": "/api/health",
            "chat": "/api/chat",
            "memory": "/api/memory/stats",
            "h3": "/api/h3/history"
        }
    }

@app.get("/api")
async def api_info():
    """
    API 信息接口
    """
    return {
        "message": "Endgame OS Brain API",
        "status": "running",
        "version": "0.1.0"
    }

@app.get("/api/health")
async def health_check():
    """
    健康检查接口
    """
    return {"status": "healthy"}

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    聊天接口
    接收用户输入，调用 LangGraph 工作流，返回 AI 回复
    """
    try:
        logger.info(f"收到请求: query={request.query}, h3_state={request.h3_state}")

        initial_state = {
            "messages": [HumanMessage(content=request.query)],
            "context": request.context,
            "h3_state": request.h3_state.dict() if request.h3_state else {"mind": 5, "body": 5, "spirit": 5, "vocation": 5}
        }

        logger.info("调用 graph.invoke")
        result = graph.invoke(initial_state)
        logger.info(f"graph.invoke 完成: {result}")

        response_text = result["messages"][-1].content

        return ChatResponse(
            response=response_text,
            context=result.get("context", "")
        )
    except Exception as e:
        logger.error(f"聊天接口错误: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/h3/update")
async def update_h3(log: H3Log):
    """
    更新 H3 能量状态
    """
    try:
        # TODO: 将 H3 状态存入 KuzuDB
        logger.info(f"更新 H3 状态: {log}")
        return {"success": True, "message": "H3 状态已更新"}
    except Exception as e:
        logger.error(f"更新 H3 状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/h3/history")
async def get_h3_history():
    """
    获取 H3 历史趋势
    """
    try:
        # TODO: 从 KuzuDB 获取历史数据
        return {
            "success": True,
            "history": [
                {"date": "2026-01-01", "mind": 5, "body": 6, "spirit": 4, "vocation": 5},
                {"date": "2026-01-02", "mind": 6, "body": 5, "spirit": 5, "vocation": 6}
            ]
        }
    except Exception as e:
        logger.error(f"获取 H3 历史失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    文件上传接口
    """
    try:
        file_path = UPLOAD_DIR / file.filename
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        logger.info(f"文件上传成功: {file_path}")
        
        return {
            "success": True,
            "file_path": str(file_path),
            "filename": file.filename
        }
    except Exception as e:
        logger.error(f"文件上传失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/train")
async def train_memory(request: TrainRequest):
    """
    记忆训练接口
    """
    try:
        logger.info(f"开始训练记忆，文件数量: {len(request.file_paths)}")
        result = memory_service.ingest_files(request.file_paths)
        logger.info(f"训练完成: 成功 {result['success']}, 失败 {result['failed']}")
        return result
    except Exception as e:
        logger.error(f"训练失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/memory/query")
async def query_memory(request: QueryRequest):
    """
    记忆查询接口
    """
    try:
        logger.info(f"查询记忆: {request.query}")
        results = memory_service.query_memory(
            query=request.query,
            n_results=request.n_results,
            filter_metadata=request.filter_metadata
        )
        return {
            "success": True,
            "results": results,
            "count": len(results)
        }
    except Exception as e:
        logger.error(f"查询记忆失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/memory/stats")
async def get_memory_stats():
    """
    记忆统计接口
    """
    try:
        stats = memory_service.get_stats()
        return stats
    except Exception as e:
        logger.error(f"获取统计信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/memory/clear")
async def clear_memory():
    """
    清空记忆接口
    """
    try:
        result = memory_service.clear_memory()
        return result
    except Exception as e:
        logger.error(f"清空记忆失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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
        app,
        host=args.host,
        port=args.port,
        log_level=UVICORN_CONFIG["log_level"]
    )

if __name__ == "__main__":
    main()
