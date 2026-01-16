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

import json
from ..models.memory import (
    MemoryNode, MemoryRelation, MemoryType, RelationType,
    MemorySearchResult, MemoryGraphData, MemoryCreateRequest, MemorySearchRequest
)
from ..models.user import User
from .auth import require_user

from ..services.memory.memory_service import get_memory_service
from ..services.ingestion.service import get_ingestion_service
from ..core.config import UPLOAD_DIR

# 移除 ThreadPoolExecutor，不再需要

router = APIRouter()

# 共享任务状态数据库
_tasks_db: Dict[str, Dict] = {}  # task_id -> task_status

logger = logging.getLogger(__name__)

async def _process_training_task(task_id: str, filename: str, user_id: str):
    """异步处理训练任务，调用 IngestionService"""
    try:
        service = get_ingestion_service()
        
        _tasks_db[task_id]["status"] = "processing"
        _tasks_db[task_id]["progress"] = 10
        _tasks_db[task_id]["message"] = "正在解析文档..."
        
        def on_progress(p, msg):
            # 直接更新状态 (因为现在是 async 环境，不需要 threadsafe)
            _tasks_db[task_id].update({"progress": p, "message": msg})

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
        
        # 1. 调用 ingest_file (异步)
        result = await service.ingest_file(str(file_path), user_id, on_progress)
        
        if result.get("success"):
            # 2. 如果有图谱任务，继续执行 (串行化处理，确保完成后再标记 task completed)
            if "deepseek_task_args" in result:
                _tasks_db[task_id]["message"] = "DeepSeek 正在结构化记忆..."
                args = result["deepseek_task_args"]
                # 传入进度回调
                await service.process_deepseek_pipeline(*args, progress_callback=on_progress)
            elif "graph_task_args" in result:
                _tasks_db[task_id]["message"] = "正在提取知识图谱..."
                args = result["graph_task_args"]
                await service.process_graph_task(*args)
            
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
            
            # 处理单个文件
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
    service = get_ingestion_service()
    
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

    # 进度回调
    def on_progress(p, msg):
        current_p = base_progress + int((p / 100) * weight)
        _tasks_db[task_id].update({"progress": current_p, "message": f"[{filename}] {msg}"})

    # 执行训练 (异步)
    result = await service.ingest_file(str(file_path), user_id, on_progress)
    
    if result.get("success"):
        # 执行后续图谱任务
        if "deepseek_task_args" in result:
             # 更新消息
            _tasks_db[task_id]["message"] = f"[{filename}] DeepSeek 正在结构化..."
            args = result["deepseek_task_args"]
            await service.process_deepseek_pipeline(*args)
        elif "graph_task_args" in result:
             # 更新消息
            _tasks_db[task_id]["message"] = f"[{filename}] 正在提取知识图谱..."
            args = result["graph_task_args"]
            await service.process_graph_task(*args)
            
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
    view_type: str = Query(default="global", description="图谱视图类型: global, strategic, people"),
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
            None, lambda: service.graph_store.get_all_graph_data(user_id=user.id, view_type=view_type)
        )
        
        # [Strategic Brain] 确保默认节点存在 (Self & Vision)
        # 如果图谱为空，或者缺少核心节点，则自动同步
        has_self = any(n.get("type") == "Self" for n in graph_data.get("nodes", []))
        if not has_self:
            logger.info(f"检测到用户 {user.id} 缺少核心节点，正在初始化...")
            vision_data = user.vision.model_dump() if user.vision else None
            persona_data = user.persona.model_dump() if user.persona else None
            await asyncio.get_event_loop().run_in_executor(
                None, 
                lambda: service.graph_store.sync_user_to_self_node(user.id, vision_data, persona_data)
            )
            # 重新获取数据
            graph_data = await asyncio.get_event_loop().run_in_executor(
                None, lambda: service.graph_store.get_all_graph_data(user_id=user.id, view_type=view_type)
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
                    alignment_score=n.get("alignment_score", 0.0),
                    metadata={"group": n.get("group", 5)}
                ))
            except Exception as e:
                logger.warning(f"节点转换失败: {n.get('id')}, {e}")

        links = []
        valid_relation_types = {t.value for t in RelationType}
        
        # 计算类型分布
        type_counts = {}
        for n in nodes:
            t = n.type
            type_counts[t] = type_counts.get(t, 0) + 1

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
            total_links=len(links),
            type_counts=type_counts
        )
    except Exception as e:
        logger.error(f"获取图谱数据失败: {e}")
        # 即使失败也返回空数据结构，而不是 500
        return MemoryGraphData(nodes=[], links=[], total_nodes=0, total_links=0, type_counts={})


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

