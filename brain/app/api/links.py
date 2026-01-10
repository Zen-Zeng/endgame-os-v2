"""
神经链接 API 路由
支持手动建立知识/目标间的拓扑连接，并提供基于向量相似度的链接推荐。
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional, Dict, Any
import numpy as np

from ..models.user import User
from .auth import require_user
from ..services.memory.memory_service import get_memory_service
from ..models.memory import RelationType

router = APIRouter()

# ============ Models ============

class LinkCreateRequest(Dict[str, Any]):
    """创建链接请求"""
    source_id: str
    target_id: str
    relation: str = "relates_to"
    strength: float = 1.0

# ============ API 端点 ============

@router.post("/connect")
async def create_manual_link(request: Dict[str, Any], user: User = Depends(require_user)):
    """手动建立两个节点间的神经链接"""
    service = get_memory_service()
    
    source = request.get("source")
    target = request.get("target")
    relation = request.get("relation", "relates_to")
    
    if not source or not target:
        raise HTTPException(status_code=400, detail="必须提供源节点和目标节点名称或ID")
        
    success = service.graph_store.upsert_relations_batch(user.id, [{
        "source": source,
        "target": target,
        "relation": relation,
        "properties": {"manual": True, "strength": request.get("strength", 1.0)}
    }])
    
    if not success:
        raise HTTPException(status_code=500, detail="建立链接失败")
        
    return {"status": "success", "message": f"已建立连接: {source} --[{relation}]--> {target}"}

@router.get("/recommendations")
async def get_link_recommendations(
    node_id: str, 
    limit: int = 5,
    user: User = Depends(require_user)
):
    """
    基于向量相似度的链接推荐
    找到语义上最接近但尚未建立连接的节点
    """
    service = get_memory_service()
    
    # 1. 获取目标节点的向量
    target_vector = service.vector_store.get_vector(node_id)
    if target_vector is None:
        return []
        
    # 2. 在向量库中搜索相似节点
    similar_nodes = service.vector_store.search(target_vector, limit=limit + 5)
    
    # 3. 过滤掉自身和已经建立连接的节点
    recommendations = []
    # 这里简单处理，实际应检查 graph_store 是否已有边
    for node in similar_nodes:
        if node['id'] != node_id:
            recommendations.append({
                "node_id": node['id'],
                "name": node.get('metadata', {}).get('name', '未知'),
                "similarity": node.get('score', 0),
                "reason": "语义相关性高"
            })
            
    return recommendations[:limit]

@router.get("/topology/{node_id}")
async def get_node_topology(node_id: str, depth: int = 1, user: User = Depends(require_user)):
    """获取某个节点周边的拓扑结构（用于局部编辑）"""
    service = get_memory_service()
    
    # 这是一个简化实现，实际需要 graph_store 支持多层查询
    # 目前先返回该节点的所有直接邻居
    with service.graph_store._get_conn() as conn:
        # 查出边
        out_edges = conn.execute(
            "SELECT target as id, relation FROM edges WHERE source = ? AND user_id = ?",
            (node_id, user.id)
        ).fetchall()
        
        # 查入边
        in_edges = conn.execute(
            "SELECT source as id, relation FROM edges WHERE target = ? AND user_id = ?",
            (node_id, user.id)
        ).fetchall()
        
    nodes = [{"id": node_id, "main": True}]
    links = []
    
    for e in out_edges:
        nodes.append({"id": e['id']})
        links.append({"source": node_id, "target": e['id'], "relation": e['relation']})
        
    for e in in_edges:
        nodes.append({"id": e['id']})
        links.append({"source": e['id'], "target": node_id, "relation": e['relation']})
        
    return {"nodes": nodes, "links": links}
