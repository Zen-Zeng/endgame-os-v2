"""
记忆图谱 API 路由
处理知识图谱的查询、创建和可视化
"""
from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from typing import List, Optional, Dict, Any
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

from concurrent.futures import ThreadPoolExecutor

router = APIRouter()

# 共享任务状态数据库
_tasks_db: Dict[str, Dict] = {}  # task_id -> task_status

# 专用线程池用于处理重型 NLP 任务，避免阻塞主 API 线程池
# 限制为 1 个 worker 也是为了防止 GPU/显存 竞争导致卡顿
training_executor = ThreadPoolExecutor(max_workers=1)

logger = logging.getLogger(__name__)

async def _process_training_task(task_id: str, filename: str, user_id: str):
    """异步处理训练任务，调用真实的 MemoryService"""
    try:
        service = get_memory_service()
        loop = asyncio.get_event_loop()
        
        _tasks_db[task_id]["status"] = "processing"
        _tasks_db[task_id]["progress"] = 10
        _tasks_db[task_id]["message"] = "正在解析文档..."
        
        # 定义进度回调
        def on_progress(p, msg):
            # 使用 call_soon_threadsafe 确保在主循环中更新状态
            loop.call_soon_threadsafe(
                lambda: _tasks_db[task_id].update({"progress": p, "message": msg})
            )

        # 获取完整文件路径
        file_path = UPLOAD_DIR / filename
        
        # 如果不存在，尝试在所有子目录中查找
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
        _tasks_db[task_id]["message"] = "正在初始化模型并提取实体..."
        
        # 调用真实的 ingest_file (使用专用线程池)
        # 传递 user_id 确保数据存入正确用户名下
        result = await loop.run_in_executor(
            training_executor, 
            service.ingest_file, 
            str(file_path), 
            user_id, 
            on_progress
        )
        
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
    request: Dict[str, Any],
    background_tasks: BackgroundTasks,
    user: User = Depends(require_user)
):
    """
    开始记忆训练任务
    支持单个文件或多个文件批量训练
    """
    filenames = request.get("filenames", [])
    if not filenames and "filename" in request:
        filenames = [request["filename"]]
    
    if not filenames:
        raise HTTPException(status_code=400, detail="未指定训练文件")
    
    task_id = str(uuid.uuid4())
    _tasks_db[task_id] = {
        "id": task_id,
        "status": "pending",
        "progress": 0,
        "message": "任务已排队",
        "created_at": datetime.now().isoformat()
    }
    
    # 启动后台处理
    background_tasks.add_task(_process_batch_training, task_id, filenames, user.id)
    
    return {"task_id": task_id}

