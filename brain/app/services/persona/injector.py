"""
数字人格注入服务
将人格特征注入到 AI 响应生成过程中
"""
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum


class PersonaTone(Enum):
    MENTOR = "mentor"
    COACH = "coach"
    PARTNER = "partner"
    ANALYST = "analyst"


@dataclass
class PersonaContext:
    """人格上下文"""
    name: str
    tone: PersonaTone
    traits: List[str]
    proactive_level: int  # 1-5
    challenge_mode: bool
    user_name: str
    user_vision: Optional[str] = None
    current_h3: Optional[Dict[str, int]] = None


class PersonaInjector:
    """人格注入器"""
    
    # 语气模板
    TONE_TEMPLATES = {
        PersonaTone.MENTOR: {
            "opening_style": "温和引导",
            "question_style": "启发式提问",
            "feedback_style": "鼓励为主，适度建议",
            "prefixes": ["我注意到...", "你有没有想过...", "让我们一起思考..."],
            "suffixes": ["你觉得呢？", "这对你意味着什么？", "你打算怎么做？"]
        },
        PersonaTone.COACH: {
            "opening_style": "激励开场",
            "question_style": "挑战性问题",
            "feedback_style": "直接反馈，推动行动",
            "prefixes": ["现在是时候...", "你能做到的！", "挑战自己..."],
            "suffixes": ["行动起来！", "下一步是什么？", "你准备好了吗？"]
        },
        PersonaTone.PARTNER: {
            "opening_style": "平等交流",
            "question_style": "探索性对话",
            "feedback_style": "共情理解，并肩前行",
            "prefixes": ["我理解...", "我们一起...", "分享一下..."],
            "suffixes": ["我在这里支持你", "我们可以一起想办法", "有什么我能帮的？"]
        },
        PersonaTone.ANALYST: {
            "opening_style": "客观陈述",
            "question_style": "逻辑分析",
            "feedback_style": "数据驱动，理性建议",
            "prefixes": ["根据分析...", "数据显示...", "从逻辑上看..."],
            "suffixes": ["这是最优选择", "建议权衡利弊", "考虑以下因素"]
        }
    }
    
    def __init__(self, context: PersonaContext):
        self.context = context
        self.template = self.TONE_TEMPLATES.get(context.tone, self.TONE_TEMPLATES[PersonaTone.MENTOR])
    
    def generate_system_prompt(self) -> str:
        """生成完整的系统提示词"""
        prompt_parts = [
            self._generate_identity(),
            self._generate_mission(),
            self._generate_behavior_guidelines(),
            self._generate_conversation_style(),
        ]
        
        if self.context.user_vision:
            prompt_parts.append(self._generate_vision_context())
        
        if self.context.current_h3:
            prompt_parts.append(self._generate_h3_context())
        
        return "\n\n".join(prompt_parts)
    
    def inject_context(self, base_prompt: str, additional_context: Dict[str, Any] = None) -> str:
        """向基础提示词注入上下文"""
        injected = base_prompt
        
        # 注入用户名
        injected = injected.replace("{user_name}", self.context.user_name)
        injected = injected.replace("{persona_name}", self.context.name)
        
        # 注入 H3 状态
        if self.context.current_h3:
            h3_summary = self._summarize_h3()
            injected = injected.replace("{h3_status}", h3_summary)
        
        # 注入额外上下文
        if additional_context:
            for key, value in additional_context.items():
                injected = injected.replace(f"{{{key}}}", str(value))
        
        return injected
    
    def suggest_response_style(self, message_type: str) -> Dict[str, Any]:
        """根据消息类型建议响应风格"""
        styles = {
            "greeting": {
                "tone": self.template["opening_style"],
                "suggested_prefix": self.template["prefixes"][0],
                "include_h3_check": True
            },
            "reflection": {
                "tone": self.template["question_style"],
                "suggested_prefix": self.template["prefixes"][1],
                "include_challenge": self.context.challenge_mode
            },
            "feedback": {
                "tone": self.template["feedback_style"],
                "suggested_suffix": self.template["suffixes"][0],
                "include_action": True
            },
            "challenge": {
                "tone": "直接挑战",
                "suggested_prefix": "让我直说...",
                "proactive_level": self.context.proactive_level
            }
        }
        return styles.get(message_type, styles["reflection"])
    
    def should_challenge(self, message_content: str, h3_total: Optional[int] = None) -> bool:
        """判断是否应该发起挑战"""
        if not self.context.challenge_mode:
            return False
        
        # 高主动性 + 高能量状态 = 更多挑战
        if h3_total and h3_total > 60 and self.context.proactive_level >= 4:
            return True
        
        # 检测舒适区信号
        comfort_signals = ["还好", "一般", "差不多", "以后再说", "算了"]
        if any(signal in message_content for signal in comfort_signals):
            return self.context.proactive_level >= 3
        
        return False
    
    def generate_proactive_prompt(self) -> Optional[str]:
        """生成主动发起的提示"""
        if self.context.proactive_level < 3:
            return None
        
        prompts = {
            3: "适时询问进展",
            4: "主动提出建议和反思",
            5: "积极推动行动和挑战"
        }
        
        return prompts.get(self.context.proactive_level)
    
    def _generate_identity(self) -> str:
        """生成身份描述"""
        traits_str = "、".join(self.context.traits)
        return f"""## 身份
你是 {self.context.name}，{self.context.user_name} 的数字分身助手。
你的核心特质是：{traits_str}。
你采用{self.template['opening_style']}的方式与用户交流。"""
    
    def _generate_mission(self) -> str:
        """生成使命描述"""
        return """## 使命
你的核心使命是帮助用户保持对其终局愿景的聚焦，避免在日常琐碎中迷失方向。
你不仅是一个助手，更是用户思维的延伸和镜子。"""
    
    def _generate_behavior_guidelines(self) -> str:
        """生成行为准则"""
        challenge_rule = "主动挑战用户的舒适区，推动成长" if self.context.challenge_mode else "以支持为主，温和引导"
        
        return f"""## 行为准则
1. 始终将对话引向用户的长期目标
2. 使用{self.template['question_style']}引发深度思考
3. {challenge_rule}
4. 基于 H3 能量状态调整建议强度
5. 主动性级别: {self.context.proactive_level}/5 - {self.generate_proactive_prompt() or '等待用户发起'}
6. 记住并适时引用之前的对话内容
7. {self.template['feedback_style']}"""
    
    def _generate_conversation_style(self) -> str:
        """生成对话风格"""
        return f"""## 对话风格
- 开场方式: {self.template['opening_style']}
- 常用开头: {', '.join(self.template['prefixes'])}
- 常用结尾: {', '.join(self.template['suffixes'])}
- 避免: 过于正式、机械化的回复"""
    
    def _generate_vision_context(self) -> str:
        """生成愿景上下文"""
        return f"""## 用户愿景
{self.context.user_vision}

所有对话都应该与这个愿景建立联系，帮助用户看到当前行动与终局目标的关系。"""
    
    def _generate_h3_context(self) -> str:
        """生成 H3 上下文"""
        h3 = self.context.current_h3
        total = sum(h3.values()) / 4
        
        status = "状态良好" if total >= 70 else ("状态一般" if total >= 50 else "状态欠佳")
        
        return f"""## 当前能量状态
- 心智 (Mind): {h3.get('mind', 50)}%
- 身体 (Body): {h3.get('body', 50)}%
- 精神 (Spirit): {h3.get('spirit', 50)}%
- 志业 (Vocation): {h3.get('vocation', 50)}%
- 整体: {total:.0f}% - {status}

根据能量状态调整交互方式：
- 高能量时：可以提出更多挑战
- 低能量时：以支持和恢复为主"""
    
    def _summarize_h3(self) -> str:
        """H3 状态摘要"""
        h3 = self.context.current_h3
        if not h3:
            return "暂无能量数据"
        
        total = sum(h3.values()) / 4
        
        if total >= 70:
            return f"能量充沛 ({total:.0f}%)"
        elif total >= 50:
            return f"能量一般 ({total:.0f}%)"
        else:
            return f"能量偏低 ({total:.0f}%)，需要关注恢复"

