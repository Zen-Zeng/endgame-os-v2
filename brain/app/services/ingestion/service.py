from typing import Dict, Any, List
from pathlib import Path
import logging
import asyncio
import uuid
from datetime import datetime

from app.services.memory.memory_service import get_memory_service
from app.services.memory.file_processor import FileProcessor
from app.core.config import DATA_DIR, MemoryConfig

logger = logging.getLogger(__name__)

class IngestionService:
    def __init__(self):
        self.memory_service = get_memory_service()
        self.file_processor = FileProcessor()
        # 使用集中配置
        self.core_keywords = MemoryConfig.CORE_KEYWORDS

    async def ingest_file(self, file_path: str, user_id: str = "default_user", progress_callback=None) -> Dict[str, Any]:
        """
        全链路异步文件摄入
        1. 文件解析 (同步/线程池)
        2. 向量化 (异步/同步)
        3. 图谱提取 (异步后台任务)
        """
        try:
            path = Path(file_path)
            if not path.exists(): return {'success': False, 'error': 'File not found'}
            filename = path.name
            
            # 尝试从文件名或文件元数据中提取原始时间
            original_timestamp = datetime.now().isoformat()
            try:
                from app.services.memory.archives import _files_db
                for fdoc in _files_db.values():
                    if fdoc.get("filename") == filename and fdoc.get("user_id") == user_id:
                        if fdoc.get("created_at"):
                            original_timestamp = fdoc["created_at"]
                            break
            except Exception:
                pass
            
            if progress_callback: progress_callback(10, "正在读取并解析文件内容...")

            # 准备元数据
            metadata = self.file_processor.get_file_metadata(file_path)
            metadata["user_id"] = user_id
            metadata["timestamp"] = original_timestamp
            
            # 文件解析 (CPU 密集型，放入线程池)
            chunks = await asyncio.to_thread(self.file_processor.parse_file, file_path)
            
            # 1. 向量化 (Vectorization)
            result = await self._process_vector_async(chunks, metadata, progress_callback)
            
            # 2. 图谱提取 (Graph Extraction)
            return {
                "success": True, 
                "message": "向量化完成，准备进行图谱提取",
                "chunks": len(chunks),
                "graph_task_args": (chunks, result['ids'], result['embeddings'], metadata)
            }
        except Exception as e:
            logger.error(f"Ingest Error: {e}")
            return {'success': False, 'error': str(e)}

    async def _process_vector_async(self, chunks: List[str], metadata: Dict[str, Any], progress_callback=None):
        """异步向量化处理"""
        file_id = f"file_{uuid.uuid4().hex[:8]}"
        all_ids = []
        all_embeddings = []
        
        BATCH_SIZE = MemoryConfig.VECTOR_BATCH_SIZE
        
        total_chunks = len(chunks)
        
        for i in range(0, total_chunks, BATCH_SIZE):
            batch = chunks[i : i + BATCH_SIZE]
            
            # NeuralProcessor 的 embed_batch 可能是同步的，使用 to_thread
            embeddings = await asyncio.to_thread(
                self.memory_service.neural_processor.embed_batch, 
                batch
            )
            
            ids = [f"{file_id}_c_{i+j}" for j in range(len(batch))]
            
            # VectorStore add 也可能是同步的
            await asyncio.to_thread(
                self.memory_service.vector_store.add_documents,
                batch, [metadata]*len(batch), ids, embeddings
            )
            
            all_ids.extend(ids)
            all_embeddings.extend(embeddings)
            
            if progress_callback:
                progress = min(10 + int((i + len(batch)) / total_chunks * 20), 30)
                progress_callback(progress, "正在进行向量化存储...")
                
        return {"ids": all_ids, "embeddings": all_embeddings}

    async def process_graph_task(self, chunks: List[str], ids: List[str], embeddings: List[List[float]], metadata: Dict[str, Any]):
        """
        后台图谱提取任务
        完全异步，适合 BackgroundTasks 调用
        """
        total = len(chunks)
        logger.info(f"开始后台图谱提取，总计 {total} 个切片")
        timestamp = metadata.get("timestamp", datetime.now().isoformat())
        user_id = metadata.get("user_id", "default_user")
        
        batch_size = 10
        for i in range(0, total, batch_size):
            batch_chunks = chunks[i:i+batch_size]
            batch_ids = ids[i:i+batch_size]
            batch_embeddings = embeddings[i:i+batch_size]
            
            tasks = []
            for j, text in enumerate(batch_chunks):
                if not self._is_informative(text):
                    continue
                
                chunk_id = batch_ids[j]
                # 记录日志 (SQLite 写入)
                await asyncio.to_thread(
                    self.memory_service.graph_store.add_log,
                    user_id, chunk_id, text[:200], timestamp, "file_chunk"
                )
                
                # 创建提取任务 (NeuralProcessor.extract_structured_memory 已经是 async)
                tasks.append(self.memory_service.neural_processor.extract_structured_memory(text))
            
            if not tasks:
                continue
                
            # 并行执行当前批次
            results = await asyncio.gather(*tasks)
            
            for idx, structured_data in enumerate(results):
                entities = structured_data.get("entities", [])
                relations = structured_data.get("relations", [])
                
                if entities:
                    for e in entities:
                        if "attributes" not in e: e["attributes"] = {}
                        e["attributes"]["last_mentioned"] = timestamp
                    
                    # 数据库操作转为异步线程
                    await asyncio.to_thread(
                        self.memory_service.graph_store.upsert_entities_batch,
                        user_id, entities
                    )
                    
                    concepts_with_vectors = []
                    mentions = []
                    for e in entities:
                        # 注意：_get_stable_id 是同步的纯计算函数，直接调用即可，或者放入 thread
                        cid = self.memory_service.graph_store._get_stable_id(e["name"])
                        concepts_with_vectors.append({"id": cid, "name": e["name"], "vector": batch_embeddings[idx]})
                        mentions.append((batch_ids[idx], cid))
                    
                    if concepts_with_vectors: 
                        await asyncio.to_thread(self.memory_service.graph_store.add_concepts_batch, user_id, concepts_with_vectors)
                    if mentions: 
                        await asyncio.to_thread(self.memory_service.graph_store.add_mentions_batch, user_id, mentions)

                if relations:
                    await asyncio.to_thread(self.memory_service.graph_store.upsert_relations_batch, user_id, relations)
            
            # 批次间停顿
            await asyncio.sleep(1) 
            logger.info(f"进度: {min(i + batch_size, total)}/{total}")
            
        logger.info("后台图谱提取完成")

    def _is_informative(self, text: str) -> bool:
        """激进的注意力策略"""
        if len(text) < MemoryConfig.MIN_TEXT_LENGTH: return False
        
        stop_phrases = ["好的", "收到", "谢谢", "明白", "再见", "ok", "thanks", "yes", "no", "bye"]
        if any(sp == text.lower().strip() for sp in stop_phrases): return False
        
        has_core_keyword = any(k in text for k in self.core_keywords)
        has_logic_marker = any(m in text for m in ["因为", "所以", "但是", "如果", "定义", "实现", "属于"])
        
        return has_core_keyword or has_logic_marker

# 单例模式
_ingestion_service = None
def get_ingestion_service():
    global _ingestion_service
    if _ingestion_service is None:
        _ingestion_service = IngestionService()
    return _ingestion_service