async def _process_batch_training(task_id: str, filenames: List[str], user_id: str):
    """批量处理训练任务"""
    total_files = len(filenames)
    try:
        for i, filename in enumerate(filenames):
            # 更新总体进度
            base_progress = int((i / total_files) * 100)
            _tasks_db[task_id]["message"] = f"正在处理第 {i+1}/{total_files} 个文件: {filename}"
            _tasks_db[task_id]["progress"] = base_progress
            
            # 调用原有的处理逻辑（复用 _process_training_task 的核心部分）
            await _process_single_file_in_batch(task_id, filename, user_id, base_progress, 100 // total_files)
            
        _tasks_db[task_id]["status"] = "completed"
        _tasks_db[task_id]["progress"] = 100
        _tasks_db[task_id]["message"] = "批量训练全部完成"
        
    except Exception as e:
        logger.error(f"Batch training task {task_id} failed: {str(e)}")
        _tasks_db[task_id]["status"] = "failed"
        _tasks_db[task_id]["error"] = str(e)
        _tasks_db[task_id]["message"] = f"批量训练中断: {str(e)}"

async def _process_single_file_in_batch(task_id: str, filename: str, user_id: str, base_progress: int, weight: int):
    """在批量任务中处理单个文件"""
    service = get_memory_service()
    loop = asyncio.get_event_loop()
    
    # 查找文件路径
    file_path = UPLOAD_DIR / user_id / filename
    if not file_path.exists():
        # 兼容性查找
        for user_dir in UPLOAD_DIR.iterdir():
            if user_dir.is_dir():
                potential_path = user_dir / filename
                if potential_path.exists():
                    file_path = potential_path
                    break
    
    if not file_path.exists():
        logger.warning(f"文件不存在，跳过: {filename}")
        return

    # 简单的进度回调映射
    def on_progress(p, msg):
        current_p = base_progress + int((p / 100) * weight)
        loop.call_soon_threadsafe(
            lambda: _tasks_db[task_id].update({"progress": current_p, "message": f"[{filename}] {msg}"})
        )

    # 执行训练
    await loop.run_in_executor(
        training_executor, 
        service.ingest_file, 
        str(file_path), 
        user_id, 
        on_progress
    )

    # 训练成功后，更新 archives_files.json 中的状态
    try:
        from .archives import _files_db, _save_db, FILES_FILE
        # 查找对应的文件 ID
        file_id = None
        for fid, fdoc in _files_db.items():
            if fdoc.get("filename") == filename and fdoc.get("user_id") == user_id:
                file_id = fid
                break
        
        if file_id:
            _files_db[file_id]["is_processed"] = True
            _files_db[file_id]["updated_at"] = datetime.now().isoformat()
            _save_db(FILES_FILE, _files_db)
            logger.info(f"已更新文件状态为已训练: {filename} (ID: {file_id})")
    except Exception as e:
        logger.error(f"更新文件训练状态失败: {e}")

@router.get("/tasks/{task_id}")
@router.get("/train/status/{task_id}")
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
    try:
        service = get_memory_service()
        # 显式传递参数，解决某些环境下 run_in_executor 丢失参数的问题
        graph_data = await asyncio.get_event_loop().run_in_executor(
            None, lambda: service.graph_store.get_all_graph_data(user_id=user.id)
        )
        
        # 转换为 Pydantic 模型
        nodes = []
        # 获取有效的 MemoryType 值列表
        valid_memory_types = {t.value for t in MemoryType}
        
        for n in graph_data.get("nodes", []):
            try:
                # 确保类型转换正确
                node_type = n.get("type")
                if node_type not in valid_memory_types:
                    node_type = MemoryType.CONCEPT.value
                    
                nodes.append(MemoryNode(
                    id=str(n.get("id")),
                    type=node_type,
                    label=n.get("label", "Unknown"),
                    content=n.get("content", ""),
                    metadata={"group": n.get("group", 5)}
                ))
            except Exception as e:
                logger.warning(f"节点转换失败: {n.get('id')}, {e}")

        links = []
        valid_relation_types = {t.value for t in RelationType}
        
        for l in graph_data.get("links", []):
            try:
                # 格式转换以匹配 MemoryRelation 模型
                rel_type = l.get('type')
                if rel_type not in valid_relation_types:
                    rel_type = RelationType.RELATES_TO.value
                    
                links.append(MemoryRelation(
                    id=f"{l['source']}_{l['target']}",
                    source=str(l['source']),
                    target=str(l['target']),
                    type=rel_type,
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
    except Exception as e:
        logger.error(f"获取图谱数据失败: {e}")
        # 即使失败也返回空数据结构，而不是 500
        return MemoryGraphData(nodes=[], links=[], total_nodes=0, total_links=0)


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
    """获取记忆库综合统计数据"""
    try:
        memory_service = get_memory_service()
        stats = await asyncio.get_event_loop().run_in_executor(
            None, lambda: memory_service.get_stats(user_id=user.id)
        )
        
        # 获取正在进行的任务数
        active_tasks = sum(1 for t in _tasks_db.values() if t.get("status") in ["pending", "processing"])
        
        return {
            "success": True,
            "active_tasks": active_tasks,
            **stats
        }
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
            None, lambda: memory_service.clear_all_memories(user_id=user.id)
        )
        return {"status": "success", "message": "所有记忆数据已清除"}
    except Exception as e:
        logger.error(f"清除记忆失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

