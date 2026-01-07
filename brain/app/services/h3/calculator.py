"""
H3 能量计算服务
处理能量值计算、趋势分析、预警生成
"""
from datetime import datetime, date, timedelta
from typing import List, Optional, Tuple
from dataclasses import dataclass
import math


@dataclass
class EnergyPoint:
    """能量数据点"""
    date: date
    mind: int
    body: int
    spirit: int
    vocation: int
    
    @property
    def total(self) -> int:
        return (self.mind + self.body + self.spirit + self.vocation) // 4
    
    @property
    def values(self) -> List[int]:
        return [self.mind, self.body, self.spirit, self.vocation]


class H3Calculator:
    """H3 能量计算器"""
    
    # 维度权重（可配置）
    DEFAULT_WEIGHTS = {
        "mind": 1.0,
        "body": 1.0,
        "spirit": 1.0,
        "vocation": 1.0
    }
    
    # 预警阈值
    LOW_THRESHOLD = 30
    WARNING_THRESHOLD = 50
    HIGH_THRESHOLD = 80
    
    def __init__(self, weights: Optional[dict] = None):
        self.weights = weights or self.DEFAULT_WEIGHTS
    
    def calculate_total(self, point: EnergyPoint) -> float:
        """计算加权总能量"""
        weighted_sum = (
            point.mind * self.weights["mind"] +
            point.body * self.weights["body"] +
            point.spirit * self.weights["spirit"] +
            point.vocation * self.weights["vocation"]
        )
        total_weight = sum(self.weights.values())
        return weighted_sum / total_weight
    
    def calculate_balance_score(self, point: EnergyPoint) -> float:
        """
        计算平衡度分数
        
        标准差越小，平衡度越高
        返回 0-100 的分数
        """
        values = point.values
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        std_dev = math.sqrt(variance)
        
        # 转换为 0-100 分数
        # 标准差 0 -> 100分, 标准差 50 -> 0分
        score = max(0, 100 - std_dev * 2)
        return round(score, 1)
    
    def calculate_momentum(self, history: List[EnergyPoint]) -> dict:
        """
        计算能量动量（变化趋势）
        
        返回各维度的动量值 (-1 到 1)
        """
        if len(history) < 2:
            return {"mind": 0, "body": 0, "spirit": 0, "vocation": 0}
        
        def calc_trend(values: List[int]) -> float:
            n = len(values)
            if n < 2:
                return 0
            
            # 简单线性回归
            x_mean = (n - 1) / 2
            y_mean = sum(values) / n
            
            numerator = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
            denominator = sum((i - x_mean) ** 2 for i in range(n))
            
            if denominator == 0:
                return 0
            
            slope = numerator / denominator
            # 归一化到 -1 到 1
            return max(-1, min(1, slope / 10))
        
        return {
            "mind": calc_trend([p.mind for p in history]),
            "body": calc_trend([p.body for p in history]),
            "spirit": calc_trend([p.spirit for p in history]),
            "vocation": calc_trend([p.vocation for p in history])
        }
    
    def detect_anomalies(self, history: List[EnergyPoint]) -> List[dict]:
        """
        检测能量异常
        
        返回异常列表
        """
        if len(history) < 3:
            return []
        
        anomalies = []
        dimensions = ["mind", "body", "spirit", "vocation"]
        
        for dim in dimensions:
            values = [getattr(p, dim) for p in history]
            mean = sum(values) / len(values)
            std_dev = math.sqrt(sum((v - mean) ** 2 for v in values) / len(values))
            
            # 检查最新值是否异常（超过2个标准差）
            latest = values[-1]
            if std_dev > 0 and abs(latest - mean) > 2 * std_dev:
                anomalies.append({
                    "dimension": dim,
                    "value": latest,
                    "expected_range": (
                        max(0, mean - 2 * std_dev),
                        min(100, mean + 2 * std_dev)
                    ),
                    "type": "sudden_change"
                })
        
        return anomalies
    
    def predict_next(self, history: List[EnergyPoint]) -> Optional[EnergyPoint]:
        """
        预测下一个数据点
        
        基于简单移动平均
        """
        if len(history) < 3:
            return None
        
        # 使用最近3天的加权平均
        weights = [0.5, 0.3, 0.2]
        recent = history[-3:]
        
        predicted = EnergyPoint(
            date=date.today() + timedelta(days=1),
            mind=int(sum(p.mind * w for p, w in zip(recent, weights))),
            body=int(sum(p.body * w for p, w in zip(recent, weights))),
            spirit=int(sum(p.spirit * w for p, w in zip(recent, weights))),
            vocation=int(sum(p.vocation * w for p, w in zip(recent, weights)))
        )
        
        return predicted
    
    def generate_recommendations(self, point: EnergyPoint, momentum: dict) -> List[str]:
        """
        基于当前状态生成建议
        """
        recommendations = []
        
        # 低能量建议
        if point.mind < self.WARNING_THRESHOLD:
            recommendations.append("心智能量偏低，建议进行冥想或轻度阅读")
        if point.body < self.WARNING_THRESHOLD:
            recommendations.append("身体能量不足，建议适度运动或休息")
        if point.spirit < self.WARNING_THRESHOLD:
            recommendations.append("精神能量低迷，建议与朋友交流或做喜欢的事")
        if point.vocation < self.WARNING_THRESHOLD:
            recommendations.append("志业能量欠佳，建议回顾目标，重建动力")
        
        # 下降趋势建议
        for dim, value in momentum.items():
            if value < -0.3:
                dim_names = {"mind": "心智", "body": "身体", "spirit": "精神", "vocation": "志业"}
                recommendations.append(f"{dim_names[dim]}能量持续下降，需要关注")
        
        # 平衡性建议
        balance = self.calculate_balance_score(point)
        if balance < 60:
            min_dim = min(["mind", "body", "spirit", "vocation"], 
                         key=lambda d: getattr(point, d))
            dim_names = {"mind": "心智", "body": "身体", "spirit": "精神", "vocation": "志业"}
            recommendations.append(f"能量不平衡，{dim_names[min_dim]}是短板")
        
        return recommendations

