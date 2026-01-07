"""
仪表盘 API 路由
提供统计数据、活动日志、目标进度
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from datetime import datetime, date, timedelta
import uuid

from ..models.dashboard import (
    DashboardStats, ActivityLog, GoalProgress, DashboardOverview,
    TimelineFilter, ActivityType, GoalStatus
)
from ..models.user import User
from .auth import require_user

router = APIRouter()


# ============ 模拟数据存储 ============

_activity_logs_db: dict[str, List[dict]] = {}  # user_id -> [ActivityLog]
_goals_db: dict[str, List[dict]] = {}  # user_id -> [GoalProgress]


# ============ 辅助函数 ============

def _calculate_streak(user_id: str) -> int:
    """计算连续活跃天数"""
    logs = _activity_logs_db.get(user_id, [])
    if not logs:
        return 0
    
    # 按日期分组
    active_dates = set()
    for log in logs:
        log_date = datetime.fromisoformat(log["created_at"]).date()
        active_dates.add(log_date)
    
    # 计算连续天数
    streak = 0
    check_date = date.today()
    
    while check_date in active_dates:
        streak += 1
        check_date -= timedelta(days=1)
    
    return streak


def _get_user_stats(user_id: str) -> DashboardStats:
    """获取用户统计数据"""
    logs = _activity_logs_db.get(user_id, [])
    goals = _goals_db.get(user_id, [])
    
    today = date.today()
    today_logs = [
        l for l in logs
        if datetime.fromisoformat(l["created_at"]).date() == today
    ]
    
    # 计算各类统计
    chat_logs = [l for l in logs if l["type"] == "chat"]
    calibration_logs = [l for l in today_logs if l["type"] == "calibration"]
    task_logs = [l for l in today_logs if l["type"] == "task_complete"]
    
    completed_goals = [g for g in goals if g["status"] == "completed"]
    
    return DashboardStats(
        user_id=user_id,
        date=today,
        total_conversations=len(set(l.get("entity_id") for l in chat_logs if l.get("entity_id"))),
        total_messages=len(chat_logs),
        total_goals=len(goals),
        completed_goals=len(completed_goals),
        streak_days=_calculate_streak(user_id),
        last_active=datetime.fromisoformat(logs[-1]["created_at"]) if logs else None,
        today_messages=len([l for l in today_logs if l["type"] == "chat"]),
        today_calibrations=len(calibration_logs),
        today_tasks_completed=len(task_logs)
    )


# ============ API 端点 ============

@router.get("/overview", response_model=DashboardOverview)
async def get_dashboard_overview(user: User = Depends(require_user)):
    """
    获取仪表盘总览数据
    
    包含统计数据、最近活动、活跃目标、即将到来的里程碑
    """
    stats = _get_user_stats(user.id)
    
    # 获取最近活动
    logs = _activity_logs_db.get(user.id, [])
    recent_logs = sorted(logs, key=lambda x: x["created_at"], reverse=True)[:10]
    recent_activities = [ActivityLog(**l) for l in recent_logs]
    
    # 获取活跃目标
    goals = _goals_db.get(user.id, [])
    active_goals = [
        GoalProgress(**g) for g in goals
        if g["status"] == "active"
    ]
    
    # 即将到来的里程碑 (模拟数据)
    upcoming_milestones = [
        {
            "id": "ms_001",
            "title": "完成 MVP 发布",
            "goal_id": "goal_001",
            "due_date": str(date.today() + timedelta(days=7)),
            "progress": 80
        }
    ]
    
    return DashboardOverview(
        stats=stats,
        recent_activities=recent_activities,
        active_goals=active_goals,
        upcoming_milestones=upcoming_milestones
    )


@router.get("/stats", response_model=DashboardStats)
async def get_stats(user: User = Depends(require_user)):
    """
    获取用户统计数据
    """
    return _get_user_stats(user.id)


@router.get("/activities", response_model=List[ActivityLog])
async def get_activities(
    types: Optional[str] = Query(default=None, description="活动类型，逗号分隔"),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(require_user)
):
    """
    获取活动日志列表
    """
    logs = _activity_logs_db.get(user.id, [])
    
    # 过滤
    if types:
        type_list = [t.strip() for t in types.split(",")]
        logs = [l for l in logs if l["type"] in type_list]
    
    if start_date:
        logs = [
            l for l in logs
            if datetime.fromisoformat(l["created_at"]).date() >= start_date
        ]
    
    if end_date:
        logs = [
            l for l in logs
            if datetime.fromisoformat(l["created_at"]).date() <= end_date
        ]
    
    # 排序和分页
    sorted_logs = sorted(logs, key=lambda x: x["created_at"], reverse=True)
    paginated = sorted_logs[offset:offset + limit]
    
    return [ActivityLog(**l) for l in paginated]


@router.post("/activities", response_model=ActivityLog)
async def create_activity(
    activity_type: ActivityType,
    title: str,
    description: Optional[str] = None,
    entity_id: Optional[str] = None,
    entity_type: Optional[str] = None,
    user: User = Depends(require_user)
):
    """
    创建活动日志
    """
    log = ActivityLog(
        id=f"log_{uuid.uuid4().hex[:8]}",
        user_id=user.id,
        type=activity_type,
        title=title,
        description=description,
        entity_id=entity_id,
        entity_type=entity_type,
        created_at=datetime.now()
    )
    
    if user.id not in _activity_logs_db:
        _activity_logs_db[user.id] = []
    
    _activity_logs_db[user.id].append(log.model_dump())
    
    return log


@router.get("/goals", response_model=List[GoalProgress])
async def get_goals(
    status: Optional[GoalStatus] = None,
    user: User = Depends(require_user)
):
    """
    获取目标列表
    """
    goals = _goals_db.get(user.id, [])
    
    if status:
        goals = [g for g in goals if g["status"] == status.value]
    
    return [GoalProgress(**g) for g in goals]


@router.get("/goals/{goal_id}", response_model=GoalProgress)
async def get_goal(
    goal_id: str,
    user: User = Depends(require_user)
):
    """
    获取目标详情
    """
    goals = _goals_db.get(user.id, [])
    
    for goal in goals:
        if goal["id"] == goal_id:
            return GoalProgress(**goal)
    
    raise HTTPException(status_code=404, detail="目标不存在")


@router.post("/goals", response_model=GoalProgress)
async def create_goal(
    title: str,
    description: Optional[str] = None,
    target_date: Optional[date] = None,
    parent_goal_id: Optional[str] = None,
    tags: List[str] = [],
    user: User = Depends(require_user)
):
    """
    创建新目标
    """
    goal = GoalProgress(
        id=f"goal_{uuid.uuid4().hex[:8]}",
        user_id=user.id,
        title=title,
        description=description,
        status=GoalStatus.ACTIVE,
        progress=0,
        start_date=date.today(),
        target_date=target_date,
        parent_goal_id=parent_goal_id,
        tags=tags,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    
    if user.id not in _goals_db:
        _goals_db[user.id] = []
    
    _goals_db[user.id].append(goal.model_dump())
    
    # 记录活动
    await create_activity(
        activity_type=ActivityType.GOAL_UPDATE,
        title=f"创建目标: {title}",
        entity_id=goal.id,
        entity_type="goal",
        user=user
    )
    
    return goal


@router.patch("/goals/{goal_id}", response_model=GoalProgress)
async def update_goal(
    goal_id: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
    status: Optional[GoalStatus] = None,
    progress: Optional[float] = None,
    user: User = Depends(require_user)
):
    """
    更新目标
    """
    goals = _goals_db.get(user.id, [])
    
    for i, goal in enumerate(goals):
        if goal["id"] == goal_id:
            if title is not None:
                goal["title"] = title
            if description is not None:
                goal["description"] = description
            if status is not None:
                goal["status"] = status.value
                if status == GoalStatus.COMPLETED:
                    goal["completed_at"] = datetime.now().isoformat()
            if progress is not None:
                goal["progress"] = progress
            
            goal["updated_at"] = datetime.now().isoformat()
            _goals_db[user.id][i] = goal
            
            return GoalProgress(**goal)
    
    raise HTTPException(status_code=404, detail="目标不存在")


@router.get("/timeline")
async def get_timeline(
    days: int = Query(default=7, ge=1, le=30),
    user: User = Depends(require_user)
):
    """
    获取时间线数据（按日期分组的活动）
    """
    logs = _activity_logs_db.get(user.id, [])
    cutoff = date.today() - timedelta(days=days)
    
    # 过滤和分组
    timeline = {}
    for log in logs:
        log_date = datetime.fromisoformat(log["created_at"]).date()
        if log_date >= cutoff:
            date_str = str(log_date)
            if date_str not in timeline:
                timeline[date_str] = []
            timeline[date_str].append(log)
    
    # 排序
    return {
        "days": days,
        "timeline": dict(sorted(timeline.items(), reverse=True))
    }

