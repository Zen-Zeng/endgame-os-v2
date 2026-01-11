"""
神经感知处理器 (Perception Layer)
专注于模型推理：提供向量化 (Embedding) 和 关系提取 (Gemini) 的原子能力。
"""
import logging
import json
import asyncio
import os
from typing import List, Dict, Any, Tuple, Optional
from google import genai
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
        
        # 初始化 Gemini (使用新版 SDK)
        self.api_key = MODEL_CONFIG.get("gemini_api_key")
        if self.api_key:
            # [Fix] 强制使用用户指定的代理 127.0.0.1:1082
            # 之前的逻辑可能被系统环境变量污染 (如 33210 端口)
            proxy_url = "http://127.0.0.1:1082"
            
            logger.info(f"Enforcing proxy settings to: {proxy_url}")
            os.environ["http_proxy"] = proxy_url
            os.environ["https_proxy"] = proxy_url
            os.environ["HTTP_PROXY"] = proxy_url
            os.environ["HTTPS_PROXY"] = proxy_url
            
            self.client = genai.Client(api_key=self.api_key)
            self.model_name = MODEL_CONFIG["gemini_model"]
            logger.info(f"Gemini 处理器就绪: {self.model_name} (Proxy: {proxy_url})")
        else:
            self.client = None
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

    async def arbitrate_merge(self, names: List[str]) -> Dict[str, Any]:
        """
        [Memory Consolidator]
        仲裁一组名称是否指向同一个实体，并生成标准名称。
        """
        if not self.client:
            return {"should_merge": False}
        
        prompt = f"""
        你是一个知识图谱管理员。以下是一组看起来相似的概念名称：
        {json.dumps(names, ensure_ascii=False)}

        请判断它们是否应该合并为同一个实体？
        规则：
        1. 仅当它们是同义词、缩写、单复数、或大小写变体时合并 (如 "RustLang" 和 "Rust", "AI" 和 "Artificial Intelligence")。
        2. 如果它们是明显不同的东西 (如 "Java" 和 "JavaScript")，请不要合并。
        3. 如果合并，请提供一个最标准、最通用的名称作为 'master_name'。

        返回 JSON:
        {{
            "should_merge": true/false,
            "master_name": "Standard Name" (仅当 should_merge 为 true 时必填),
            "reason": "简短理由"
        }}
        """

        try:
            def _sync_generate():
                return self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config={"response_mime_type": "application/json"}
                )
            
            response = await asyncio.to_thread(_sync_generate)
            return json.loads(response.text)
        except Exception as e:
            logger.error(f"Merge arbitration failed for {names}: {str(e)}")
            return {"should_merge": False, "reason": f"System error: {str(e)}"}

    async def summarize_text(self, text: str, prompt_template: str = None) -> str:
        """
        [通用能力] 使用 Gemini 总结文本
        """
        if not self.client:
            return text[:150] + "..." if len(text) > 150 else text

        prompt = prompt_template if prompt_template else f"请总结以下内容：\n{text}"

        try:
            def _sync_generate():
                return self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                )
            
            response = await asyncio.to_thread(_sync_generate)
            return response.text.strip()
        except Exception as e:
            logger.error(f"Summarize text failed: {e}")
            return text[:150] + "..." if len(text) > 150 else text

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
    async def extract_structured_memory(self, text: str, user_id: str = "default_user", chapter_start_date: str = None) -> Dict[str, Any]:
        """
        [Strategic Brain Upgrade]
        使用 Gemini 2.0 Flash 提取结构化记忆，注入主体意识和五层战略结构。
        """
        if not self.client:
            return {"entities": [], "relations": []}

        prompt = f"""
        你是一个【Endgame OS 战略大脑】的感知中枢。
        你的核心任务是：从文本中提取知识，并将其归位到以【Self ({user_id})】为中心的五层战略图谱中。

        ### 1. 核心原则：主体性 (Subjectivity)
        - **绝对主体**：文本中的“我”、“我们”、“本人”等第一人称表述，**必须**直接归属到 ID 为 `{user_id}` 的 Self 节点，**严禁**创建名为 "User" 或 "Me" 的新节点。
        - **外部识别**：只有当提到具体的第三方姓名（如“王总”、“Alice”）时，才创建 `Person` 节点。

        ### 2. 节点分类体系 (Node Ontology)
        请严格将提取的信息分类为以下 6 种类型：
        - **Vision**: 5年终局愿景（通常涉及人生方向、最终状态）。
        - **Goal**: 战略目标（OKR中的O，通常有明确的时间边界）。
        - **Project**: 执行项目（为了实现目标而做的一系列事情）。
        - **Task**: 原子任务（具体的行动项，TODO）。
        - **Person**: 外部联系人（协作者、朋友、客户）。
        - **Concept**: 认知/信念（方法论、知识点、价值观）。

        ### 3. 关系提取规则 (Predicates)
        - Self -> **OWNS** -> Vision
        - Vision -> **DECOMPOSES_TO** -> Goal
        - Goal -> **ACHIEVED_BY** -> Project
        - Project -> **CONSISTS_OF** -> Task
        - Self -> **EXECUTES** -> Task/Project
        - Self -> **KNOWS** -> Person
        - Person -> **SUPPORTS** -> Project
        - Self -> **BELIEVES** -> Concept

        ### 4. 输出要求 (JSON)
        {{
          "entities": [
            {{
              "name": "实体名称 (Self节点请直接填 '{user_id}')",
              "type": "Vision|Goal|Project|Task|Person|Concept",
              "content": "核心描述",
              "status": "pending",  // 默认为待确认
              "dossier": {{ ...详细属性... }}
            }}
          ],
          "relations": [
            {{"source": "主体ID", "relation": "谓语", "target": "客体ID"}}
          ]
        }}

        ### 待处理文本：
        {text}
        """

        try:
            def _sync_generate():
                return self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config={
                        "response_mime_type": "application/json"
                    }
                )

            response = await asyncio.to_thread(_sync_generate)
            
            if not response or not response.text:
                return {"entities": [], "relations": []}
            
            data = json.loads(response.text)
            
            # 后处理：确保 Self 节点不被重复创建为普通节点
            entities = data.get("entities", [])
            for e in entities:
                if e["name"] == user_id:
                    e["type"] = "Self" # 强制修正类型
                    
            return {
                "entities": entities,
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
