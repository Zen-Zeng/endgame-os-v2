from typing import Dict, Any, List
from pathlib import Path
import logging
import asyncio
import uuid
import json
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
            
            # 新流程: 上传 -> 分块 -> DeepSeek结构化 -> 向量化 -> 图谱化
            # 直接返回给后台任务处理
            return {
                "success": True, 
                "message": "文件解析完成，准备进行DeepSeek结构化处理",
                "chunks": len(chunks),
                "deepseek_task_args": (chunks, metadata)
            }
        except Exception as e:
            logger.error(f"Ingest Error: {e}")
            return {'success': False, 'error': str(e)}

    async def process_deepseek_pipeline(self, chunks: List[str], metadata: Dict[str, Any], progress_callback=None):
        """
        [DeepSeek Pipeline]
        分块 -> 结构化 -> 向量化 -> 图谱化
        """
        from app.core.config import ENDGAME_VISION # Lazy import to avoid circular dependency
        
        total = len(chunks)
        logger.info(f"开始 DeepSeek 流水线，总计 {total} 个切片")
        user_id = metadata.get("user_id", "default_user")
        vision_context = ENDGAME_VISION

        # 1. 结构化 (DeepSeek)
        structured_results = []
        for i, chunk in enumerate(chunks):
            if progress_callback:
                progress_callback(30 + int((i / total) * 30), f"DeepSeek 正在结构化切片 {i+1}/{total}...")
            logger.info(f"DeepSeek 正在处理切片 {i+1}/{total}...")
            res = await self.memory_service.neural_processor.extract_structured_memory_deepseek(chunk, vision_context)
            if res:
                structured_results.append(res)
        
        # 2. 准备数据
        if progress_callback: progress_callback(60, "正在整理结构化数据...")
        all_nodes = []
        all_edges = []
        vectors_to_add = [] # (id, text, metadata)
        
        # ID 映射表 (DeepSeek ID -> Stable ID)
        id_map = {}
        
        # 处理结构化数据
        for res in structured_results:
            nodes = res.get("nodes", [])
            edges = res.get("edges", [])
            
            # 第一遍：生成 Stable IDs
            for node in nodes:
                original_id = node.get("id")
                name = node.get("name", "Unknown")
                node_type = node.get("type", "Concept")
                
                # [Strategic Brain] 强一致性 ID 归一化: Vision 和 Self 节点使用固定 ID
                if node_type == "Vision":
                    stable_id = f"vision_{user_id}"
                elif node_type == "Self":
                    stable_id = user_id
                else:
                    # 其他节点使用 GraphStore 的确定性 ID 生成逻辑
                    stable_id = self.memory_service.graph_store._get_stable_id(name)
                
                if original_id:
                    id_map[original_id] = stable_id
                
                # 更新 Node ID
                node["id"] = stable_id
                
                # 添加到图谱待写入列表
                all_nodes.append({
                    "id": stable_id,
                    "user_id": user_id,
                    "type": node_type,
                    "name": name,
                    "content": node.get("content", ""),
                    "attributes": {}
                })
                
                # 筛选需要向量化的节点 (Goal, Project)
                if node.get("type") in ["Goal", "Project"]:
                    vectors_to_add.append({
                        "id": stable_id,
                        "text": node.get("content") or name,
                        "metadata": {"name": name, "type": node.get("type"), "user_id": user_id}
                    })
            
            # 第二遍：更新 Edges 的 Source/Target
            for edge in edges:
                src = edge.get("source")
                tgt = edge.get("target")
                
                # 尝试映射，如果映射失败保留原值
                final_src = id_map.get(src, src)
                final_tgt = id_map.get(tgt, tgt)
                
                all_edges.append({
                    "source": final_src,
                    "target": final_tgt,
                    "relation": edge["relation"],
                    "user_id": user_id
                })

        # 3. 向量化 & 存储向量
        # A. 节点向量化
        if vectors_to_add:
            if progress_callback: progress_callback(70, f"正在向量化 {len(vectors_to_add)} 个关键节点...")
            logger.info(f"正在向量化 {len(vectors_to_add)} 个关键节点...")
            texts = [v["text"] for v in vectors_to_add]
            ids = [v["id"] for v in vectors_to_add]
            metadatas = [v["metadata"] for v in vectors_to_add]
            
            embeddings = await asyncio.to_thread(
                self.memory_service.neural_processor.embed_batch, 
                texts
            )
            
            await asyncio.to_thread(
                self.memory_service.vector_store.add_documents,
                texts, metadatas, ids, embeddings
            )

        # B. 原始切片向量化 (保持全文检索能力)
        if chunks:
            if progress_callback: progress_callback(80, "正在向量化原始文本切片...")
            logger.info("正在向量化原始切片...")
            chunk_embeddings = await asyncio.to_thread(
                self.memory_service.neural_processor.embed_batch,
                chunks
            )
            chunk_ids = [f"chunk_{uuid.uuid4().hex[:8]}" for _ in chunks]
            chunk_metadatas = [metadata] * len(chunks)
            
            await asyncio.to_thread(
                self.memory_service.vector_store.add_documents,
                chunks, chunk_metadatas, chunk_ids, chunk_embeddings
            )

        # 4. 图谱存储 (Nodes & Edges)
        if progress_callback: progress_callback(90, f"正在写入图谱: {len(all_nodes)} 节点, {len(all_edges)} 关系...")
        logger.info(f"正在写入图谱: {len(all_nodes)} Nodes, {len(all_edges)} Edges")
        try:
            with self.memory_service.graph_store._get_conn() as conn:
                # 预设对齐分：Vision/Self 节点设为 1.0，其他默认为 0.5 (中性对齐，防止滑块拉一点就全消失)
                db_nodes = []
                for n in all_nodes:
                    score = 0.5
                    if n["type"] in ["Vision", "Self"]:
                        score = 1.0
                    
                    db_nodes.append((
                        n["id"], n["user_id"], n["type"], n["name"], 
                        n["content"], json.dumps(n["attributes"]), score
                    ))

                conn.executemany("""
                    INSERT OR REPLACE INTO nodes (id, user_id, type, name, content, attributes, alignment_score)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, db_nodes)
            
                db_edges = [(e["source"], e["target"], e["relation"], e["user_id"]) for e in all_edges]
                conn.executemany("""
                    INSERT OR IGNORE INTO edges (source, target, relation, user_id)
                    VALUES (?, ?, ?, ?)
                """, db_edges)
                conn.commit()
        except Exception as e:
            logger.error(f"Graph DB Write Failed: {e}")

        if progress_callback: progress_callback(100, "DeepSeek 流水线处理完成")
        logger.info("DeepSeek 流水线完成")

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
