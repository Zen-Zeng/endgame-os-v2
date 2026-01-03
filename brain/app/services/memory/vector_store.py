"""
ChromaDB 向量存储封装
用于海马体记忆功能
"""
import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any, Optional
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VectorStore:
    """
    ChromaDB 向量存储类
    提供文档的向量化和语义搜索功能
    """

    def __init__(self, persist_directory: str = "./data/chroma"):
        """
        初始化 ChromaDB 客户端

        Args:
            persist_directory: 持久化存储目录
        """
        self.persist_directory = persist_directory
        self.client = None
        self.collection = None
        self._initialize_client()

    def _initialize_client(self):
        """
        初始化 ChromaDB 客户端和集合
        """
        try:
            persist_path = Path(self.persist_directory)
            persist_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"ChromaDB 持久化路径: {str(persist_path)}")

            # 创建持久化客户端
            self.client = chromadb.PersistentClient(
                path=str(persist_path),
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            logger.info("ChromaDB 客户端创建成功")

            # 列出所有集合，检查是否存在 endgame_memory
            collections = self.client.list_collections()
            logger.info(f"现有集合: {[col.name for col in collections]}")

            # 获取或创建集合
            self.collection = self.client.get_or_create_collection(
                name="endgame_memory",
                metadata={"description": "Endgame OS 长期记忆"}
            )
            logger.info(f"ChromaDB 集合 {self.collection.name} 初始化成功")

            logger.info(f"ChromaDB 初始化完成，存储路径: {self.persist_directory}")
        except Exception as e:
            logger.error(f"ChromaDB 初始化失败: {e}")
            # 打印更详细的错误信息，包括异常类型和栈跟踪
            import traceback
            logger.error(f"异常详情: {traceback.format_exc()}")
            raise

    def add_documents(
        self,
        documents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None
    ) -> bool:
        """
        添加文档到向量存储

        Args:
            documents: 文档内容列表
            metadatas: 文档元数据列表
            ids: 文档 ID 列表

        Returns:
            bool: 是否添加成功
        """
        try:
            if not documents:
                logger.warning("没有文档需要添加")
                return False
            
            logger.info(f"开始添加文档到向量存储，共 {len(documents)} 个文档")

            if ids is None:
                logger.info("生成文档 ID")
                ids = [f"doc_{i}_{hash(doc)}" for i, doc in enumerate(documents)]
            
            # 确保元数据不为空且长度匹配
            if metadatas is None:
                metadatas = [{} for _ in documents]
            elif len(metadatas) != len(documents):
                metadatas = [metadatas[i] if i < len(metadatas) else {} for i in range(len(documents))]
            
            # 最后检查：确保所有元数据都是非空字典
            for i, meta in enumerate(metadatas):
                if not meta or not isinstance(meta, dict):
                    metadatas[i] = {"source": "text"}  # 提供默认元数据
            
            logger.info("调用 ChromaDB add 方法")
            self.collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )

            logger.info(f"成功添加 {len(documents)} 个文档到向量存储")
            return True
        except Exception as e:
            logger.error(f"添加文档失败: {e}")
            # 打印更详细的错误信息，包括异常类型和栈跟踪
            import traceback
            logger.error(f"异常详情: {traceback.format_exc()}")
            return False

    def similarity_search(
        self,
        query: str,
        n_results: int = 5,
        where: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        执行语义相似度搜索

        Args:
            query: 查询文本
            n_results: 返回结果数量
            where: 过滤条件

        Returns:
            List[Dict[str, Any]]: 搜索结果列表
        """
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where
            )

            formatted_results = []
            if results['documents'] and results['documents'][0]:
                for i, doc in enumerate(results['documents'][0]):
                    formatted_results.append({
                        'content': doc,
                        'metadata': results['metadatas'][0][i] if results['metadatas'] else {},
                        'distance': results['distances'][0][i] if results['distances'] else 0,
                        'id': results['ids'][0][i] if results['ids'] else ''
                    })

            logger.info(f"搜索完成，找到 {len(formatted_results)} 个相关结果")
            return formatted_results
        except Exception as e:
            logger.error(f"搜索失败: {e}")
            return []

    def get_stats(self) -> Dict[str, Any]:
        """
        获取向量存储统计信息

        Returns:
            Dict[str, Any]: 统计信息
        """
        try:
            count = self.collection.count()
            return {
                'total_documents': count,
                'collection_name': self.collection.name,
                'persist_directory': self.persist_directory
            }
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return {
                'total_documents': 0,
                'collection_name': 'unknown',
                'persist_directory': self.persist_directory
            }

    def clear_collection(self) -> bool:
        """
        清空集合中的所有文档

        Returns:
            bool: 是否清空成功
        """
        try:
            self.client.delete_collection(name="endgame_memory")
            self.collection = self.client.get_or_create_collection(
                name="endgame_memory",
                metadata={"description": "Endgame OS 长期记忆"}
            )
            logger.info("向量存储已清空")
            return True
        except Exception as e:
            logger.error(f"清空向量存储失败: {e}")
            return False

    def delete_by_ids(self, ids: List[str]) -> bool:
        """
        根据文档 ID 删除文档

        Args:
            ids: 文档 ID 列表

        Returns:
            bool: 是否删除成功
        """
        try:
            self.collection.delete(ids=ids)
            logger.info(f"成功删除 {len(ids)} 个文档")
            return True
        except Exception as e:
            logger.error(f"删除文档失败: {e}")
            return False
