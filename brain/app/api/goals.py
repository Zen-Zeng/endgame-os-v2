"""
目标管理 API 路由
处理愿景、目标、项目和任务的 CRUD
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional, Dict, Any
from datetime import datetime, date
import uuid
import json
import logging

from ..models.user import User
from .auth import require_user
from ..services.memory.memory_service import get_memory_service
from pydantic import BaseModel, Field

router = APIRouter()
logger = logging.getLogger(__name__)

# ============ 数据模型 ============

class ProjectDossier(BaseModel):
    status: str = "active"
    sector: Optional[str] = None
    progress: int = 0
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())

class ProjectResponse(BaseModel):
    id: str
    name: str
    type: str = "Project"
    content: Optional[str] = ""
    tasks_count: int = 0
    dossier: ProjectDossier

class TaskDossier(BaseModel):
    status: str = "pending"
    priority: str = "medium"
    progress: int = 0
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())

class TaskResponse(BaseModel):
    id: str
    name: str
    type: str = "Task"
    content: Optional[str] = ""
    dossier: TaskDossier

class GoalDossier(BaseModel):
    status: str = "active"
    deadline: Optional[str] = None
    priority: str = "medium"
    progress: int = 0
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())

class GoalResponse(BaseModel):
    id: str
    name: str
    type: str = "Goal"
    content: Optional[str] = ""
    projects_count: int = 0
    projects: List[ProjectResponse] = []
    dossier: GoalDossier

class VisionResponse(BaseModel):
    id: str
    title: str
    description: str
    progress: int
    created_at: str

# ============ API 端点 ============

@router.get("/vision", response_model=Optional[VisionResponse])
async def get_vision(user: User = Depends(require_user)):
    """获取用户的终局愿景"""
    try:
        service = get_memory_service()
        # 1. 寻找 Vision 节点 (User --[OWNS]--> Vision)
        with service.graph_store._get_conn() as conn:
            row = conn.execute("""
                SELECT n.* FROM nodes n
                JOIN edges e ON n.id = e.target
                WHERE e.source = ? AND e.relation = 'OWNS' AND n.type = 'Vision'
                LIMIT 1
            """, (user.id,)).fetchone()
            
            if row:
                return VisionResponse(
                    id=row['id'],
                    title=row['name'],
                    description=row['content'] or "",
                    progress=int((row['alignment_score'] or 0) * 100),
                    created_at=row['created_at']
                )
        return None
    except Exception as e:
        logger.error(f"Failed to get vision: {e}")
        return None

@router.get("/list", response_model=List[GoalResponse])
async def list_goals(user: User = Depends(require_user)):
    """
    获取用户的目标列表 (归一化路径：User -> Vision -> Goal)
    """
    try:
        service = get_memory_service()
        goals = []
        
        with service.graph_store._get_conn() as conn:
            # 1. 尝试获取 Vision 节点
            vision_row = conn.execute("""
                SELECT target FROM edges 
                WHERE source = ? AND relation = 'OWNS' 
                LIMIT 1
            """, (user.id,)).fetchone()
            
            parent_id = vision_row['target'] if vision_row else user.id
            
            # 2. 获取挂载在 Vision 或 User 下的目标
            # 兼容两种关系：HAS_GOAL 或 DECOMPOSES_TO
            query = """
                SELECT n.* FROM nodes n
                JOIN edges e ON n.id = e.target
                WHERE e.source = ? AND (e.relation = 'HAS_GOAL' OR e.relation = 'DECOMPOSES_TO')
                AND n.type = 'Goal'
            """
            rows = conn.execute(query, (parent_id,)).fetchall()
            
            # 如果没有找到关联目标，则回退到查询所有类型为 Goal 的节点 (确保不漏掉孤立节点)
            if not rows:
                rows = conn.execute("SELECT * FROM nodes WHERE user_id = ? AND type = 'Goal'", (user.id,)).fetchall()

            for row in rows:
                attr = row['attributes']
                if isinstance(attr, str):
                    try:
                        attr = json.loads(attr)
                    except:
                        attr = {}
                
                # 获取关联项目数量
                p_count_row = conn.execute("""
                    SELECT COUNT(*) as count FROM edges 
                    WHERE source = ? AND (relation = 'HAS_PROJECT' OR relation = 'ACHIEVED_BY')
                """, (row['id'],)).fetchone()
                p_count = p_count_row['count'] if p_count_row else 0
                
                goals.append(GoalResponse(
                    id=row['id'],
                    name=row['name'],
                    type=row['type'],
                    content=row['content'] or "",
                    projects_count=p_count,
                    projects=[],
                    dossier=GoalDossier(
                        status=attr.get("status", "active"),
                        deadline=attr.get("deadline"),
                        priority=attr.get("priority", "medium"),
                        progress=attr.get("progress", 0),
                        created_at=row['created_at']
                    )
                ))
            
        return goals
    except Exception as e:
        logger.error(f"Failed to list goals: {e}")
        return []

@router.post("/create", response_model=GoalResponse)
async def create_goal(
    name: str, 
    content: Optional[str] = "", 
    priority: str = "medium",
    user: User = Depends(require_user)
):
    """
    创建新目标，并自动挂载到 Vision 节点
    """
    try:
        service = get_memory_service()
        goal_id = f"goal_{uuid.uuid4().hex[:8]}"
        
        with service.graph_store._get_conn() as conn:
            # 1. 寻找 Vision 节点
            vision_row = conn.execute("""
                SELECT target FROM edges 
                WHERE source = ? AND relation = 'OWNS' 
                LIMIT 1
            """, (user.id,)).fetchone()
            
            parent_id = vision_row['target'] if vision_row else user.id
            
            # 2. 创建目标节点
            service.graph_store._upsert_node(
                conn,
                user.id,
                goal_id,
                "Goal",
                name=name,
                content=content,
                status="confirmed",
                attributes={
                    "status": "active",
                    "priority": priority,
                    "progress": 0,
                    "created_at": datetime.now().isoformat()
                }
            )
            
            # 3. 建立关系 (Vision/User -> HAS_GOAL -> Goal)
            service.graph_store._upsert_edge(conn, user.id, parent_id, goal_id, "HAS_GOAL")
            
            return GoalResponse(
                id=goal_id,
                name=name,
                content=content,
                dossier=GoalDossier(priority=priority)
            )
    except Exception as e:
        logger.error(f"Failed to create goal: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/projects/create", response_model=ProjectResponse)
async def create_project(
    goal_id: str,
    name: str,
    content: Optional[str] = "",
    user: User = Depends(require_user)
):
    """
    为目标创建新项目
    """
    try:
        service = get_memory_service()
        project_id = f"proj_{uuid.uuid4().hex[:8]}"
        
        with service.graph_store._get_conn() as conn:
            # 1. 创建项目节点
            service.graph_store._upsert_node(
                conn,
                user.id,
                project_id,
                "Project",
                name=name,
                content=content,
                status="active",
                attributes={
                    "status": "active",
                    "progress": 0,
                    "created_at": datetime.now().isoformat()
                }
            )
            
            # 2. 建立关系 (Goal -> HAS_PROJECT -> Project)
            service.graph_store._upsert_edge(conn, user.id, goal_id, project_id, "HAS_PROJECT")
            
            return ProjectResponse(
                id=project_id,
                name=name,
                content=content,
                dossier=ProjectDossier()
            )
    except Exception as e:
        logger.error(f"Failed to create project: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/tasks/create", response_model=TaskResponse)
async def create_task(
    project_id: str,
    name: str,
    content: Optional[str] = "",
    priority: str = "medium",
    user: User = Depends(require_user)
):
    """
    为项目创建新任务
    """
    try:
        service = get_memory_service()
        task_id = f"task_{uuid.uuid4().hex[:8]}"
        
        with service.graph_store._get_conn() as conn:
            # 1. 创建任务节点
            service.graph_store._upsert_node(
                conn,
                user.id,
                task_id,
                "Task",
                name=name,
                content=content,
                status="pending",
                attributes={
                    "status": "pending",
                    "priority": priority,
                    "progress": 0,
                    "created_at": datetime.now().isoformat()
                }
            )
            
            # 2. 建立关系 (Project -> CONSISTS_OF -> Task)
            service.graph_store._upsert_edge(conn, user.id, project_id, task_id, "CONSISTS_OF")
            
            return TaskResponse(
                id=task_id,
                name=name,
                content=content,
                dossier=TaskDossier(priority=priority)
            )
    except Exception as e:
        logger.error(f"Failed to create task: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{goal_id}/projects", response_model=List[ProjectResponse])
async def list_goal_projects(goal_id: str, user: User = Depends(require_user)):
    """获取目标的关联项目"""
    try:
        service = get_memory_service()
        projects = []
        with service.graph_store._get_conn() as conn:
            query = """
                SELECT n.* FROM nodes n
                JOIN edges e ON n.id = e.target
                WHERE e.source = ? AND (e.relation = 'HAS_PROJECT' OR e.relation = 'ACHIEVED_BY' OR e.relation = 'DECOMPOSES_TO')
                AND n.type = 'Project'
            """
            rows = conn.execute(query, (goal_id,)).fetchall()
            for row in rows:
                attr = json.loads(row['attributes']) if row['attributes'] else {}
                
                # 获取任务数量
                t_count_row = conn.execute("""
                    SELECT COUNT(*) as count FROM edges 
                    WHERE source = ? AND (relation = 'CONSISTS_OF' OR relation = 'ACHIEVED_BY')
                """, (row['id'],)).fetchone()
                
                projects.append(ProjectResponse(
                    id=row['id'],
                    name=row['name'],
                    content=row['content'] or "",
                    tasks_count=t_count_row['count'] if t_count_row else 0,
                    dossier=ProjectDossier(
                        status=attr.get("status", "active"),
                        sector=attr.get("sector"),
                        progress=attr.get("progress", 0),
                        created_at=row['created_at']
                    )
                ))
        return projects
    except Exception as e:
        logger.error(f"Failed to list projects for goal {goal_id}: {e}")
        return []

@router.get("/projects/{project_id}/tasks", response_model=List[TaskResponse])
async def list_project_tasks(project_id: str, user: User = Depends(require_user)):
    """获取项目的关联任务"""
    try:
        service = get_memory_service()
        tasks = []
        with service.graph_store._get_conn() as conn:
            query = """
                SELECT n.* FROM nodes n
                JOIN edges e ON n.id = e.target
                WHERE e.source = ? AND (e.relation = 'CONSISTS_OF' OR e.relation = 'ACHIEVED_BY')
                AND n.type = 'Task'
            """
            rows = conn.execute(query, (project_id,)).fetchall()
            for row in rows:
                attr = json.loads(row['attributes']) if row['attributes'] else {}
                tasks.append(TaskResponse(
                    id=row['id'],
                    name=row['name'],
                    content=row['content'] or "",
                    dossier=TaskDossier(
                        status=attr.get("status", "pending"),
                        priority=attr.get("priority", "medium"),
                        progress=attr.get("progress", 0),
                        created_at=row['created_at']
                    )
                ))
        return tasks
    except Exception as e:
        logger.error(f"Failed to list tasks for project {project_id}: {e}")
        return []