@router.get("/pending", response_model=List[MemoryNode])
async def get_pending_memories(user: User = Depends(require_user)):
    """
    [Strategic Brain] 获取待确认的记忆节点
    """
    service = get_memory_service()
    try:
        # 查询 status='pending' 的节点
        with service.graph_store._get_conn() as conn:
            # 兼容性处理：如果表没有 status 列，这里会报错，需要 try-catch
            try:
                rows = conn.execute(
                    "SELECT id, type, name, content, attributes FROM nodes WHERE user_id=? AND status='pending'",
                    (user.id,)
                ).fetchall()
            except Exception:
                # 可能是旧表结构
                return []
            
            result = []
            for r in rows:
                result.append(MemoryNode(
                    id=r['id'],
                    type=r['type'],
                    label=r['name'] or "Unknown",
                    content=r['content'],
                    metadata=json.loads(r['attributes']) if r['attributes'] else {},
                    status="pending"
                ))
            return result
    except Exception as e:
        logger.error(f"Get pending memories failed: {e}")
        return []

@router.post("/confirm/{node_id}")
async def confirm_memory(node_id: str, action: str = Query(..., pattern="^(confirm|reject)$"), user: User = Depends(require_user)):
    """
    [Strategic Brain] 确认或拒绝记忆节点
    action=confirm: 状态改为 confirmed
    action=reject: 删除节点
    """
    service = get_memory_service()
    try:
        with service.graph_store._lock, service.graph_store._get_conn() as conn:
            if action == "confirm":
                conn.execute(
                    "UPDATE nodes SET status='confirmed' WHERE id=? AND user_id=?",
                    (node_id, user.id)
                )
                message = "记忆已确认"
            else:
                # 级联删除相关边
                conn.execute("DELETE FROM edges WHERE (source=? OR target=?) AND user_id=?", (node_id, node_id, user.id))
                conn.execute("DELETE FROM nodes WHERE id=? AND user_id=?", (node_id, user.id))
                message = "记忆已拒绝并删除"
                
            return {"success": True, "message": message}
    except Exception as e:
        logger.error(f"Confirm memory failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/nodes", response_model=List[MemoryNode])
async def get_nodes(
    type: Optional[str] = Query(None, description="节点类型过滤"),
    user: User = Depends(require_user)
):
    """获取节点列表"""
    service = get_memory_service()
    try:
        if type:
            nodes = await asyncio.get_event_loop().run_in_executor(
                None, lambda: service.graph_store.get_nodes_by_type(user_id=user.id, node_type=type)
            )
        else:
            # 如果没传类型，默认获取全部（慎用）
            graph_data = await asyncio.get_event_loop().run_in_executor(
                None, lambda: service.graph_store.get_all_graph_data(user_id=user.id)
            )
            nodes = graph_data.get("nodes", [])
            
        result = []
        for n in nodes:
            result.append(MemoryNode(
                id=str(n["id"]),
                type=n["type"],
                label=n.get("name") or n.get("label") or "Unknown",
                content=n.get("content", ""),
                alignment_score=n.get("alignment_score", 0.0)
            ))
        return result
    except Exception as e:
        logger.error(f"获取节点列表失败: {e}")
        return []

@router.delete("/nodes/{node_id}")
async def delete_node(node_id: str, user: User = Depends(require_user)):
    """删除正式库中的节点及其关联边"""
    service = get_memory_service()
    try:
        with service.graph_store._lock, service.graph_store._get_conn() as conn:
            # 1. 级联删除相关边
            conn.execute("DELETE FROM edges WHERE (source = ? OR target = ?) AND user_id = ?", (node_id, node_id, user.id))
            # 2. 删除节点
            conn.execute("DELETE FROM nodes WHERE id = ? AND user_id = ?", (node_id, user.id))
            return {"success": True, "message": "节点已成功从知识图谱中删除"}
    except Exception as e:
        logger.error(f"删除节点失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/edges")
