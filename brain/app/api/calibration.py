"""
系统校准 API 路由
处理晨间唤醒协议和系统配置校准
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, date, timedelta
import uuid

from ..models.h3 import H3Energy, H3CalibrationRequest
from ..models.user import User
from .auth import require_user
from ..core.db import db_manager

router = APIRouter()


# ============ Request/Response Models ============

class MorningCheckIn(BaseModel):
    """晨间签到数据"""
    sleep_quality: int = Field(..., ge=1, le=5, description="睡眠质量 1-5")
    energy_level: int = Field(..., ge=1, le=5, description="起床精力 1-5")
    mood: str = Field(..., description="心情描述")
    intentions: List[str] = Field(default_factory=list, description="今日意图")


class MorningWakeResponse(BaseModel):
    """晨间唤醒响应"""
    greeting: str
    yesterday_summary: Optional[dict] = None
    h3_status: Optional[dict] = None
    today_focus: List[str]
    ai_message: str
    requires_calibration: bool


class SystemCalibration(BaseModel):
    """系统校准配置"""
    morning_protocol_time: str = Field(default="07:00", description="晨间协议时间")
    evening_review_time: str = Field(default="21:00", description="晚间回顾时间")
    notification_enabled: bool = Field(default=True)
    proactive_reminders: bool = Field(default=True)
    calibration_frequency: str = Field(default="daily", description="校准频率")


# ============ 模拟数据存储 ============

_morning_checkins_db: dict[str, dict] = {}  # user_id -> {date: checkin}
_system_calibrations_db: dict[str, dict] = {}  # user_id -> calibration


# ============ 辅助函数 ============

def _generate_morning_greeting(user: User, checkin: Optional[MorningCheckIn] = None) -> str:
    """生成晨间问候语"""
    hour = datetime.now().hour
    
    if hour < 6:
        time_greeting = "夜深了，还没休息吗"
    elif hour < 9:
        time_greeting = "早安"
    elif hour < 12:
        time_greeting = "上午好"
    elif hour < 14:
        time_greeting = "中午好"
    elif hour < 18:
        time_greeting = "下午好"
    else:
        time_greeting = "晚上好"
    
    return f"{time_greeting}，{user.name}！新的一天，新的可能。"


def _generate_ai_morning_message(
    user: User,
    checkin: Optional[MorningCheckIn],
    h3_status: Optional[dict]
) -> str:
    """生成 AI 晨间消息"""
    messages = []
    
    if checkin:
        if checkin.sleep_quality < 3:
            messages.append("看起来昨晚休息得不太好，今天要注意调节节奏。")
        if checkin.energy_level >= 4:
            messages.append("精力充沛的一天！正是推进重要事项的好时机。")
    
    if h3_status:
        total = h3_status.get("total", 50)
        if total < 40:
            messages.append("能量状态偏低，建议今天以恢复为主，不要给自己太大压力。")
        elif total >= 70:
            messages.append("能量状态很好！可以挑战一些有难度的任务。")
    
    if not messages:
        messages.append("让我们一起保持对终局愿景的聚焦，今天要做什么来接近它？")
    
    return " ".join(messages)


# ============ API 端点 ============

@router.get("/morning/wake", response_model=MorningWakeResponse)
async def morning_wake(user: User = Depends(require_user)):
    """
    晨间唤醒协议
    
    返回今日晨间唤醒数据，包括昨日回顾和今日建议
    """
    today = date.today()
    yesterday = today - timedelta(days=1)
    
    # 检查今日是否已签到
    user_checkins = _morning_checkins_db.get(user.id, {})
    today_checkin = user_checkins.get(str(today))
    
    # 昨日摘要 (TODO: 从实际数据获取)
    yesterday_summary = {
        "conversations": 3,
        "tasks_completed": 2,
        "h3_average": {
            "mind": 65,
            "body": 55,
            "spirit": 70,
            "vocation": 60
        }
    }
    
    # 获取最新 H3 状态
    h3_history = db_manager.get_h3_energy_history(user.id, 1)
    if h3_history:
        h3 = h3_history[0]
        h3_status = {
            "mind": h3.get("mind", 50),
            "body": h3.get("body", 50),
            "spirit": h3.get("spirit", 50),
            "vocation": h3.get("vocation", 50),
            "total": sum([h3.get(k, 50) for k in ["mind", "body", "spirit", "vocation"]]) // 4,
            "trend": "stable"
        }
    else:
        h3_status = {
            "mind": 50,
            "body": 50,
            "spirit": 50,
            "vocation": 50,
            "total": 50,
            "trend": "stable"
        }
    
    # 今日聚焦建议
    today_focus = [
        "继续推进 Endgame OS 开发",
        "完成代码审查",
        "30分钟运动恢复身体能量"
    ]
    
    return MorningWakeResponse(
        greeting=_generate_morning_greeting(user, today_checkin),
        yesterday_summary=yesterday_summary,
        h3_status=h3_status,
        today_focus=today_focus,
        ai_message=_generate_ai_morning_message(user, today_checkin, h3_status),
        requires_calibration=today_checkin is None
    )


@router.post("/morning/checkin")
async def morning_checkin(
    checkin: MorningCheckIn,
    user: User = Depends(require_user)
):
    """
    提交晨间签到
    """
    today = str(date.today())
    
    if user.id not in _morning_checkins_db:
        _morning_checkins_db[user.id] = {}
    
    _morning_checkins_db[user.id][today] = {
        **checkin.model_dump(),
        "created_at": datetime.now().isoformat()
    }
    
    return {
        "message": "晨间签到完成",
        "date": today,
        "checkin": checkin
    }


@router.get("/system")
async def get_system_calibration(user: User = Depends(require_user)):
    """
    获取系统校准配置
    """
    calibration = _system_calibrations_db.get(user.id)
    
    if not calibration:
        calibration = SystemCalibration().model_dump()
        _system_calibrations_db[user.id] = calibration
    
    return calibration


@router.put("/system")
async def update_system_calibration(
    calibration: SystemCalibration,
    user: User = Depends(require_user)
):
    """
    更新系统校准配置
    """
    _system_calibrations_db[user.id] = calibration.model_dump()
    return calibration


@router.get("/status")
async def get_calibration_status(user: User = Depends(require_user)):
    """
    获取校准状态概览
    """
    today = date.today()
    
    # 检查今日签到
    user_checkins = _morning_checkins_db.get(user.id, {})
    morning_done = str(today) in user_checkins
    
    # 获取系统配置
    system_config = _system_calibrations_db.get(user.id, SystemCalibration().model_dump())
    
    return {
        "date": str(today),
        "morning_checkin_done": morning_done,
        "h3_calibration_done": False,  # TODO: 从 H3 服务获取
        "evening_review_done": False,  # TODO: 实现晚间回顾
        "system_config": system_config,
        "next_action": "morning_checkin" if not morning_done else "h3_calibration"
    }


@router.post("/onboarding/complete")
async def complete_onboarding(user: User = Depends(require_user)):
    """
    完成引导流程
    """
    # TODO: 更新用户 onboarding_completed 状态
    return {"message": "引导完成", "user_id": user.id}


@router.get("/onboarding/status")
async def get_onboarding_status(user: User = Depends(require_user)):
    """
    获取引导进度
    """
    return {
        "completed": user.onboarding_completed,
        "steps": {
            "profile_setup": True,
            "vision_defined": user.vision is not None,
            "persona_configured": True,
            "first_calibration": False,  # TODO: 检查是否完成首次校准
            "first_conversation": False  # TODO: 检查是否完成首次对话
        }
    }

