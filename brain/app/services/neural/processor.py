"""
神经感知处理器 (Perception Layer)
专注于模型推理：提供向量化 (Embedding) 和 关系提取 (Gemini) 的原子能力。
"""
import logging
import json
import asyncio
from typing import List, Dict, Any, Tuple, Optional
import google.generativeai as genai
from app.core.config import MODEL_CONFIG

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NeuralProcessor:
    """
    神经感知处理器类
    集成 Gemini 关系提取和本地向量化模型
    """

    def __init__(self):
        """初始化神经处理器"""
        self.embedding_model = None
        self.embedding_model_name = MODEL_CONFIG["embedding_model"]
        
        # 初始化 Gemini
        self.api_key = MODEL_CONFIG.get("gemini_api_key")
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.gemini = genai.GenerativeModel(MODEL_CONFIG["gemini_model"])
            logger.info(f"Gemini 处理器就绪: {MODEL_CONFIG['gemini_model']}")
        else:
            self.gemini = None
            logger.warning("未配置 Gemini API Key，图谱提取功能将不可用")

    def _ensure_embedding_loaded(self):
        """确保向量化模型已加载（延迟加载）"""
        if self.embedding_model is not None:
            return

        try:
            from sentence_transformers import SentenceTransformer
            logger.info(f"正在加载本地向量化模型: {self.embedding_model_name}...")
            self.embedding_model = SentenceTransformer(self.embedding_model_name)
        except Exception as e:
            logger.error(f"向量模型加载失败: {e}")

    # --- 核心接口 1: 向量化 (右脑) ---
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """批量将文本转化为向量"""
        if not texts:
            return []
            
        self._ensure_embedding_loaded()
        if self.embedding_model is None:
            logger.error("无法执行向量化：模型未加载")
            return [[0.0] * 1024 for _ in texts] # 返回空向量占位
            
        try:
            embeddings = self.embedding_model.encode(texts)
            return embeddings.tolist()
        except Exception as e:
            logger.error(f"向量化执行出错: {e}")
            return [[0.0] * 1024 for _ in texts]

    # --- 核心接口 2: 结构化关系提取 (左脑) ---
    async def extract_structured_memory(self, text: str) -> Dict[str, Any]:
        """
        使用 Gemini 2.0 Flash 提取结构化记忆（实体 + 关系）
        """
        if not self.gemini:
            return {"entities": [], "relations": []}

        prompt = f"""
        你是一个专业的【个人终局操作系统 (Endgame OS)】知识提取引擎。
        你的任务是从用户的原始文本（如对话记录、笔记、文档）中提取深度的、结构化的【记忆实体】和【关系】。

        ### 提取规则：
        1. **识别实体 (Entities)**：
           - **Person**: 用户提到的重要人物，提取其背景、偏好、与用户的关系。
           - **Project**: 正在进行的具体项目、研究、创作或开发任务。
           - **Concept**: 核心知识点、方法论、独特观点或专业术语。
           - **Event**: 重要的时间点、里程碑、会议或生活经历。
           - **Experience**: 用户的感悟、情绪偏好、底层信念或性格特征。
           - **Tool**: 经常使用的软件、硬件、AI模型或物理工具。

        2. **构建档案 (Dossier)**：针对不同类型，提取以下维度的深度信息（JSON 格式）：
           - **Person**: {{"bio": "身份背景", "preferences": ["喜好1"], "interaction_history": "互动关键点"}}
           - **Project**: {{"status": "状态/进度", "tech_stack": ["技术栈"], "milestones": ["里程碑"], "architecture": "核心设计"}}
           - **Concept**: {{"definition": "核心定义", "principles": ["原则/定律"], "links": ["相关领域"]}}
           - **Experience**: {{"emotion": "情感基调", "insight": "核心感悟", "impact": "对未来的影响"}}
           - **Default**: {{"summary": "简要概述", "metadata": {{"key": "value"}}}}

        3. **提取关系 (Relations)**：
           - 捕捉实体间的逻辑关联（例如：Person -> WORKS_ON -> Project, Concept -> UNDERLIES -> Project）。
           - 关系应简洁明确（如：BELONGS_TO, PARTICIPATED_IN, DEFINES, LIKES）。

        ### 输出要求：
        必须返回纯 JSON 格式，严禁包含任何 Markdown 代码块标签或解释性文字。
        格式如下：
        {{
          "entities": [
            {{
              "name": "唯一名称",
              "type": "Person|Project|Concept|Event|Experience|Tool",
              "content": "核心描述文字",
              "dossier": {{ ...根据类型填充对应的结构化字段... }}
            }}
          ],
          "relations": [
            {{"source": "主体名", "relation": "关系名", "target": "客体名"}}
          ]
        }}

        ### 待处理文本：
        {text}
        """

        try:
            def _sync_generate():
                return self.gemini.generate_content(
                    prompt,
                    generation_config={
                        "response_mime_type": "application/json"
                    }
                )

            response = await asyncio.to_thread(_sync_generate)
            
            if not response or not response.text:
                return {"entities": [], "relations": []}
            
            data = json.loads(response.text)
            return {
                "entities": data.get("entities", []),
                "relations": data.get("relations", [])
            }
        except Exception as e:
            logger.error(f"Gemini 提取结构化记忆失败: {e}")
            return {"entities": [], "relations": []}

    # 为了保持向后兼容，暂时保留三元组接口的包装
    async def extract_triplets_with_gemini(self, text: str) -> List[Tuple[str, str, str]]:
        """向后兼容接口"""
        data = await self.extract_structured_memory(text)
        triplets = []
        for r in data.get("relations", []):
            triplets.append((r["source"], r["relation"], r["target"]))
        return triplets

    def get_embedding_dimension(self) -> int:
        """获取向量维度"""
        return 384 # all-MiniLM-L6-v2 的标准维度

# 单例模式
_processor_instance = None
def get_processor():
    global _processor_instance
    if _processor_instance is None:
        _processor_instance = NeuralProcessor()
    return _processor_instance
