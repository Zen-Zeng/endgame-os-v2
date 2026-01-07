"""
晨间唤醒协议服务
处理每日晨间流程：回顾、校准、激励
"""
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass


@dataclass
class DayReview:
    """昨日回顾"""
    date: date
    conversations_count: int
    tasks_completed: int
    h3_average: Dict[str, int]
    highlights: List[str]
    areas_for_improvement: List[str]


@dataclass
class MorningBriefing:
    """晨间简报"""
    greeting: str
    yesterday_review: Optional[DayReview]
    today_focus: List[str]
    h3_status: Dict[str, Any]
    ai_message: str
    requires_calibration: bool
    suggested_priorities: List[str]


class MorningProtocol:
    """晨间唤醒协议"""
    
    # 问候语模板
    GREETINGS = {
        "early": "夜深了，还没休息吗？明天又是新的一天。",
        "dawn": "清晨好！黎明的光芒预示着新的可能。",
        "morning": "早安！新的一天，新的机会。",
        "late_morning": "上午好！今天的计划准备好了吗？",
        "noon": "中午好！上午的进展如何？",
        "afternoon": "下午好！继续保持专注。",
        "evening": "晚上好！今天过得怎么样？"
    }
    
    # 激励语句库
    MOTIVATIONS = [
        "记住，每一天都是向终局愿景迈进的机会。",
        "小步前进也是前进，关键是保持方向。",
        "今天的努力，是明天成就的基石。",
        "保持专注，你比想象中更接近目标。",
        "能量是可再生的，保持节奏，持续前进。"
    ]
    
    def __init__(self, user_name: str, user_vision: Optional[str] = None):
        self.user_name = user_name
        self.user_vision = user_vision
    
    def generate_briefing(
        self,
        yesterday_data: Optional[Dict] = None,
        current_h3: Optional[Dict] = None,
        pending_tasks: Optional[List[str]] = None
    ) -> MorningBriefing:
        """生成晨间简报"""
        
        # 生成问候
        greeting = self._generate_greeting()
        
        # 昨日回顾
        yesterday_review = None
        if yesterday_data:
            yesterday_review = self._create_day_review(yesterday_data)
        
        # H3 状态分析
        h3_status = self._analyze_h3_status(current_h3)
        
        # 今日聚焦
        today_focus = self._generate_focus_items(
            yesterday_review,
            h3_status,
            pending_tasks
        )
        
        # AI 消息
        ai_message = self._generate_ai_message(yesterday_review, h3_status)
        
        # 建议优先级
        suggested_priorities = self._suggest_priorities(
            h3_status,
            pending_tasks
        )
        
        return MorningBriefing(
            greeting=greeting,
            yesterday_review=yesterday_review,
            today_focus=today_focus,
            h3_status=h3_status,
            ai_message=ai_message,
            requires_calibration=current_h3 is None,
            suggested_priorities=suggested_priorities
        )
    
    def generate_wake_message(
        self,
        h3_status: Optional[Dict] = None,
        streak_days: int = 0
    ) -> str:
        """生成唤醒消息"""
        parts = []
        
        # 基础问候
        parts.append(self._generate_greeting())
        
        # 连续天数提醒
        if streak_days > 0:
            if streak_days >= 7:
                parts.append(f"🔥 你已经连续活跃 {streak_days} 天了！保持这种节奏！")
            elif streak_days >= 3:
                parts.append(f"✨ 连续第 {streak_days} 天了，习惯正在形成。")
        
        # H3 状态提示
        if h3_status:
            total = sum(h3_status.values()) / 4
            if total >= 70:
                parts.append("能量状态很好，今天可以挑战一些有难度的任务。")
            elif total >= 50:
                parts.append("能量状态适中，建议合理安排任务优先级。")
            else:
                parts.append("能量偏低，今天以恢复为主，不要给自己太大压力。")
        
        # 随机激励
        import random
        parts.append(random.choice(self.MOTIVATIONS))
        
        return "\n\n".join(parts)
    
    def check_should_trigger(self, last_checkin: Optional[datetime] = None) -> bool:
        """检查是否应该触发晨间协议"""
        now = datetime.now()
        
        # 检查时间窗口（6:00 - 10:00）
        if not (6 <= now.hour < 10):
            return False
        
        # 检查今日是否已触发
        if last_checkin:
            if last_checkin.date() == date.today():
                return False
        
        return True
    
    def _generate_greeting(self) -> str:
        """生成时段问候"""
        hour = datetime.now().hour
        
        if hour < 5:
            key = "early"
        elif hour < 6:
            key = "dawn"
        elif hour < 10:
            key = "morning"
        elif hour < 12:
            key = "late_morning"
        elif hour < 14:
            key = "noon"
        elif hour < 18:
            key = "afternoon"
        else:
            key = "evening"
        
        base_greeting = self.GREETINGS[key]
        return f"{base_greeting.replace('！', f'，{self.user_name}！')}"
    
    def _create_day_review(self, data: Dict) -> DayReview:
        """创建昨日回顾"""
        return DayReview(
            date=date.today() - timedelta(days=1),
            conversations_count=data.get("conversations", 0),
            tasks_completed=data.get("tasks_completed", 0),
            h3_average=data.get("h3_average", {}),
            highlights=data.get("highlights", []),
            areas_for_improvement=data.get("improvements", [])
        )
    
    def _analyze_h3_status(self, h3: Optional[Dict]) -> Dict[str, Any]:
        """分析 H3 状态"""
        if not h3:
            return {
                "available": False,
                "message": "请先完成今日能量校准"
            }
        
        total = sum(h3.values()) / 4
        
        # 找出最高和最低维度
        dimensions = ["mind", "body", "spirit", "vocation"]
        dim_labels = {"mind": "心智", "body": "身体", "spirit": "精神", "vocation": "志业"}
        
        best = max(dimensions, key=lambda d: h3.get(d, 0))
        worst = min(dimensions, key=lambda d: h3.get(d, 0))
        
        return {
            "available": True,
            "values": h3,
            "total": total,
            "best_dimension": {"key": best, "label": dim_labels[best], "value": h3.get(best, 0)},
            "worst_dimension": {"key": worst, "label": dim_labels[worst], "value": h3.get(worst, 0)},
            "balance_score": self._calculate_balance(h3),
            "status": "good" if total >= 70 else ("moderate" if total >= 50 else "low")
        }
    
    def _calculate_balance(self, h3: Dict) -> float:
        """计算平衡分数"""
        values = list(h3.values())
        if not values:
            return 0
        
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        std_dev = variance ** 0.5
        
        return max(0, 100 - std_dev * 2)
    
    def _generate_focus_items(
        self,
        review: Optional[DayReview],
        h3_status: Dict,
        pending_tasks: Optional[List[str]]
    ) -> List[str]:
        """生成今日聚焦事项"""
        focus = []
        
        # 基于 H3 状态的建议
        if h3_status.get("available"):
            worst = h3_status.get("worst_dimension", {})
            if worst.get("value", 50) < 50:
                focus.append(f"关注 {worst.get('label', '')} 能量恢复")
        
        # 基于待办任务
        if pending_tasks:
            focus.extend(pending_tasks[:3])  # 最多3个
        
        # 默认建议
        if not focus:
            focus = [
                "完成今日 H3 校准",
                "回顾本周目标进度",
                "处理最重要的一项任务"
            ]
        
        return focus[:5]  # 最多5个聚焦项
    
    def _generate_ai_message(
        self,
        review: Optional[DayReview],
        h3_status: Dict
    ) -> str:
        """生成 AI 个性化消息"""
        messages = []
        
        # 基于昨日回顾
        if review:
            if review.tasks_completed > 0:
                messages.append(f"昨天完成了 {review.tasks_completed} 项任务，不错的进展！")
            if review.highlights:
                messages.append(f"昨日亮点：{review.highlights[0]}")
        
        # 基于 H3 状态
        if h3_status.get("available"):
            status = h3_status.get("status")
            if status == "good":
                messages.append("能量充沛的一天，正是推进重要事项的好时机。")
            elif status == "low":
                messages.append("今天能量偏低，建议以恢复为主，专注最重要的一件事。")
        
        # 愿景提醒
        if self.user_vision:
            messages.append(f"记住你的终局愿景：{self.user_vision[:50]}...")
        
        if not messages:
            messages.append("让我们一起度过有意义的一天。你打算从哪里开始？")
        
        return " ".join(messages)
    
    def _suggest_priorities(
        self,
        h3_status: Dict,
        pending_tasks: Optional[List[str]]
    ) -> List[str]:
        """建议优先级"""
        priorities = []
        
        # H3 相关优先级
        if not h3_status.get("available"):
            priorities.append("1. 完成今日 H3 能量校准")
        elif h3_status.get("status") == "low":
            worst = h3_status.get("worst_dimension", {})
            priorities.append(f"1. 优先恢复 {worst.get('label', '')} 能量")
        
        # 任务优先级
        if pending_tasks:
            for i, task in enumerate(pending_tasks[:2], start=len(priorities) + 1):
                priorities.append(f"{i}. {task}")
        
        return priorities

