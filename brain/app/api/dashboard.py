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
from ..core.db import db_manager
from ..services.memory.memory_service import get_memory_service
from ..models.memory import MemoryType
from ..core.config import DATA_DIR, ENDGAME_VISION
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
import json
import asyncio
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

CONVERSATIONS_FILE = DATA_DIR / "conversations.json"
MESSAGES_FILE = DATA_DIR / "messages.json"

def _load_json_data(file_path, default_value):
    logger.info(f"正在加载 JSON 数据: {file_path}")
    if file_path.exists():
        try:
            content = file_path.read_text(encoding='utf-8')
            data = json.loads(content)
            logger.info(f"成功加载数据，项数: {len(data)}")
            return data
        except Exception as e:
            logger.error(f"加载 JSON 失败 {file_path}: {e}")
            return default_value
    else:
        logger.warning(f"文件不存在: {file_path}")
    return default_value

# 模拟活动日志数据库 (生产环境应从数据库获取)
_activity_logs_db = {}

# ============ 辅助函数 ============

def _calculate_streak(user_id: str, messages: List[dict]) -> int:
    """计算连续活跃天数"""
    active_dates = set()
    
    # 1. 收集消息日期
    for msg in messages:
        if "created_at" in msg:
            try:
                dt_str = msg["created_at"]
                if isinstance(dt_str, str):
                    dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
                    active_dates.add(dt.date())
            except:
                continue
    
    # 2. 收集校准日期 (补充活跃度)
    try:
        calibrations = db_manager.get_h3_calibrations(user_id, 90) # 查最近 90 天
        for c in calibrations:
            if "created_at" in c:
                dt = datetime.fromisoformat(c["created_at"]).date()
                active_dates.add(dt)
    except Exception as e:
        logger.error(f"获取校准记录失败: {e}")

    if not active_dates:
        return 0
    
    # 3. 计算连续天数 (从今天或最近的一个活跃日开始往回倒推)
    streak = 0
    today = date.today()
    
    # 如果今天活跃，从今天开始算
    # 如果今天不活跃，从昨天开始算 (允许 1 天的容错中断，或者说只看连续到昨天的)
    check_date = today
    if today not in active_dates:
        check_date = today - timedelta(days=1)
    
    while check_date in active_dates:
        streak += 1
        check_date -= timedelta(days=1)
    
    # 如果今天刚活跃（之前没活动），streak 应该是 1
    if streak == 0 and today in active_dates:
        streak = 1
        
    return streak


