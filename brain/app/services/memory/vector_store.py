"""
ChromaDB 向量存储 (Final Stable Version)
"""
import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any, Optional
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VectorStore:
    def __init__(self, persist_directory: str = "./data/chroma"):
        self.persist_directory = persist_directory
        self._initialize_client()

    def _initialize_client(self):
        try:
            Path(self.persist_directory).mkdir(parents=True, exist_ok=True)
            self.client = chromadb.PersistentClient(
                path=str(self.persist_directory),
                settings=Settings(anonymized_telemetry=False, allow_reset=True)
            )
            # 关键：禁用内置函数，允许 1024 维向量
            self.collection = self.client.get_or_create_collection(
                name="endgame_memory",
                metadata={"hnsw:space": "cosine"},
                embedding_function=None 
            )
            self.concept_collection = self.client.get_or_create_collection(
                name="endgame_concepts",
                metadata={"hnsw:space": "cosine"},
                embedding_function=None
            )
            logger.info("ChromaDB 初始化成功 (自定义向量模式)")
        except Exception as e:
            logger.error(f"ChromaDB 初始化失败: {e}")
            raise

    def clear_all_data(self):
        try:
            self.client.delete_collection("endgame_memory")
            self.client.delete_collection("endgame_concepts")
            self._initialize_client()
        except Exception: pass

    def add_documents(self, documents: List[str], metadatas: List[Dict], ids: List[str], embeddings: List[List[float]] = None) -> bool:
        if not documents or embeddings is None: 
            logger.error("添加文档失败：必须提供 embeddings")
            return False
        try:
            self.collection.add(documents=documents, metadatas=metadatas, ids=ids, embeddings=embeddings)
            return True
        except Exception as e:
            logger.error(f"Chroma 添加失败: {e}")
            return False

    def add_concept(self, concept_id: str, name: str, vector: List[float]) -> bool:
        try:
            self.concept_collection.add(ids=[concept_id], embeddings=[vector], metadatas=[{"name": name}])
            return True
        except Exception: return False

    def find_similar_concept(self, vector: List[float], threshold: float = 0.85) -> Optional[Dict[str, Any]]:
        try:
            results = self.concept_collection.query(query_embeddings=[vector], n_results=1)
            if results['ids'] and results['ids'][0]:
                if results['distances'][0][0] < (1 - threshold):
                    return {'id': results['ids'][0][0], 'name': results['metadatas'][0][0]['name']}
            return None
        except Exception: return None

    def similarity_search(self, query_vector: List[float], n_results: int = 5) -> List[Dict]:
        try:
            results = self.collection.query(query_embeddings=[query_vector], n_results=n_results)
            formatted = []
            if results['documents']:
                for i, doc in enumerate(results['documents'][0]):
                    formatted.append({'content': doc, 'metadata': results['metadatas'][0][i]})
            return formatted
        except Exception: return []
    
    def get_stats(self):
        return {"count": self.collection.count()}