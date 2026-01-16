"""
Strategic Brain Graph API
提供 OKR + 时间轴视角的图谱查询接口
"""
from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

from ..api.auth import require_user
from ..models.user import User
from ..services.memory.memory_service import get_memory_service

router = APIRouter()

class StrategicNode(BaseModel):
    id: str
    type: str
    label: str
    status: str
    content: Optional[str] = None
    day_offset: Optional[int] = None
    data: Dict[str, Any] = {}
    children: List['StrategicNode'] = [] # 树状结构

StrategicNode.model_rebuild()

class StrategicGraphResponse(BaseModel):
    root: StrategicNode
    stats: Dict[str, int]

@router.get("/strategic", response_model=StrategicGraphResponse)
async def get_strategic_graph(user: User = Depends(require_user)):
    """
    获取战略视图图谱 (Tree Structure)
    Self -> Vision -> Goal -> Project -> Task
    """
    service = get_memory_service()
    graph = service.graph_store
    
    # 1. 获取所有节点和边
    try:
        # 使用 strategic 视图模式，确保获取完整的执行层级节点 (Vision -> Action)
        raw_data = graph.get_all_graph_data(user.id, view_type='strategic')
        nodes_map = {n['id']: n for n in raw_data.get('nodes', [])}
        links = raw_data.get('links', [])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Graph query failed: {e}")

    # 2. 构建 Self 根节点
    self_node_id = user.id
    if self_node_id not in nodes_map:
        # 如果尚未同步，返回空壳
        return {
            "root": {
                "id": user.id,
                "type": "Self",
                "label": "Me",
                "status": "confirmed",
                "children": []
            },
            "stats": {}
        }

    # 3. 递归构建树
    # 预处理邻接表：Parent -> [Children]
    
    # 正向关系：Src 是 Parent，Tgt 是 Child
    FORWARD_RELATIONS = {
        "OWNS", "DECOMPOSES_TO", "ACHIEVED_BY", "CONSISTS_OF", "HAS_GOAL", "HAS_PROJECT",
        "USES", "REFERENCES", "MENTIONS", "RELATED_TO", "HAS_RELATION", "DEFINES", "IMPROVES", "INCLUDES", "MANAGES", "COMMUNICATED_WITH"
    }
    # 反向关系：Src 是 Child，Tgt 是 Parent (需要反转)
    REVERSE_RELATIONS = {
        "PART_OF", "BELONGS_TO", "WORKS_ON", "IS_A", "BASED_ON", "WORKS_FOR", "OWNED_BY"
    }
    
    adj_list = {}
    for link in links:
        src = link['source']
        tgt = link['target']
        rel = link['type']
        
        if rel in FORWARD_RELATIONS:
            if src not in adj_list: adj_list[src] = []
            adj_list[src].append(tgt)
        elif rel in REVERSE_RELATIONS:
            if tgt not in adj_list: adj_list[tgt] = []
            adj_list[tgt].append(src)
    
    def build_tree(node_id: str, visited: set) -> Dict[str, Any]:
        if node_id in visited: return None
        visited.add(node_id)
        
        node_data = nodes_map.get(node_id, {})
        # 转换节点格式
        node_out = {
            "id": node_id,
            "type": node_data.get("type", "Unknown"),
            "label": node_data.get("label", node_id),
            "status": node_data.get("attributes", {}).get("status", "confirmed"), # 兼容
            "content": node_data.get("content"),
            "data": node_data.get("data", {}),
            "children": []
        }
        
        # 查找子节点
        if node_id in adj_list:
            for child_id in adj_list[node_id]:
                child_tree = build_tree(child_id, visited.copy())
                if child_tree:
                    node_out["children"].append(child_tree)
                    
        return node_out

    root_tree = build_tree(self_node_id, set())
    
    return {
        "root": root_tree,
        "stats": {
            "total_nodes": len(nodes_map),
            "total_links": len(links)
        }
    }
