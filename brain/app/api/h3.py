"""
H3 能量系统 API 路由
处理能量数据的 CRUD 和趋势分析
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from datetime import date, datetime, timedelta
import uuid

from ..models.h3 import (
    H3Energy, H3Calibration, H3Trend, H3Alert,
    H3CalibrationRequest, EnergyDimension, AlertLevel
)
from ..models.user import User
from .auth import require_user
from pydantic import BaseModel
from ..core.db import db_manager

router = APIRouter()

# ============ 前端对接模型 ============

class H3Scores(BaseModel):
    mind: int
    body: int
    spirit: int
    vocation: int

class H3InitializeRequest(BaseModel):
    scores: H3Scores
    source: str = "calibration"
    note: str = ""

class H3UpdateRequest(BaseModel):
    scores: H3Scores
    note: str = ""
    source: str = "manual"

class H3EntryResponse(BaseModel):
    scores: H3Scores
    created_at: str
    source: str
    note: str


# ============ 数据访问层 (重构为持久化存储) ============

def _get_user_energy_history(user_id: str, days: int = 7) -> List[H3Energy]:
    """获取用户能量历史 (从数据库读取)"""
    history_data = db_manager.get_h3_energy_history(user_id, days)
    return [H3Energy(**e) for e in history_data]


def _calculate_trend(values: List[int]) -> float:
    """计算趋势 (-1 到 1)"""
    if len(values) < 2:
        return 0
    
    # 简单线性回归斜率
    n = len(values)
    sum_x = sum(range(n))
    sum_y = sum(values)
    sum_xy = sum(i * v for i, v in enumerate(values))
    sum_x2 = sum(i * i for i in range(n))
    
    denominator = n * sum_x2 - sum_x * sum_x
    if denominator == 0:
        return 0
    
    slope = (n * sum_xy - sum_x * sum_y) / denominator
    
    # 归一化到 -1 到 1
    return max(-1, min(1, slope / 10))


def _generate_alerts(energy: H3Energy, history: List[H3Energy]) -> List[H3Alert]:
    """生成能量预警"""
    alerts = []
    
    # 检查各维度
    dimensions = [
        (EnergyDimension.MIND, energy.mind, "心智"),
        (EnergyDimension.BODY, energy.body, "身体"),
        (EnergyDimension.SPIRIT, energy.spirit, "精神"),
        (EnergyDimension.VOCATION, energy.vocation, "志业"),
    ]
    
    for dim, value, name in dimensions:
        # 低能量预警
        if value < 30:
            alerts.append(H3Alert(
                dimension=dim,
                level=AlertLevel.CRITICAL,
                message=f"{name}能量过低 ({value}%)",
                suggestion=f"建议优先关注{name}恢复"
            ))
        elif value < 50:
            alerts.append(H3Alert(
                dimension=dim,
                level=AlertLevel.WARNING,
                message=f"{name}能量偏低 ({value}%)",
                suggestion=f"注意{name}状态"
            ))
        
        # 连续下降预警
        if len(history) >= 3:
            recent_values = [getattr(h, dim.value) for h in history[-3:]]
            if all(recent_values[i] > recent_values[i+1] for i in range(len(recent_values)-1)):
                alerts.append(H3Alert(
                    dimension=dim,
                    level=AlertLevel.WARNING,
                    message=f"{name}能量连续下降",
                    suggestion=f"关注{name}领域，找出下降原因"
                ))
    
    return alerts


# ============ API 端点 ============

@router.get("/current", response_model=H3Energy)
async def get_current_energy(user: User = Depends(require_user)):
    """
    获取当前（今日）能量状态。如果没有今日记录，则返回最新的一条记录。
    """
    history = db_manager.get_h3_energy_history(user.id, 1)
    
    if history:
        # 如果有记录，直接返回最新的（无论是今天的还是之前的）
        # 这样可以保证 UI 的连续性，而不是突然跳回 50
        return H3Energy(**history[0])
    
    # 没有任何历史记录，返回默认值
    return H3Energy(
        user_id=user.id,
        date=date.today(),
        mind=50,
        body=50,
        spirit=50,
        vocation=50
    )


@router.get("/history", response_model=List[H3Energy])
async def get_energy_history(
    days: int = Query(default=7, ge=1, le=90),
    user: User = Depends(require_user)
):
    """
    获取能量历史数据
    """
    return _get_user_energy_history(user.id, days)


@router.get("/trend", response_model=H3Trend)
async def get_energy_trend(
    period: str = Query(default="7d", pattern="^(7d|30d|90d)$"),
    user: User = Depends(require_user)
):
    """
    获取能量趋势分析
    """
    days = {"7d": 7, "30d": 30, "90d": 90}[period]
    history = _get_user_energy_history(user.id, days)
    
    if not history:
        return H3Trend(user_id=user.id, period=period)
    
    # 计算各维度趋势
    mind_values = [e.mind for e in history]
    body_values = [e.body for e in history]
    spirit_values = [e.spirit for e in history]
    vocation_values = [e.vocation for e in history]
    
    # 生成预警
    current = history[-1] if history else None
    alerts = _generate_alerts(current, history) if current else []
    
    return H3Trend(
        user_id=user.id,
        period=period,
        data_points=history,
        mind_trend=_calculate_trend(mind_values),
        body_trend=_calculate_trend(body_values),
        spirit_trend=_calculate_trend(spirit_values),
        vocation_trend=_calculate_trend(vocation_values),
        alerts=[a.model_dump() for a in alerts]
    )


@router.post("/calibrate", response_model=H3Calibration)
async def calibrate_energy(
    request: H3CalibrationRequest,
    user: User = Depends(require_user)
):
    """
    提交 H3 能量校准
    
    记录用户自评的能量状态
    """
    today = date.today()
    
    now = datetime.now()
    # 创建能量快照
    energy = H3Energy(
        user_id=user.id,
        date=today,
        mind=request.mind,
        body=request.body,
        spirit=request.spirit,
        vocation=request.vocation,
        created_at=now
    )
    
    # 保存能量数据
    db_manager.save_h3_energy(user.id, energy.model_dump())
    
    # 创建校准记录
    calibration = H3Calibration(
        id=f"cal_{uuid.uuid4().hex[:8]}",
        user_id=user.id,
        energy=energy,
        mood_note=request.mood_note,
        blockers=request.blockers,
        wins=request.wins,
        calibration_type="manual",
        created_at=now
    )
    
    # 保存校准记录
    db_manager.save_h3_calibration(calibration.model_dump())
    
    return calibration


@router.get("/calibrations", response_model=List[H3Calibration])
async def get_calibrations(
    limit: int = Query(default=10, ge=1, le=100),
    user: User = Depends(require_user)
):
    """
    获取校准历史记录
    """
    calibrations = db_manager.get_h3_calibrations(user.id, limit)
    return [H3Calibration(**c) for c in calibrations]


@router.post("/initialize")
async def initialize_h3(
    request: H3InitializeRequest,
    user: User = Depends(require_user)
):
    """
    初始化 H3 状态
    """
    today = date.today()
    created_at = datetime.now()
    
    # 创建能量快照
    energy = H3Energy(
        user_id=user.id,
        date=today,
        mind=request.scores.mind,
        body=request.scores.body,
        spirit=request.scores.spirit,
        vocation=request.scores.vocation,
        created_at=created_at
    )
    
    # 保存数据
    db_manager.save_h3_energy(user.id, energy.model_dump())
    
    return {
        "entry": {
            "scores": request.scores.model_dump(),
            "created_at": created_at.isoformat(),
            "source": request.source,
            "note": request.note
        }
    }


@router.post("/update")
async def update_h3(
    request: H3UpdateRequest,
    user: User = Depends(require_user)
):
    """
    更新 H3 状态
    """
    today = date.today()
    created_at = datetime.now()
    
    # 创建能量快照
    energy = H3Energy(
        user_id=user.id,
        date=today,
        mind=request.scores.mind,
        body=request.scores.body,
        spirit=request.scores.spirit,
        vocation=request.scores.vocation,
        created_at=created_at
    )
    
    # 更新数据
    db_manager.save_h3_energy(user.id, energy.model_dump())
        
    return {
        "entry": {
            "scores": request.scores.model_dump(),
            "created_at": created_at.isoformat(),
            "source": request.source,
            "note": request.note
        }
    }


@router.get("/alerts", response_model=List[H3Alert])
async def get_alerts(user: User = Depends(require_user)):
    """
    获取当前能量预警
    """
    history = _get_user_energy_history(user.id, 7)
    
    if not history:
        return []
    
    current = history[-1]
    return _generate_alerts(current, history)


@router.get("/summary")
async def get_energy_summary(user: User = Depends(require_user)):
    """
    获取能量状态摘要（用于仪表盘）
    """
    history = _get_user_energy_history(user.id, 7)
    
    if not history:
        return {
            "current": None,
            "average": None,
            "trend": "stable",
            "alerts_count": 0
        }
    
    current = history[-1]
    
    # 计算平均值
    avg_mind = sum(e.mind for e in history) / len(history)
    avg_body = sum(e.body for e in history) / len(history)
    avg_spirit = sum(e.spirit for e in history) / len(history)
    avg_vocation = sum(e.vocation for e in history) / len(history)
    
    # 判断整体趋势
    total_trend = _calculate_trend([e.total for e in history])
    trend = "up" if total_trend > 0.1 else ("down" if total_trend < -0.1 else "stable")
    
    # 预警数量
    alerts = _generate_alerts(current, history)
    
    return {
        "current": {
            "mind": current.mind,
            "body": current.body,
            "spirit": current.spirit,
            "vocation": current.vocation,
            "total": current.total,
            "balance_score": current.balance_score
        },
        "average": {
            "mind": round(avg_mind),
            "body": round(avg_body),
            "spirit": round(avg_spirit),
            "vocation": round(avg_vocation)
        },
        "trend": trend,
        "alerts_count": len(alerts)
    }

