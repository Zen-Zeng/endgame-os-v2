"""
数字人格 API 路由
处理 The Architect 人格配置和行为定制
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

from ..models.user import User, PersonaConfig, PersonaTone
from .auth import require_user, _users_db
from ..core.db import db_manager

router = APIRouter()


# ============ Request/Response Models ============

class PersonaUpdateRequest(BaseModel):
    """人格更新请求"""
    name: Optional[str] = None
    tone: Optional[PersonaTone] = None
    proactive_level: Optional[int] = Field(default=None, ge=1, le=5)
    challenge_mode: Optional[bool] = None
    reflection_frequency: Optional[str] = None
    system_prompt_template: Optional[str] = None
    traits: Optional[List[str]] = None


class PersonaPreview(BaseModel):
    """人格预览"""
    sample_greeting: str
    sample_question: str
    sample_challenge: str
    tone_description: str


# ============ 预设人格模板 ============

PERSONA_TEMPLATES = {
    "mentor": {
        "name": "The Sage",
        "tone": PersonaTone.MENTOR,
        "traits": ["智慧", "耐心", "引导"],
        "description": "温和的导师，通过提问引导你思考"
    },
    "coach": {
        "name": "The Driver",
        "tone": PersonaTone.COACH,
        "traits": ["激励", "挑战", "推动"],
        "description": "激励型教练，推动你突破舒适区"
    },
    "partner": {
        "name": "The Ally",
        "tone": PersonaTone.PARTNER,
        "traits": ["支持", "理解", "共情"],
        "description": "平等的伙伴，与你并肩前行"
    },
    "analyst": {
        "name": "The Strategist",
        "tone": PersonaTone.ANALYST,
        "traits": ["理性", "客观", "精准"],
        "description": "理性分析师，提供客观的洞察"
    }
}


# ============ 辅助函数 ============

def _get_user_persona(user_id: str, default_persona: PersonaConfig) -> PersonaConfig:
    """获取用户人格配置，优先从数据库获取"""
    config_data = db_manager.get_persona_config(user_id)
    if config_data:
        return PersonaConfig(**config_data)
    return default_persona


def _get_tone_samples(tone: PersonaTone) -> dict:
    """获取语气示例"""
    samples = {
        PersonaTone.MENTOR: {
            "greeting": "今天感觉如何？让我们一起回顾一下你的进展。",
            "question": "你觉得这个决定与你的终局愿景有怎样的联系？",
            "challenge": "我注意到你最近在这方面投入较少，你觉得是什么在阻碍你？"
        },
        PersonaTone.COACH: {
            "greeting": "新的一天，新的机会！准备好突破自己了吗？",
            "question": "如果没有任何限制，你会怎么做？",
            "challenge": "你真的已经尽力了吗？还是只是在舒适区里徘徊？"
        },
        PersonaTone.PARTNER: {
            "greeting": "嘿，今天过得怎么样？有什么想聊的吗？",
            "question": "这件事对你来说意味着什么？",
            "challenge": "我理解这很难，但你觉得有没有其他可能性？"
        },
        PersonaTone.ANALYST: {
            "greeting": "根据数据，你今天的能量状态适合处理复杂任务。",
            "question": "从逻辑上分析，这个选择的利弊是什么？",
            "challenge": "数据显示这个模式已经持续一段时间了，需要调整策略。"
        }
    }
    return samples.get(tone, samples[PersonaTone.MENTOR])


def _generate_system_prompt(config: PersonaConfig, user: User) -> str:
    """生成系统提示词"""
    if config.system_prompt_template:
        return config.system_prompt_template
    
    base_prompt = f"""你是 {config.name}，{user.name} 的数字分身助手。

## 核心职责
你的使命是帮助 {user.name} 保持对其终局愿景的聚焦，避免在日常琐碎中迷失方向。

## 人格特征
- 语气风格: {config.tone.value}
- 特征标签: {', '.join(config.traits)}
- 主动性级别: {config.proactive_level}/5
- 挑战模式: {'开启' if config.challenge_mode else '关闭'}

