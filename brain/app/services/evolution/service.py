"""
Evolution Service (进化服务)
负责系统的自我反思 (Self-Questioning)、归因 (Self-Attributing) 和经验沉淀。
实现 AgentEvolver 核心逻辑。
"""
import uuid
import logging
import asyncio
from typing import List, Optional
from datetime import datetime
from google import genai
from google.genai import types

from ..memory.memory_service import get_memory_service
from app.core.config import MODEL_CONFIG

logger = logging.getLogger(__name__)

class EvolutionService:
    def __init__(self):
        self.memory_service = get_memory_service()
        self.neural_processor = self.memory_service.neural_processor
        # 使用较低温度以保证分析的理性
        api_key = MODEL_CONFIG.get("gemini_api_key")
        if api_key:
            self.client = genai.Client(api_key=api_key)
            self.model_name = "gemini-2.0-flash"
        else:
            self.client = None
            logger.warning("EvolutionService: 未配置 Gemini API Key")

    async def evolve(self, user_id: str, user_query: str, current_response: str, user_feedback: str = ""):
        """
        触发一次微进化 (Micro-Evolution)
        当对话结束或用户反馈时调用
        """
        logger.info(f"开始进化分析: User={user_query[:20]}...")
        
        # 1. 自我归因 (Self-Attributing): 分析这次交互好不好
        prompt = f"""
        我是来自5年后的主脑，正在进行夜间复盘。
        
        场景信息：
        - 用户输入: "{user_query}"
        - 我的回答: "{current_response}"
        - 用户反馈: "{user_feedback}" (为空表示无直接反馈)
        
        任务：
        请客观分析这次交互。如果我的回答完美，则无需生成经验。
        如果存在改进空间（例如：语气不对、忽略了用户情绪、建议不切实际、回答过于啰嗦等），
        请生成一条【策略经验】，指导我下次遇到类似情况该怎么做。
        
        输出格式（严格遵守）：
        如果没有改进必要，仅输出 "PASS"。
        如果有改进必要，输出格式如下：
        TRIGGER: [触发场景简述]
        INSIGHT: [问题归因/洞察]
        STRATEGY: [具体的改进策略/行动指南]
        """
        
        try:
            if not self.client:
                return

            def _sync_generate():
                return self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config={
                        "temperature": 0.2
                    }
                )

            response = await asyncio.to_thread(_sync_generate)
            content = response.text.strip()
            
            if content == "PASS":
                logger.info("进化分析: 本次交互无显著改进点")
                return

            # 解析返回结果
            lines = content.split('\n')
            trigger, insight, strategy = "", "", ""
            
            for line in lines:
                if line.startswith("TRIGGER:"): trigger = line.replace("TRIGGER:", "").strip()
                elif line.startswith("INSIGHT:"): insight = line.replace("INSIGHT:", "").strip()
                elif line.startswith("STRATEGY:"): strategy = line.replace("STRATEGY:", "").strip()
            
            if trigger and strategy:
                self.create_experience(user_id, trigger, insight, strategy)
            else:
                logger.warning(f"进化分析格式解析失败: {content}")
                
        except Exception as e:
            logger.error(f"进化过程出错: {e}")

    def create_experience(self, user_id: str, trigger: str, insight: str, strategy: str):
        """将反思结果存入双脑"""
        exp_id = f"exp_{uuid.uuid4().hex[:8]}"
        
        # 1. 存入 SQLite (结构化存储，用于展示和管理)
        success = self.memory_service.graph_store.add_experience(user_id, exp_id, trigger, insight, strategy)
        
        if success:
            # 2. 存入 Chroma (向量化，用于检索)
            # 组合 Trigger 和 Insight 作为检索键，因为用户下次也是在类似场景(Trigger)下出现类似问题
            content = f"场景: {trigger}\n洞察: {insight}"
            
            # 获取向量
            vec = self.neural_processor.embed_batch([content])[0]
            
            # 存入向量库，注意：我们存入的内容是 content，但在 add_experience_vector 中我们实际上不需要 text 用于检索，
            # 这里 vector_store.add_experience_vector 需要 documents 参数
            # 实际上检索出来给 Prompt 用的是 Strategy
            self.memory_service.vector_store.add_experience_vector(exp_id, strategy, vec)
            
            logger.info(f"进化完成！新策略已沉淀: {strategy}")
        else:
            logger.error("经验存储失败")

    def get_guidance(self, current_query: str) -> str:
        """获取进化后的指导策略 (用于注入 Prompt)"""
        try:
            # 向量化当前用户输入
            vec = self.neural_processor.embed_batch([current_query])[0]
            
            # 检索最相关的 3 条经验
            strategies = self.memory_service.vector_store.search_experiences(vec, n_results=3)
            
            if not strategies:
                return ""
            
            guidance = "\n".join([f"- {s}" for s in strategies])
            return guidance
        except Exception as e:
            logger.error(f"获取指导失败: {e}")
            return ""

# 单例
_instance = None
def get_evolution_service():
    global _instance
    if _instance is None: _instance = EvolutionService()
    return _instance
