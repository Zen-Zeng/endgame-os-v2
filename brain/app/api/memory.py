"""
记忆图谱 API 路由
处理知识图谱的查询、创建和可视化
"""
from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from typing import List, Optional, Dict
from datetime import datetime
import uuid
import asyncio
import logging

from ..models.memory import (
    MemoryNode, MemoryRelation, MemoryType, RelationType,
    MemorySearchResult, MemoryGraphData, MemoryCreateRequest, MemorySearchRequest
)
from ..models.user import User
from .auth import require_user

from ..services.memory.memory_service import get_memory_service
from ..core.config import UPLOAD_DIR

router = APIRouter()

# 共享任务状态数据库
_tasks_db: Dict[str, Dict] = {}  # task_id -> task_status

logger = logging.getLogger(__name__)

async def _process_training_task(task_id: str, filename: str):
    """异步处理训练任务，调用真实的 MemoryService"""
    try:
        service = get_memory_service()
        _tasks_db[task_id]["status"] = "processing"
        _tasks_db[task_id]["progress"] = 10
        _tasks_db[task_id]["message"] = "正在解析文档..."
        
        # 获取完整文件路径
        # 注意：这里的逻辑要根据 archives.py 的存储逻辑来对齐
        # archives.py 目前把文件存放在 uploads/{user_id}/{filename}
        # 但目前 _process_training_task 没有 user_id
        # 为了演示，我们先从全局 uploads 目录找，或者修改接口
        file_path = UPLOAD_DIR / filename
        
        # 如果不存在，尝试在所有子目录中查找（应对不同用户的上传）
        if not file_path.exists():
            for user_dir in UPLOAD_DIR.iterdir():
                if user_dir.is_dir():
                    potential_path = user_dir / filename
                    if potential_path.exists():
                        file_path = potential_path
                        break

        if not file_path.exists():
            raise FileNotFoundError(f"找不到文件: {filename}")

        _tasks_db[task_id]["progress"] = 30
        _tasks_db[task_id]["message"] = "正在提取实体与关系..."
        
        # 调用真实的 ingest_file (同步方法在后台线程运行)
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, service.ingest_file, str(file_path))
        
        if result.get("success"):
            _tasks_db[task_id]["status"] = "completed"
            _tasks_db[task_id]["progress"] = 100
            _tasks_db[task_id]["message"] = "训练完成"
        else:
            raise Exception(result.get("error", "未知处理错误"))
        
    except Exception as e:
        logger.error(f"Training task {task_id} failed: {str(e)}")
        _tasks_db[task_id]["status"] = "failed"
        _tasks_db[task_id]["error"] = str(e)
        _tasks_db[task_id]["message"] = f"错误: {str(e)}"

# 移除模拟数据存储和初始化
# _nodes_db: dict[str, dict] = {}
# _relations_db: dict[str, dict] = {}


@router.post("/train")
async def start_training(
    request: Dict[str, str],
    background_tasks: BackgroundTasks,
    user: User = Depends(require_user)
):
    """
    启动异步记忆训练任务
    """
    filename = request.get("filename")
    if not filename:
        raise HTTPException(status_code=400, detail="缺少文件名")
    
    task_id = f"task_{uuid.uuid4().hex[:8]}"
    _tasks_db[task_id] = {
        "id": task_id,
        "status": "pending",
        "progress": 0,
        "filename": filename,
        "created_at": datetime.now().isoformat()
    }
    
    background_tasks.add_task(_process_training_task, task_id, filename)
    
    return {"task_id": task_id, "message": "训练任务已启动"}


@router.get("/tasks/{task_id}")
async def get_task_status(
    task_id: str,
    user: User = Depends(require_user)
):
    """
    获取任务执行状态
    """
    if task_id not in _tasks_db:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    return _tasks_db[task_id]


# ============ API 端点 ============

@router.get("/graph", response_model=MemoryGraphData)
async def get_graph(
    types: Optional[str] = Query(default=None, description="节点类型过滤，逗号分隔"),
    depth: int = Query(default=2, ge=1, le=5, description="遍历深度"),
    center_node_id: Optional[str] = None,
    user: User = Depends(require_user)
):
    """
    获取记忆图谱数据（从真实的 KuzuDB 获取）
    """
    service = get_memory_service()
    graph_data = service.graph_store.get_all_graph_data()
    
    # 转换为 Pydantic 模型
    nodes = []
    for n in graph_data.get("nodes", []):
        try:
            # 确保类型转换正确
            nodes.append(MemoryNode(**n))
        except Exception as e:
            logger.warning(f"节点转换失败: {n.get('id')}, {e}")

    links = []
    for l in graph_data.get("links", []):
        try:
            # 格式转换以匹配 MemoryRelation 模型
            links.append(MemoryRelation(
                id=f"{l['source']}_{l['target']}",
                source_id=str(l['source']),
                target_id=str(l['target']),
                type=RelationType(l['type']) if l['type'] in RelationType.__members__ else RelationType.RELATES_TO,
                weight=1.0
            ))
        except Exception as e:
            logger.warning(f"关系转换失败: {l}, {e}")

    return MemoryGraphData(
        nodes=nodes,
        links=links,
        total_nodes=len(nodes),
        total_links=len(links)
    )


@router.post("/search", response_model=List[MemorySearchResult])
async def search_memories(
    request: MemorySearchRequest,
    user: User = Depends(require_user)
):
    """
    搜索记忆节点（从 ChromaDB 获取）
    """
    service = get_memory_service()
    
    # 转换为向量存储搜索参数
    # 如果指定了类型，目前 VectorStore 可能还没支持类型过滤，我们需要在查询后过滤
    try:
        results = service.vector_store.search(
            query=request.query,
            limit=request.limit or 10
        )
        
        # 转换为 MemorySearchResult
        search_results = []
        for res in results:
            node = MemoryNode(
                id=res.get("id"),
                type=MemoryType.CONCEPT,
                label=res.get("metadata", {}).get("name", "Unknown"),
                content=res.get("document", ""),
                metadata=res.get("metadata", {}),
                importance=0.5
            )
            search_results.append(MemorySearchResult(
                node=node,
                score=res.get("score", 0.0)
            ))
        
        return search_results
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats")
async def get_memory_stats(user: User = Depends(require_user)):
    """获取记忆图谱统计数据"""
    try:
        memory_service = get_memory_service()
        stats = await asyncio.get_event_loop().run_in_executor(
            None, memory_service.graph_store.get_stats
        )
        return stats
    except Exception as e:
        logger.error(f"获取统计数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/clear")
async def clear_memory(user: User = Depends(require_user)):
    """清除所有记忆数据"""
    try:
        memory_service = get_memory_service()
        # 确保调用的是 clear_all_memories
        # 同时清除任务数据库
        _tasks_db.clear()
        
        await asyncio.get_event_loop().run_in_executor(
            None, memory_service.clear_all_memories
        )
        return {"status": "success", "message": "所有记忆数据已清除"}
    except Exception as e:
        logger.error(f"清除记忆失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

