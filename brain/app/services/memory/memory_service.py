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
import threading
from datetime import datetime
from .vector_store import VectorStore
from .file_processor import FileProcessor
from .graph_store import GraphStore
from ..neural.processor import get_processor
from app.core.config import DATA_DIR

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
        self.file_processor = FileProcessor()
        # 感知层：只负责模型推理
        self.neural_processor = get_processor()
        
        # 核心注意力关键词
        self.core_keywords = [
            "愿景", "目标", "架构", "设计", "重构", "优化", "学习", "计划", 
            "实现", "解决", "困难", "思考", "启发", "技术", "艺术", "财务自由",
            "社区", "创作", "开发者", "思想家", "认知", "终局"
        ]
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

    def ingest_file(self, file_path: str, user_id: str = "default_user", progress_callback=None) -> Dict[str, Any]:
        """
        同步：向量化 (快，右脑)
        异步：图谱提取 (慢，左脑)
        """
        try:
            path = Path(file_path)
            if not path.exists(): return {'success': False, 'error': 'File not found'}
            filename = path.name
            
            # 尝试从文件名或文件元数据中提取原始时间
            # 针对解析出来的对话文件，尝试获取其原始时间戳
            original_timestamp = datetime.now().isoformat()
            try:
                from .archives import _files_db
                for fdoc in _files_db.values():
                    if fdoc.get("filename") == filename and fdoc.get("user_id") == user_id:
                        if fdoc.get("created_at"):
                            original_timestamp = fdoc["created_at"]
                            break
            except Exception:
                pass
            
            if progress_callback: progress_callback(10, "正在读取并解析文件内容...")

            # 准备元数据，包含 user_id
            metadata = self.file_processor.get_file_metadata(file_path)
            metadata["user_id"] = user_id
            metadata["timestamp"] = original_timestamp
            
            # 处理大文件：流式读取切片
            chunks = self.file_processor.parse_file(file_path)
            
            # 1. 同步处理：右脑向量化 (保证数据立即可查)
            result = self._process_vector_sync(chunks, metadata, progress_callback)
            
            # 2. 异步处理：左脑图谱化 (使用后台线程启动异步循环)
            threading.Thread(
                target=self._run_async_graph_task, 
                args=(chunks, result['ids'], result['embeddings'], metadata),
                daemon=True
            ).start()
            
            return {
                "success": True, 
                "message": "向量化完成，图谱提取已在后台启动",
                "chunks": len(chunks)
            }
        except Exception as e:
            logger.error(f"Ingest Error: {e}")
            return {'success': False, 'error': str(e)}

    def _run_async_graph_task(self, chunks, ids, embeddings, metadata):
        """在独立线程中运行异步图谱任务"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self._process_graph_async(chunks, ids, embeddings, metadata))
        loop.close()

    # --- 注意力过滤器 ---
    def _is_informative(self, text: str) -> bool:
        """激进的注意力策略：过滤 90% 的低价值对话"""
        if len(text) < 20: return False
        
        # 排除常见废话
        stop_phrases = ["好的", "收到", "谢谢", "明白", "再见", "ok", "thanks", "yes", "no", "bye"]
        if any(sp == text.lower().strip() for sp in stop_phrases): return False
        
        # 包含核心关键词或特定的动作特征
        has_core_keyword = any(k in text for k in self.core_keywords)
        has_logic_marker = any(m in text for m in ["因为", "所以", "但是", "如果", "定义", "实现", "属于"])
        
        return has_core_keyword or has_logic_marker

    def _process_vector_sync(self, chunks: List[str], metadata: Dict[str, Any], progress_callback=None):
        """同步向量化：快速存入 ChromaDB"""
        file_id = f"file_{uuid.uuid4().hex[:8]}"
        all_ids = []
        all_embeddings = []
        
        BATCH_SIZE = 50 # 3.11 下向量化非常快
        for i in range(0, len(chunks), BATCH_SIZE):
            batch = chunks[i : i + BATCH_SIZE]
            embeddings = self.neural_processor.embed_batch(batch)
            ids = [f"{file_id}_c_{i+j}" for j in range(len(batch))]
            
            self.vector_store.add_documents(batch, [metadata]*len(batch), ids, embeddings)
            all_ids.extend(ids)
            all_embeddings.extend(embeddings)
            
            if progress_callback:
                progress = min(10 + int((i + len(batch)) / len(chunks) * 20), 30)
                progress_callback(progress, "正在进行向量化存储...")
                
        return {"ids": all_ids, "embeddings": all_embeddings}

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

    async def _process_graph_async(self, chunks: List[str], ids: List[str], embeddings: List[List[float]], metadata: Dict[str, Any]):
        """异步图谱化：使用 Gemini 提取核心逻辑"""
        total = len(chunks)
        logger.info(f"开始后台图谱提取，总计 {total} 个切片")
        timestamp = metadata.get("timestamp", datetime.now().isoformat())
        user_id = metadata.get("user_id", "default_user")
        
        # 批量处理以提高效率，同时避免 API 限制
        batch_size = 10
        for i in range(0, total, batch_size):
            batch_chunks = chunks[i:i+batch_size]
            batch_ids = ids[i:i+batch_size]
            batch_embeddings = embeddings[i:i+batch_size]
            
            tasks = []
            for j, text in enumerate(batch_chunks):
                if not self._is_informative(text):
                    continue
                
                # 记录日志
                chunk_id = batch_ids[j]
                self.graph_store.add_log(user_id, chunk_id, text[:200], timestamp, "file_chunk")
                
                # 创建提取任务
                tasks.append(self.neural_processor.extract_structured_memory(text))
            
            if not tasks:
                continue
                
            # 并行执行当前批次
            results = await asyncio.gather(*tasks)
            
            for idx, structured_data in enumerate(results):
                entities = structured_data.get("entities", [])
                relations = structured_data.get("relations", [])
                
                if entities:
                    # 为实体添加时间戳属性
                    for e in entities:
                        if "attributes" not in e: e["attributes"] = {}
                        e["attributes"]["last_mentioned"] = timestamp
                    self.graph_store.upsert_entities_batch(user_id, entities)
                    
                    concepts_with_vectors = []
                    mentions = []
                    for e in entities:
                        cid = self.graph_store._get_stable_id(e["name"])
                        # 使用对应切片的向量
                        concepts_with_vectors.append({"id": cid, "name": e["name"], "vector": batch_embeddings[idx]})
                        mentions.append((batch_ids[idx], cid))
                    
                    if concepts_with_vectors: self.graph_store.add_concepts_batch(user_id, concepts_with_vectors)
                    if mentions: self.graph_store.add_mentions_batch(user_id, mentions)

                if relations:
                    self.graph_store.upsert_relations_batch(user_id, relations)
            
            # 批次间稍微停顿，保护 API
            await asyncio.sleep(1) 
            logger.info(f"进度: {min(i + batch_size, total)}/{total}")
            
        logger.info("后台图谱提取完成")

# 单例
_instance = None
def get_memory_service():
    global _instance
    if _instance is None: _instance = MemoryService()
    return _instance
