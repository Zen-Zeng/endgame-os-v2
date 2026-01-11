"""
统一记忆服务 (Cognitive Layer)
作为系统的“中枢”，负责协调“感知层”(NeuralProcessor) 和“存储层”(GraphStore/VectorStore)。
"""
from typing import List, Dict, Any, Tuple
from pathlib import Path
import logging
import uuid
import re
import asyncio
from datetime import datetime
from .vector_store import VectorStore
from .graph_store import GraphStore
from ..neural.processor import get_processor
from app.core.config import DATA_DIR, MemoryConfig

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MemoryService:
    def __init__(self, persist_directory=None, graph_db_path=None):
        if persist_directory is None:
            persist_directory = str(DATA_DIR / "chroma")
        if graph_db_path is None:
            graph_db_path = str(DATA_DIR / "brain.db")
            
        self.vector_store = VectorStore(persist_directory=persist_directory)
        self.graph_store = GraphStore(db_path=graph_db_path)
        # FileProcessor 移除，交由 IngestionService 管理
        # 感知层：只负责模型推理
        self.neural_processor = get_processor()
        
        # 核心注意力关键词
        self.core_keywords = MemoryConfig.CORE_KEYWORDS
        logger.info("MemoryService (Cognitive Center) 就绪")

    def clear_all_memories(self, user_id: str = None):
        """清空记忆：如果提供 user_id 则只清空该用户的数据，否则清空全部"""
        self.vector_store.clear_all_data() # ChromaDB 目前全局清空，后续可优化
        self.graph_store.clear_all_data(user_id=user_id)

    def get_stats(self, user_id: str = "default_user") -> Dict[str, Any]:
        """获取综合统计信息"""
        vector_stats = self.vector_store.get_stats()
        graph_stats = self.graph_store.get_stats(user_id=user_id)
        
        return {
            "vector": vector_stats,
            "graph": graph_stats,
            "total_documents": vector_stats.get("total_documents", 0),
            "total_nodes": graph_stats.get("node_counts", {}).get("total", 0),
            "total_links": graph_stats.get("relation_counts", {}).get("total", 0)
        }

    # --- 注意力过滤器 ---
    def _is_informative(self, text: str) -> bool:
        """激进的注意力策略：过滤 90% 的低价值对话"""
        if len(text) < MemoryConfig.MIN_TEXT_LENGTH: return False
        
        # 排除常见废话
        stop_phrases = ["好的", "收到", "谢谢", "明白", "再见", "ok", "thanks", "yes", "no", "bye"]
        if any(sp == text.lower().strip() for sp in stop_phrases): return False
        
        # 包含核心关键词或特定的动作特征
        has_core_keyword = any(k in text for k in self.core_keywords)
        has_logic_marker = any(m in text for m in ["因为", "所以", "但是", "如果", "定义", "实现", "属于"])
        
        return has_core_keyword or has_logic_marker

    async def process_chat_interaction(self, user_id: str, conversation_id: str, user_message: str, ai_response: str):
        """
        处理对话交互：
        1. 提取三元组 (左脑)
        2. 向量化存入 (右脑)
        """
        combined_text = f"User: {user_message}\nAI: {ai_response}"
        
        # 1. 注意力过滤
        if not self._is_informative(user_message) and not self._is_informative(ai_response):
            logger.info("对话信息量较低，跳过深度处理")
            return
            
        logger.info(f"开始处理对话记忆: {conversation_id}")
        
        # 2. 向量化存储 (右脑)
        chat_id = f"chat_{uuid.uuid4().hex[:8]}"
        embedding = self.neural_processor.embed_batch([combined_text])[0]
        self.vector_store.add_documents(
            documents=[combined_text],
            metadatas=[{"type": "chat", "user_id": user_id, "conversation_id": conversation_id, "timestamp": datetime.now().isoformat()}],
            ids=[chat_id],
            embeddings=[embedding]
        )
        
        # 3. 提取结构化记忆 (左脑) - [Strategic Brain] 注入 user_id
        structured_data = await self.neural_processor.extract_structured_memory(combined_text, user_id=user_id)
        entities = structured_data.get("entities", [])
        relations = structured_data.get("relations", [])

        if entities:
            logger.info(f"从对话中提取到 {len(entities)} 个实体")
            
            # [Strategic Brain] 自动标记状态
            # Self/Vision/Goal/Project/Concept 通常可以直接确认
            # Task/Person 建议进入 pending
            for e in entities:
                if e.get("type") in ["Task", "Person"] and e.get("status") is None:
                    e["status"] = "pending"
                elif e.get("status") is None:
                    e["status"] = "confirmed"
                    
            self.graph_store.upsert_entities_batch(user_id, entities)
            
            # 自动关联实体与当前对话的向量
            concepts_with_vectors = []
            for e in entities:
                # 只有 confirmed 的节点才建立向量索引，避免垃圾数据污染检索
                if e.get("status") == "confirmed":
                    cid = self.graph_store._get_stable_id(e["name"])
                    concepts_with_vectors.append({"id": cid, "name": e["name"], "vector": embedding})
            
            if concepts_with_vectors:
                self.graph_store.add_concepts_batch(user_id, concepts_with_vectors)

        if relations:
            logger.info(f"从对话中提取到 {len(relations)} 条关系")
            self.graph_store.upsert_relations_batch(user_id, relations)
        
        logger.info("对话记忆处理完成")

    # --- Phase 3 新增: 经验接口 ---
    def add_experience(self, user_id: str, trigger: str, insight: str, strategy: str) -> bool:
        """记录一条进化出来的经验"""
        exp_id = f"exp_{uuid.uuid4().hex[:8]}"
        # 1. 存入图谱
        success = self.graph_store.add_experience(user_id, exp_id, trigger, insight, strategy)
        
        # 2. 存入向量库 (以便检索)
        if success:
            text = f"场景: {trigger}\n洞察: {insight}\n策略: {strategy}"
            vector = self.neural_processor.embed_batch([text])[0]
            self.vector_store.add_experience_vector(exp_id, text, vector)
            
        return success

# 单例
_instance = None
def get_memory_service():
    global _instance
    if _instance is None: _instance = MemoryService()
    return _instance