async def create_edge(
    request: Dict[str, Any],
    user: User = Depends(require_user)
):
    """创建或更新关系"""
    source = request.get("source")
    target = request.get("target")
    relation = request.get("relation", "RELATES_TO")
    
    if not source or not target:
        raise HTTPException(status_code=400, detail="必须提供 source 和 target")
        
    service = get_memory_service()
    try:
        with service.graph_store._lock, service.graph_store._get_conn() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO edges (source, target, relation, user_id)
                VALUES (?, ?, ?, ?)
            """, (source, target, relation, user.id))
            return {"success": True, "message": "关系已创建/更新"}
    except Exception as e:
        logger.error(f"创建关系失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============ Memory Airlock (暂存区) API ============

@router.get("/staging")
async def get_staging_memories(user: User = Depends(require_user)):
    """获取暂存区数据"""
    service = get_memory_service()
    data = service.graph_store.get_staging_data(user.id)
    return data

@router.post("/staging/commit")
async def commit_staging_memories(
    request: Dict[str, Any],
    user: User = Depends(require_user)
):
    """
    将暂存区的节点确认入库
    request: { "node_ids": ["id1", "id2"] } 或不传表示全部
    """
    node_ids = request.get("node_ids")
    service = get_memory_service()
    
    try:
        with service.graph_store._lock, service.graph_store._get_conn() as conn:
            # 1. 获取要入库的节点
            query = "SELECT * FROM staging_nodes WHERE user_id = ?"
            params = [user.id]
            if node_ids:
                query += f" AND id IN ({','.join(['?']*len(node_ids))})"
                params.extend(node_ids)
            
            nodes = conn.execute(query, params).fetchall()
            
            # 2. 插入正式表
            for n in nodes:
                nid = n["id"]
                ntype = n["type"]
                
                # [Strategic Brain] 强一致性 ID 归一化: Vision 和 Self 节点
                if ntype == "Vision":
                    nid = f"vision_{user.id}"
                elif ntype == "Self":
                    nid = user.id
                
                conn.execute("""
                    INSERT OR REPLACE INTO nodes (id, user_id, type, name, content, attributes, source_file)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (nid, user.id, ntype, n["name"], n["content"], n["attributes"], n["source_file"]))
            
            # 3. 获取相关的边
            # 这里简单起见，只要源和目标都在已确认节点中的边都入库
            # 如果 node_ids 为空，则全部入库
            if node_ids:
                placeholders = ','.join(['?']*len(node_ids))
                edges = conn.execute(f"""
                    SELECT * FROM staging_edges 
                    WHERE user_id = ? AND source IN ({placeholders}) AND target IN ({placeholders})
                """, [user.id] + node_ids + node_ids).fetchall()
            else:
                edges = conn.execute("SELECT * FROM staging_edges WHERE user_id = ?", (user.id,)).fetchall()
                
            for e in edges:
                conn.execute("""
                    INSERT OR IGNORE INTO edges (source, target, relation, user_id)
                    VALUES (?, ?, ?, ?)
                """, (e["source"], e["target"], e["relation"], user.id))
            
            # 4. 从暂存区删除
            if node_ids:
                conn.execute(f"DELETE FROM staging_nodes WHERE user_id = ? AND id IN ({placeholders})", [user.id] + node_ids)
                # 边不好精准删除，通常 commit 完就清空 staging 比较好，或者根据 commit 的节点清理
            else:
                conn.execute("DELETE FROM staging_nodes WHERE user_id = ?", (user.id,))
                conn.execute("DELETE FROM staging_edges WHERE user_id = ?", (user.id,))
                
            return {"success": True, "message": f"成功入库 {len(nodes)} 个节点和 {len(edges)} 条关系"}
    except Exception as e:
        logger.error(f"Commit staging failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/staging/merge")
async def merge_staging_nodes(
    request: Dict[str, Any],
    user: User = Depends(require_user)
):
    """
    合并暂存区的两个节点 (Human-in-the-loop)
    request: { "source_id": "被合并ID", "target_id": "保留ID" }
    """
    source_id = request.get("source_id")
    target_id = request.get("target_id")
    
    if not source_id or not target_id:
        raise HTTPException(status_code=400, detail="Missing source_id or target_id")
        
    service = get_memory_service()
    try:
        with service.graph_store._lock, service.graph_store._get_conn() as conn:
            # 1. 更新暂存区的边：将所有指向 source_id 的边改为指向 target_id
            conn.execute("UPDATE staging_edges SET source = ? WHERE source = ? AND user_id = ?", (target_id, source_id, user.id))
            conn.execute("UPDATE staging_edges SET target = ? WHERE target = ? AND user_id = ?", (target_id, source_id, user.id))
            
            # 2. 删除 source 节点
            conn.execute("DELETE FROM staging_nodes WHERE id = ? AND user_id = ?", (source_id, user.id))
            
            return {"success": True, "message": "节点合并成功"}
    except Exception as e:
        logger.error(f"Merge staging nodes failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/staging")
async def clear_staging_area(user: User = Depends(require_user)):
    """清空暂存区"""
    service = get_memory_service()
    if service.graph_store.clear_staging(user.id):
        return {"success": True}
    else:
        raise HTTPException(status_code=500, detail="Failed to clear staging")

