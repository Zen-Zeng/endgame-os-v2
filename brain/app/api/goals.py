"""
目标管理 API 路由
支持愿景 -> 目标 -> 项目 -> 任务的层级管理，并深度集成 H3 能量系统。
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional, Dict, Any
from datetime import datetime, date
import uuid

from ..models.memory import (
    MemoryNode, MemoryType, RelationType, MemoryCreateRequest
)
from ..models.user import User
from .auth import require_user
from ..services.memory.memory_service import get_memory_service
from ..core.db import db_manager

router = APIRouter()

# ============ Request/Response Models ============

class GoalCreateRequest(MemoryCreateRequest):
    """创建目标请求"""
    type: MemoryType = MemoryType.GOAL
    deadline: Optional[str] = None
    priority: str = "medium" # high, medium, low

class ProjectCreateRequest(MemoryCreateRequest):
    """创建项目请求"""
    type: MemoryType = MemoryType.PROJECT
    parent_goal_id: str
    tech_stack: List[str] = []

class TaskCreateRequest(MemoryCreateRequest):
    """创建任务请求"""
    type: MemoryType = MemoryType.TASK
    parent_project_id: str
    intensity: int = 3 # 1-5, 5为最高强度
    estimated_hours: float = 1.0

# ============ 辅助函数 ============

def _check_h3_threshold(user_id: str, intensity: int) -> bool:
    """
    H3 能量联动校验逻辑
    强度 4-5 的任务需要 body/mind 平均分 > 50
    """
    history = db_manager.get_h3_energy_history(user_id, 1)
    if not history:
        return True # 没有数据时不阻塞，但建议校准
    
    current = history[0]
    avg_energy = (current['body'] + current['mind']) / 2
    
    if intensity >= 4 and avg_energy < 50:
        return False
    return True

# ============ API 端点 ============

@router.get("/list", response_model=List[Dict[str, Any]])
async def list_goals(user: User = Depends(require_user)):
    """获取所有目标及其进度"""
    service = get_memory_service()
    goals = service.graph_store.get_nodes_by_type(user.id, MemoryType.GOAL.value)
    
    # 丰富目标数据：获取子项目
    result = []
    for g in goals:
        g_dict = dict(g)
        # 获取关联的项目
        projects = service.graph_store.get_sub_entities(user.id, g['id'], RelationType.HAS_PROJECT.value)
        g_dict['projects_count'] = len(projects)
        g_dict['projects'] = projects
        result.append(g_dict)
        
    return result

@router.post("/goal", response_model=Dict[str, Any])
async def create_goal(request: GoalCreateRequest, user: User = Depends(require_user)):
    """创建新目标"""
    service = get_memory_service()
    node_id = f"goal_{uuid.uuid4().hex[:8]}"
    
    # 构建档案信息
    dossier = {
        "status": "active",
        "deadline": request.deadline,
        "priority": request.priority,
        "created_at": datetime.now().isoformat()
    }
    
    success = service.graph_store.upsert_entities_batch(user.id, [{
        "name": request.label,
        "type": MemoryType.GOAL.value,
        "content": request.content or "",
        "dossier": dossier
    }])
    
    if not success:
        raise HTTPException(status_code=500, detail="创建目标失败")
        
    return {"id": node_id, "status": "success"}

@router.post("/task", response_model=Dict[str, Any])
async def create_task(request: TaskCreateRequest, user: User = Depends(require_user)):
    """
    创建任务，并执行 H3 能量联动校验
    """
    # 1. 能量校验
    if not _check_h3_threshold(user.id, request.intensity):
        raise HTTPException(
            status_code=403, 
            detail={
                "error": "ENERGY_LOW",
                "message": f"当前 H3 能量状态较低（心智/身体平均分不足 50），不建议启动强度为 {request.intensity} 的任务。请先进行休息或能量校准。",
                "intensity": request.intensity
            }
        )
    
    service = get_memory_service()
    task_id = f"task_{uuid.uuid4().hex[:8]}"
    
    # 2. 写入任务节点
    dossier = {
        "status": "todo",
        "intensity": request.intensity,
        "estimated_hours": request.estimated_hours,
        "created_at": datetime.now().isoformat()
    }
    
    success = service.graph_store.upsert_entities_batch(user.id, [{
        "name": request.label,
        "type": MemoryType.TASK.value,
        "content": request.content or "",
        "dossier": dossier
    }])
    
    if success:
        # 3. 建立与项目的连接
        project_node_id = request.parent_project_id
        task_node_id = service.graph_store._get_stable_id(request.label)
        service.graph_store.upsert_relations_batch(user.id, [{
            "source_id": project_node_id, # 注意：这里假设前端传的是 ID，但 graph_store 可能期望 name
            "source": project_node_id,
            "target": request.label,
            "relation": RelationType.HAS_TASK.value
        }])
        
    return {"id": task_id, "status": "success"}

@router.get("/stats")
async def get_goal_stats(user: User = Depends(require_user)):
    """获取目标达成统计"""
    service = get_memory_service()
    stats = service.graph_store.get_stats(user.id)
    
    node_counts = stats.get("node_counts", {})
    return {
        "goals": node_counts.get("Goal", 0),
        "projects": node_counts.get("Project", 0),
        "tasks": node_counts.get("Task", 0)
    }
