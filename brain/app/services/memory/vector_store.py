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
            # 关键：禁用内置函数，允许自定义维度向量
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
            self.experience_collection = self.client.get_or_create_collection(
                name="endgame_experiences",
                metadata={"hnsw:space": "cosine"},
                embedding_function=None
            )
            
            # 自动维度检测与重置
            self._check_and_reset_if_needed()
            
            logger.info("ChromaDB 初始化成功 (自定义向量模式)")
        except Exception as e:
            logger.error(f"ChromaDB 初始化失败: {e}")
            raise

    def _check_and_reset_if_needed(self):
        """检测现有向量维度，如果不匹配则重置数据库"""
        try:
            # 获取一条数据来检查维度
            sample = self.collection.get(limit=1, include=['embeddings'])
            if sample and sample['embeddings'] is not None and len(sample['embeddings']) > 0:
                existing_dim = len(sample['embeddings'][0])
                target_dim = 1024 # BGE 模型维度
                if existing_dim != target_dim:
                    logger.warning(f"检测到维度不匹配: 现有 {existing_dim}, 目标 {target_dim}。正在重置向量数据库...")
                    self.clear_all_data()
        except Exception as e:
            logger.error(f"维度检查失败: {e}")

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
            error_msg = str(e)
            logger.error(f"Chroma 添加失败: {error_msg}")
            if "readonly database" in error_msg or "code: 1032" in error_msg:
                logger.warning("检测到 Chroma 数据库只读/锁定，尝试重新初始化...")
                try:
                    self._initialize_client()
                    # 重新初始化后重试一次
                    self.collection.add(documents=documents, metadatas=metadatas, ids=ids, embeddings=embeddings)
                    return True
                except Exception as retry_e:
                    logger.error(f"Chroma 重试失败: {retry_e}")
            return False

    def add_concept(self, concept_id: str, name: str, vector: List[float]) -> bool:
        try:
            self.concept_collection.add(ids=[concept_id], embeddings=[vector], metadatas=[{"name": name}])
            return True
        except Exception as e:
            error_msg = str(e)
            if "readonly database" in error_msg or "code: 1032" in error_msg:
                try:
                    self._initialize_client()
                    self.concept_collection.add(ids=[concept_id], embeddings=[vector], metadatas=[{"name": name}])
                    return True
                except Exception: pass
            return False

    def find_similar_concept(self, vector: List[float], threshold: float = 0.85) -> Optional[Dict[str, Any]]:
        try:
            results = self.concept_collection.query(query_embeddings=[vector], n_results=1)
            if results['ids'] and results['ids'][0]:
                if results['distances'][0][0] < (1 - threshold):
                    return {'id': results['ids'][0][0], 'name': results['metadatas'][0][0]['name']}
            return None
        except Exception: return None

    def similarity_search(self, query_vector: List[float], user_id: str = None, n_results: int = 5) -> List[Dict]:
        try:
            where = {"user_id": user_id} if user_id else None
            results = self.collection.query(
                query_embeddings=[query_vector], 
                n_results=n_results,
                where=where
            )
            formatted = []
            if results['documents']:
                for i, doc in enumerate(results['documents'][0]):
                    formatted.append({'content': doc, 'metadata': results['metadatas'][0][i]})
            return formatted
        except Exception as e:
            logger.error(f"向量检索失败: {e}")
            return []
    
    def get_stats(self):
        return {"count": self.collection.count()}

    def add_experience_vector(self, exp_id: str, text: str, vector: List[float]):
        """将经验存入向量库，以便检索"""
        try:
            self.experience_collection.add(
                ids=[exp_id],
                embeddings=[vector],
                documents=[text]
            )
        except Exception as e:
            logger.error(f"经验向量化失败: {e}")

    def search_experiences(self, query_vector: List[float], n_results: int = 3) -> List[str]:
        """检索相关的历史经验"""
        try:
            results = self.experience_collection.query(query_embeddings=[query_vector], n_results=n_results)
            return results['documents'][0] if results['documents'] else []
        except Exception: return []