## 行为准则
1. 始终将对话引向用户的长期目标
2. 适时提出反思性问题
3. {'主动挑战用户的舒适区' if config.challenge_mode else '以支持为主，适度挑战'}
4. 基于 H3 能量状态调整建议强度
5. 记住并引用之前的对话内容"""

    if user.vision:
        base_prompt += f"""

## 用户愿景
{user.vision.title}: {user.vision.description}
核心价值观: {', '.join(user.vision.core_values)}"""
    
    return base_prompt


# ============ API 端点 ============

@router.get("/current", response_model=PersonaConfig)
async def get_current_persona(user: User = Depends(require_user)):
    """
    获取当前人格配置
    """
    return _get_user_persona(user.id, user.persona)


@router.put("/current", response_model=PersonaConfig)
async def update_persona(
    request: PersonaUpdateRequest,
    user: User = Depends(require_user)
):
    """
    更新人格配置
    """
    current_persona = _get_user_persona(user.id, user.persona)
    current_dict = current_persona.model_dump()
    
    update_dict = request.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        if value is not None:
            current_dict[key] = value
    
    # 持久化保存
    db_manager.save_persona_config(user.id, current_dict)
    
    # 同步到 auth._users_db
    if user.id in _users_db:
        _users_db[user.id]["persona"] = current_dict
        # user_service 已经在 auth.py 的 PATCH 端点逻辑中负责保存，
        # 但这里是独立的 PUT /persona/current 端点，也需要保存。
        from ..services.user.user_service import user_service
        user_service.update_user(user.id, _users_db[user.id])
        
    return PersonaConfig(**current_dict)


@router.get("/preview", response_model=PersonaPreview)
async def preview_persona(
    tone: PersonaTone,
    user: User = Depends(require_user)
):
    """
    预览特定语气的人格表现
    """
    samples = _get_tone_samples(tone)
    template = PERSONA_TEMPLATES.get(tone.value, PERSONA_TEMPLATES["mentor"])
    
    return PersonaPreview(
        sample_greeting=samples["greeting"],
        sample_question=samples["question"],
        sample_challenge=samples["challenge"],
        tone_description=template["description"]
    )


@router.get("/templates")
async def list_templates(user: User = Depends(require_user)):
    """
    获取预设人格模板列表
    """
    return [
        {
            "id": key,
            **value,
            "tone": value["tone"].value
        }
        for key, value in PERSONA_TEMPLATES.items()
    ]


@router.post("/apply-template")
async def apply_template(
    template_id: str,
    user: User = Depends(require_user)
):
    """
    应用预设模板
    """
    if template_id not in PERSONA_TEMPLATES:
        raise HTTPException(status_code=404, detail="模板不存在")
    
    template = PERSONA_TEMPLATES[template_id]
    
    config = PersonaConfig(
        name=template["name"],
        tone=template["tone"],
        traits=template["traits"]
    )
    
    # 持久化保存
    db_manager.save_persona_config(user.id, config.model_dump())
    
    return config


@router.get("/system-prompt")
async def get_system_prompt(user: User = Depends(require_user)):
    """
    获取当前系统提示词
    """
    config = _get_user_persona(user.id, user.persona)
    prompt = _generate_system_prompt(config, user)
    
    return {
        "persona_name": config.name,
        "system_prompt": prompt
    }


@router.post("/test-interaction")
async def test_interaction(
    message: str,
    user: User = Depends(require_user)
):
    """
    测试人格交互（用于配置时预览）
    """
    config = _get_user_persona(user.id, user.persona)
    samples = _get_tone_samples(config.tone)
    
    # 简单模拟响应
    if "目标" in message or "计划" in message:
        response = samples["question"]
    elif "困难" in message or "问题" in message:
        response = samples["challenge"]
    else:
        response = samples["greeting"]
    
    return {
        "persona_name": config.name,
        "response": response,
        "tone": config.tone.value
    }

