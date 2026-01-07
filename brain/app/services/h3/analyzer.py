"""
H3 能量分析服务
提供深度分析和洞察
"""
from datetime import date, timedelta
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from enum import Enum


class TrendDirection(Enum):
    UP = "up"
    DOWN = "down"
    STABLE = "stable"


class AlertSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class H3Alert:
    """H3 预警"""
    dimension: str
    severity: AlertSeverity
    message: str
    suggestion: str
    triggered_at: date


@dataclass
class H3Insight:
    """H3 洞察"""
    title: str
    description: str
    category: str
    confidence: float  # 0-1


class H3Analyzer:
    """H3 能量分析器"""
    
    def __init__(self):
        self.dimension_labels = {
            "mind": "心智",
            "body": "身体",
            "spirit": "精神",
            "vocation": "志业"
        }
    
    def analyze_week(self, history: List[Dict]) -> Dict[str, Any]:
        """
        分析一周数据
        
        返回周报数据
        """
        if not history:
            return self._empty_week_analysis()
        
        # 计算各维度平均值
        dimensions = ["mind", "body", "spirit", "vocation"]
        averages = {}
        for dim in dimensions:
            values = [h.get(dim, 50) for h in history]
            averages[dim] = sum(values) / len(values) if values else 50
        
        # 计算总体趋势
        totals = [(h.get("mind", 50) + h.get("body", 50) + 
                  h.get("spirit", 50) + h.get("vocation", 50)) / 4 
                  for h in history]
        
        trend = self._calculate_trend_direction(totals)
        
        # 找出最高和最低维度
        best_dim = max(dimensions, key=lambda d: averages[d])
        worst_dim = min(dimensions, key=lambda d: averages[d])
        
        # 生成周报摘要
        summary = self._generate_week_summary(averages, trend, best_dim, worst_dim)
        
        return {
            "period": "week",
            "days_count": len(history),
            "averages": averages,
            "trend": trend.value,
            "best_dimension": best_dim,
            "worst_dimension": worst_dim,
            "summary": summary,
            "insights": self._generate_insights(history, averages)
        }
    
    def generate_alerts(
        self, 
        current: Dict, 
        history: List[Dict]
    ) -> List[H3Alert]:
        """
        生成预警列表
        """
        alerts = []
        today = date.today()
        
        for dim in ["mind", "body", "spirit", "vocation"]:
            value = current.get(dim, 50)
            label = self.dimension_labels[dim]
            
            # 极低预警
            if value < 20:
                alerts.append(H3Alert(
                    dimension=dim,
                    severity=AlertSeverity.CRITICAL,
                    message=f"{label}能量严重不足 ({value}%)",
                    suggestion=f"立即关注{label}恢复，暂停非必要任务",
                    triggered_at=today
                ))
            elif value < 40:
                alerts.append(H3Alert(
                    dimension=dim,
                    severity=AlertSeverity.WARNING,
                    message=f"{label}能量偏低 ({value}%)",
                    suggestion=f"建议优先提升{label}状态",
                    triggered_at=today
                ))
            
            # 连续下降预警
            if len(history) >= 3:
                recent_values = [h.get(dim, 50) for h in history[-3:]]
                if all(recent_values[i] > recent_values[i+1] 
                       for i in range(len(recent_values)-1)):
                    alerts.append(H3Alert(
                        dimension=dim,
                        severity=AlertSeverity.WARNING,
                        message=f"{label}能量连续3天下降",
                        suggestion=f"分析{label}下降原因，及时干预",
                        triggered_at=today
                    ))
        
        # 平衡性预警
        values = [current.get(d, 50) for d in ["mind", "body", "spirit", "vocation"]]
        if max(values) - min(values) > 40:
            alerts.append(H3Alert(
                dimension="balance",
                severity=AlertSeverity.WARNING,
                message="能量严重不平衡",
                suggestion="关注短板维度，追求整体平衡",
                triggered_at=today
            ))
        
        return alerts
    
    def compare_periods(
        self,
        period1: List[Dict],
        period2: List[Dict]
    ) -> Dict[str, Any]:
        """
        比较两个时期的数据
        """
        def calc_avg(data: List[Dict], dim: str) -> float:
            values = [d.get(dim, 50) for d in data]
            return sum(values) / len(values) if values else 50
        
        comparison = {}
        for dim in ["mind", "body", "spirit", "vocation"]:
            avg1 = calc_avg(period1, dim)
            avg2 = calc_avg(period2, dim)
            change = avg2 - avg1
            change_pct = (change / avg1 * 100) if avg1 > 0 else 0
            
            comparison[dim] = {
                "previous": round(avg1, 1),
                "current": round(avg2, 1),
                "change": round(change, 1),
                "change_percent": round(change_pct, 1),
                "direction": "up" if change > 2 else ("down" if change < -2 else "stable")
            }
        
        return {
            "dimensions": comparison,
            "overall_trend": self._determine_overall_trend(comparison)
        }
    
    def _calculate_trend_direction(self, values: List[float]) -> TrendDirection:
        """计算趋势方向"""
        if len(values) < 2:
            return TrendDirection.STABLE
        
        # 简单判断：比较前半部分和后半部分的平均值
        mid = len(values) // 2
        first_half = sum(values[:mid]) / mid if mid > 0 else values[0]
        second_half = sum(values[mid:]) / (len(values) - mid)
        
        diff = second_half - first_half
        if diff > 5:
            return TrendDirection.UP
        elif diff < -5:
            return TrendDirection.DOWN
        return TrendDirection.STABLE
    
    def _generate_week_summary(
        self,
        averages: Dict[str, float],
        trend: TrendDirection,
        best_dim: str,
        worst_dim: str
    ) -> str:
        """生成周报摘要"""
        trend_desc = {
            TrendDirection.UP: "整体呈上升趋势",
            TrendDirection.DOWN: "整体呈下降趋势",
            TrendDirection.STABLE: "整体保持稳定"
        }[trend]
        
        total_avg = sum(averages.values()) / 4
        
        if total_avg >= 70:
            status = "状态良好"
        elif total_avg >= 50:
            status = "状态一般"
        else:
            status = "状态欠佳"
        
        best_label = self.dimension_labels[best_dim]
        worst_label = self.dimension_labels[worst_dim]
        
        return (
            f"本周{status}，{trend_desc}。"
            f"{best_label}表现最佳（{averages[best_dim]:.0f}%），"
            f"{worst_label}需要关注（{averages[worst_dim]:.0f}%）。"
        )
    
    def _generate_insights(
        self,
        history: List[Dict],
        averages: Dict[str, float]
    ) -> List[H3Insight]:
        """生成洞察"""
        insights = []
        
        # 最佳状态日
        if history:
            best_day = max(history, key=lambda h: sum(
                h.get(d, 50) for d in ["mind", "body", "spirit", "vocation"]
            ))
            best_total = sum(best_day.get(d, 50) 
                           for d in ["mind", "body", "spirit", "vocation"]) / 4
            
            insights.append(H3Insight(
                title="本周最佳状态",
                description=f"能量总值达到 {best_total:.0f}%",
                category="highlight",
                confidence=1.0
            ))
        
        # 平衡性洞察
        balance = max(averages.values()) - min(averages.values())
        if balance > 30:
            insights.append(H3Insight(
                title="能量不平衡",
                description="各维度差异较大，建议关注短板",
                category="warning",
                confidence=0.9
            ))
        elif balance < 10:
            insights.append(H3Insight(
                title="能量均衡",
                description="各维度发展均衡，保持这种状态",
                category="positive",
                confidence=0.9
            ))
        
        return insights
    
    def _determine_overall_trend(self, comparison: Dict) -> str:
        """判断整体趋势"""
        directions = [c["direction"] for c in comparison.values()]
        
        up_count = directions.count("up")
        down_count = directions.count("down")
        
        if up_count > down_count:
            return "improving"
        elif down_count > up_count:
            return "declining"
        return "stable"
    
    def _empty_week_analysis(self) -> Dict[str, Any]:
        """空数据时的周分析"""
        return {
            "period": "week",
            "days_count": 0,
            "averages": {"mind": 0, "body": 0, "spirit": 0, "vocation": 0},
            "trend": "stable",
            "best_dimension": None,
            "worst_dimension": None,
            "summary": "本周暂无数据，请开始记录你的能量状态。",
            "insights": []
        }