@router.patch("/staging/nodes/{node_id}")
async def update_staging_node(
    node_id: str,
    request: Dict[str, Any],
    user: User = Depends(require_user)
):
    """
    更新暂存区的节点信息 (Human-in-the-loop)
    request: { "name": "新名称", "content": "新内容", "type": "新类型" }
    """
    name = request.get("name")
    content = request.get("content")
    node_type = request.get("type")
    
    service = get_memory_service()
    try:
        with service.graph_store._lock, service.graph_store._get_conn() as conn:
            update_fields = []
            params = []
            
            if name is not None:
                update_fields.append("name = ?")
                params.append(name)
            if content is not None:
                update_fields.append("content = ?")
                params.append(content)
            if node_type is not None:
                update_fields.append("type = ?")
                params.append(node_type)
                
            if not update_fields:
                return {"success": True, "message": "无变更"}
                
            query = f"UPDATE staging_nodes SET {', '.join(update_fields)} WHERE id = ? AND user_id = ?"
            params.extend([node_id, user.id])
            
            conn.execute(query, params)
            return {"success": True, "message": "节点更新成功"}
    except Exception as e:
        logger.error(f"Update staging node failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/staging/nodes/{node_id}")
async def delete_staging_node(
    node_id: str,
    user: User = Depends(require_user)
):
    """
    从暂存区删除节点 (Human-in-the-loop)
    """
    service = get_memory_service()
    try:
        with service.graph_store._lock, service.graph_store._get_conn() as conn:
            # 1. 级联删除相关边
            conn.execute("DELETE FROM staging_edges WHERE (source = ? OR target = ?) AND user_id = ?", (node_id, node_id, user.id))
            # 2. 删除节点
            conn.execute("DELETE FROM staging_nodes WHERE id = ? AND user_id = ?", (node_id, user.id))
            return {"success": True, "message": "节点已删除"}
    except Exception as e:
        logger.error(f"Delete staging node failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/lineage/{filename}")
async def get_file_lineage(
    filename: str,
    user: User = Depends(require_user)
):
    """
    获取档案的战略贡献链 (Lineage)
    返回该档案生成的所有节点（包括暂存区和正式库）
    """
    service = get_memory_service()
    try:
        with service.graph_store._get_conn() as conn:
            # 1. 查询暂存区节点
            staging_nodes = conn.execute(
                "SELECT id, name, type, 'staging' as source_table FROM staging_nodes WHERE user_id = ? AND source_file = ?",
                (user.id, filename)
            ).fetchall()
            
            # 2. 查询正式库节点
            confirmed_nodes = conn.execute(
                "SELECT id, name, type, 'confirmed' as source_table FROM nodes WHERE user_id = ? AND source_file = ?",
                (user.id, filename)
            ).fetchall()
            
            # 3. 合并结果
            nodes = []
            for n in staging_nodes:
                nodes.append({"id": n["id"], "name": n["name"], "type": n["type"], "status": "pending"})
            for n in confirmed_nodes:
                nodes.append({"id": n["id"], "name": n["name"], "type": n["type"], "status": "confirmed"})
                
            return {"filename": filename, "nodes": nodes}
    except Exception as e:
        logger.error(f"Get file lineage failed: {e}")
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
        
        # [Strategic Brain] 1. 清空后重新建立默认的 Self 和 Vision 节点
        try:
            vision_data = user.vision.model_dump() if user.vision else None
            persona_data = user.persona.model_dump() if user.persona else None
            await asyncio.get_event_loop().run_in_executor(
                None, 
                lambda: memory_service.graph_store.sync_user_to_self_node(user.id, vision_data, persona_data)
            )
        except Exception as sync_e:
            logger.error(f"Sync Self Node Error after clear: {sync_e}")
            
        # [Strategic Brain] 2. 重置档案库状态为全新未训练状态 (is_processed = False)
        try:
            from .archives import _files_db, _save_db, FILES_FILE
            changed = False
            for fid, fdoc in _files_db.items():
                if fdoc.get("user_id") == user.id and fdoc.get("is_processed"):
                    fdoc["is_processed"] = False
                    fdoc["updated_at"] = datetime.now().isoformat()
                    _files_db[fid] = fdoc
                    changed = True
            
            if changed:
                _save_db(FILES_FILE, _files_db)
                logger.info(f"档案库状态已重置为未训练状态 (User: {user.id})")
        except Exception as archive_e:
            logger.error(f"Reset archive status error: {archive_e}")

        return {"status": "success", "message": "所有记忆数据已清除，已重建初始节点，并重置档案库状态"}
    except Exception as e:
        logger.error(f"清除记忆失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
