"""
统一记忆服务 (Final Stable Version)
"""
from typing import List, Dict, Any
from pathlib import Path
import logging
import uuid
from datetime import datetime
from .vector_store import VectorStore
from .file_processor import FileProcessor
from .graph_store import GraphStore
from ..neural.processor import NeuralProcessor, create_processor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MemoryService:
    def __init__(self, persist_directory="./data/chroma", graph_db_path="./data/brain.db"):
        self.vector_store = VectorStore(persist_directory=persist_directory)
        self.graph_store = GraphStore(db_path=graph_db_path)
        self.file_processor = FileProcessor()
        # 强制使用 MPS/CUDA，确保速度
        self.neural_processor = create_processor(offline_mode=False)
        logger.info("MemoryService (SQLite+Chroma) 就绪")

    def clear_all_memories(self):
        self.vector_store.clear_all_data()
        self.graph_store.clear_all_data()

    def ingest_file(self, file_path: str) -> Dict[str, Any]:
        try:
            path = Path(file_path)
            if not path.exists(): return {'success': False, 'error': 'File not found'}
            
            # 1. 解析
            chunks = self.file_processor.parse_file(file_path)
            metadata = self.file_processor.get_file_metadata(file_path)
            
            # 2. 统一处理 (无论是JSON还是TXT，都视作文本流处理)
            # 如果是 JSON 对话，file_processor 会返回处理好的文本列表
            return self._process_batch(chunks, metadata)
            
        except Exception as e:
            logger.error(f"Ingest Error: {e}")
            return {'success': False, 'error': str(e)}

    def _process_batch(self, chunks: List[str], metadata: Dict[str, Any]):
        file_id = f"file_{uuid.uuid4().hex[:8]}"
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 写入父节点
        self.graph_store.add_log(file_id, f"File: {metadata.get('file_name')}", ts, "file_upload")
        
        BATCH_SIZE = 10 
        total_entities = 0
        
        for i in range(0, len(chunks), BATCH_SIZE):
            batch = chunks[i : i + BATCH_SIZE]
            
            # A. 批量计算向量 (GPU加速)
            embeddings = [self.neural_processor.embed_text(txt) for txt in batch]
            ids = [f"{file_id}_c_{i+j}" for j in range(len(batch))]
            metas = [metadata for _ in batch]
            
            # B. 存入 Chroma
            self.vector_store.add_documents(batch, metas, ids, embeddings)
            
            # C. 存入 SQLite 图谱 & 提取实体
            for j, text in enumerate(batch):
                chunk_id = ids[j]
                self.graph_store.add_log(chunk_id, text[:200], ts, "file_chunk")
                
                # 提取实体 (CPU/GPU)
                res = self.neural_processor.process_text(text)
                concepts = []
                relations = []
                
                for ent in res.get('entities', []):
                    if not ent.strip(): continue
                    cid = f"con_{hash(ent)}"
                    # 复用已经计算好的 embedding
                    concepts.append({"id": cid, "name": ent, "vector": res['embedding']})
                    relations.append((chunk_id, cid))
                
                if concepts: self.graph_store.add_concepts_batch(concepts)
                if relations: self.graph_store.add_mentions_batch(relations)
                total_entities += len(concepts)
                
        return {"success": True, "chunks": len(chunks), "entities": total_entities}

# 单例
_instance = None
def get_memory_service():
    global _instance
    if _instance is None: _instance = MemoryService()
    return _instance