def _get_user_stats(user_id: str) -> DashboardStats:
    """计算用户的各项统计指标"""
    today = date.today()
    
    # 1. 加载数据
    all_convs = _load_json_data(CONVERSATIONS_FILE, {})
    all_messages = _load_json_data(MESSAGES_FILE, {})
    
    logger.info(f"加载原始数据: {len(all_convs)} 个会话, {len(all_messages)} 组消息")
    
    # 过滤用户数据
    user_convs = [c for c in all_convs.values() if c.get("user_id") == user_id]
    
    user_messages = []
    for conv_id in [c["id"] for c in user_convs]:
        if conv_id in all_messages:
            user_messages.extend(all_messages[conv_id])
    
    # 按时间排序，确保 streak 计算和 last_active 正确
    user_messages.sort(key=lambda x: x.get("created_at", ""))
    
    logger.info(f"过滤后数据: {len(user_convs)} 个会话, {len(user_messages)} 条消息")
    
    today = date.today()
    today_messages = [
        m for m in user_messages 
        if "created_at" in m and datetime.fromisoformat(m["created_at"]).date() == today
    ]
    
    # 2. 获取目标数据
    service = get_memory_service()
    goals = service.graph_store.get_nodes_by_type(user_id, MemoryType.GOAL.value)
    completed_goals = [g for g in goals if g.get("dossier", {}).get("status") == "completed"]
    
    # 3. 获取 H3 能量
    h3_history = db_manager.get_h3_energy_history(user_id, 1)
    current_h3 = None
    if h3_history:
        h3 = h3_history[0]
        current_h3 = {
            "mind": h3.get("mind", 0),
            "body": h3.get("body", 0),
            "spirit": h3.get("spirit", 0),
            "vocation": h3.get("vocation", 0)
        }
    
    # 4. 获取校准记录 (作为活跃度的 fallback)
    calibrations = db_manager.get_h3_calibrations(user_id, 30)
    today_calibrations = [
        c for c in calibrations 
        if datetime.fromisoformat(c["created_at"]).date() == today
    ]

    # 5. 计算能量点 (更稳健的算法)
    # 连胜奖励：连胜天数 * 50
    streak_val = _calculate_streak(user_id, user_messages)
    streak_bonus = streak_val * 50
    
    # 活跃奖励：对话数 * 2 (历史权重) + 校准数 * 50
    activity_points = (len(user_messages) * 2) + (len(calibrations) * 50)
    
    # 目标奖励：每个完成的目标 200 分
    goal_bonus = len(completed_goals) * 200
    
    # 存量分：每 10 条消息额外奖励 10 分 (体现数据厚度)
    legacy_points = (len(user_messages) // 10) * 10
    
    energy_points = streak_bonus + activity_points + goal_bonus + legacy_points
    
    # 如果 streak 为 0 但今天有活动，设为 1
    if streak_val == 0 and (len(today_messages) > 0 or len(today_calibrations) > 0):
        streak_val = 1
    
    return DashboardStats(
        user_id=user_id,
        date=today,
        total_conversations=len(user_convs),
        total_messages=len(user_messages),
        total_goals=len(goals),
        completed_goals=len(completed_goals),
        streak_days=streak_val,
        energy_points=int(energy_points),
        last_active=datetime.fromisoformat(user_messages[-1]["created_at"]) if user_messages else None,
        current_h3=current_h3,
        today_messages=len(today_messages),
        today_calibrations=len(today_calibrations),
        today_tasks_completed=0
    )


# ============ AI 总结逻辑 ============

async def _generate_ai_summary(stats: DashboardStats, user_id: str) -> str:
    """基于当前状态生成 AI 实时总结"""
    # 获取 H3 能量平均值和趋势
    h3_history = db_manager.get_h3_energy_history(user_id, 7)
    avg_energy = sum((e['mind'] + e['body'] + e['spirit'] + e['vocation']) / 4 for e in h3_history) / len(h3_history) if h3_history else 50
    
    hour = datetime.now().hour
    if hour < 5: greeting = "深夜了，系统建议进入深度修复模式"
    elif hour < 11: greeting = "晨间协议已激活，今日是实现愿景的关键节点"
    elif hour < 14: greeting = "正午时分，建议回顾上午的认知消耗"
    elif hour < 18: greeting = "午后推进中，保持心智专注度"
    else: greeting = "傍晚好，即将进入日终复盘时间"
    
    status_msg = ""
    if avg_energy > 80:
        status_msg = "当前能量水平极佳，适合处理高复杂度的 Critical Tasks。"
    elif avg_energy < 40:
        status_msg = "检测到能量赤字，建议调低今日认知负荷，优先进行能量校准。"
    else:
        status_msg = f"系统运行平稳。当前有 {stats.total_goals} 个活跃目标，{stats.streak_days} 天连续对齐。"
        
    return f"{greeting}。{status_msg}"


from ..services.neural.processor import get_processor

async def _summarize_vision(vision_desc: str) -> str:
    """使用 AI 总结长篇愿景画布"""
    # 如果描述比较短，或者已经是总结过的，直接返回
    if not vision_desc or len(vision_desc) < 150:
        return vision_desc
    
    # 检查是否包含 Markdown 标题，如果有，说明是原始画布
    if "##" not in vision_desc and len(vision_desc) < 300:
        return vision_desc

    logger.info(f"正在生成愿景总结... (Proxy: {os.environ.get('HTTPS_PROXY', 'None')})")
    
    prompt = f"""
    作为用户的“数字分身”，请将以下长篇幅的“终局愿景画布”总结为一段简洁、有力、且富有启发性的愿景描述（约 150 字以内）。
    
    要求：
    1. 保持第一人称（“我”）或具有感染力的视角。
    2. 提取最核心的商业终局（做什么）、自我终局（生活状态）和影响终局（价值）。
    3. 语言要精炼，具有画面感，不要列举大纲。
    
    原文内容：
    {vision_desc}
    
    总结后的愿景：
    """
    
    # 使用统一的 NeuralProcessor (已配置代理)
    return await get_processor().summarize_text(vision_desc, prompt)


# ============ API 端点 ============

import os

@router.get("/overview", response_model=DashboardOverview)
async def get_dashboard_overview(user: User = Depends(require_user)):
    """
    获取仪表盘总览数据
    """
    # 确保环境变量中存在代理设置 (LangChain Google GenAI 依赖环境变量)
    if not os.environ.get("HTTPS_PROXY") and not os.environ.get("HTTP_PROXY"):
        # 尝试使用默认代理 fallback
        default_proxy = "http://127.0.0.1:1082"
        os.environ["HTTPS_PROXY"] = default_proxy
        os.environ["HTTP_PROXY"] = default_proxy
        logger.info(f"Dashboard: Applied fallback proxy {default_proxy}")

    stats = _get_user_stats(user.id)
    
    # 1. 生成 AI 总结
    ai_summary = await _generate_ai_summary(stats, user.id)
    
    # 调试信息插入到 ai_summary
    last_msg = stats.last_active.strftime('%Y-%m-%d') if stats.last_active else "无记录"
    status_hint = "由于最近一个月没有活跃，对齐天数已归零。发送一条新消息即可重新开始对齐！" if stats.streak_days == 0 else f"您已连续对齐 {stats.streak_days} 天。"
    debug_info = f"[系统提醒] 历史数据已挂载：共 {stats.total_conversations} 个会话，{stats.total_messages} 条消息。最后活跃于 {last_msg}。{status_hint}"
    ai_summary = f"{debug_info}\n\n{ai_summary}"
    
    # 2. 获取愿景数据
    # 这里从配置或内存中获取真实愿景
    if user.vision:
        vision_title = user.vision.title
        # 调用 AI 进行总结性描述，避免直接展示长篇画布
        vision_desc = await _summarize_vision(user.vision.description)
    else:
        vision_title = ENDGAME_VISION.get("title", "成为 Level 5 自由人") if isinstance(ENDGAME_VISION, dict) else "终局愿景"
        vision_desc = (ENDGAME_VISION.get("description", "通过构建 Endgame OS 实现完全的认知自由与生命掌控") 
                      if isinstance(ENDGAME_VISION, dict) else ENDGAME_VISION)
        # 即使是默认愿景，如果太长也总结一下
        vision_desc = await _summarize_vision(vision_desc)
    
    # 计算愿景进度 (基于目标完成度)
    vision_progress = int((stats.completed_goals / stats.total_goals) * 100) if stats.total_goals > 0 else 0
    # 至少给 15% 的基础进度
    vision_progress = max(15, vision_progress)

    # 3. 派生最近活动
    # 加载聊天消息作为活动
    conversations = _load_json_data(CONVERSATIONS_FILE, {})
    user_convs = [c for c in conversations.values() if c.get("user_id") == user.id]
    
    activities = []
    
    # 对话活动
    for conv in sorted(user_convs, key=lambda x: x['updated_at'], reverse=True)[:5]:
        activities.append(ActivityLog(
            id=f"act_{conv['id']}",
            user_id=user.id,
            type=ActivityType.CHAT,
            title="进行深度对话",
            description=conv.get('title', '未命名会话'),
            entity_id=conv['id'],
            entity_type="conversation",
            created_at=datetime.fromisoformat(conv['updated_at'])
        ))
        
    # H3 校准活动
    calibrations = db_manager.get_h3_calibrations(user.id, 5)
    for cal in calibrations:
        scores = cal['energy']
        activities.append(ActivityLog(
            id=f"act_{cal['id']}",
            user_id=user.id,
            type=ActivityType.CALIBRATION,
            title="完成 H3 能量校准",
            description=f"心智: {scores['mind']}, 身体: {scores['body']}, 精神: {scores['spirit']}, 志业: {scores['vocation']}",
            entity_id=cal['id'],
            entity_type="calibration",
            created_at=datetime.fromisoformat(cal['created_at'])
        ))
        
    # 按时间排序并取前 10
    recent_activities = sorted(activities, key=lambda x: x.created_at, reverse=True)[:10]
    
    # 4. 获取活跃目标
    service = get_memory_service()
    goals = service.graph_store.get_nodes_by_type(user.id, MemoryType.GOAL.value)
    active_goals = []
    for g in goals:
        dossier = g.get("dossier", {})
        if dossier.get("status") == "active":
            # 提取目标日期
            target_date = None
            if "target_date" in dossier:
                try:
                    target_date = date.fromisoformat(dossier["target_date"])
                except:
                    pass

            active_goals.append(GoalProgress(
                id=g["id"],
                user_id=user.id,
                title=g["name"],
                description=g.get("content"),
                status=GoalStatus.ACTIVE,
                progress=dossier.get("progress", 0),
                target_date=target_date,
                created_at=datetime.fromisoformat(dossier.get("created_at", datetime.now().isoformat()))
            ))
    
    return {
        "stats": stats,
        "recent_activities": recent_activities,
        "active_goals": active_goals,
        "upcoming_milestones": [],
        "ai_summary": ai_summary,
        "vision": {
            "title": vision_title,
            "description": vision_desc,
            "progress": vision_progress
        }
    }


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
    获取活动日志列表 (从真实数据派生)
    """
    # 复用 overview 中的逻辑，但支持过滤
    overview = await get_dashboard_overview(user)
    logs = overview.recent_activities
    
    # 过滤
    if types:
        type_list = [t.strip() for t in types.split(",")]
        logs = [l for l in logs if l.type in type_list]
    
    if start_date:
        logs = [l for l in logs if l.created_at.date() >= start_date]
    
    if end_date:
        logs = [l for l in logs if l.created_at.date() <= end_date]
    
    # 排序和分页
    sorted_logs = sorted(logs, key=lambda x: x.created_at, reverse=True)
    paginated = sorted_logs[offset:offset + limit]
    
    return paginated









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

