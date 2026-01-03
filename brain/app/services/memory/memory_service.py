"""
统一记忆服务
整合向量存储、图数据库和神经处理功能
"""
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import logging
import json
import uuid
from datetime import datetime
from .vector_store import VectorStore
from .file_processor import FileProcessor
from .graph_store import GraphStore
from ..neural.processor import NeuralProcessor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MemoryService:
    """
    记忆服务类
    统一管理文件解析、神经处理、向量化和图谱存储
    """

    def __init__(
        self,
        persist_directory: str = "./data/chroma",
        graph_db_path: str = "./data/kuzu_db",
        chunk_size: int = 1000,
        chunk_overlap: int = 200
    ):
        """
        初始化记忆服务

        Args:
            persist_directory: 向量存储持久化目录
            graph_db_path: 图数据库存储路径
            chunk_size: 文本切分大小
            chunk_overlap: 文本切分重叠大小
        """
        self.vector_store = VectorStore(persist_directory=persist_directory)
        self.graph_store = GraphStore(db_path=graph_db_path)
        self.file_processor = FileProcessor(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        self.neural_processor = NeuralProcessor()
        logger.info("记忆服务初始化成功")

    def _get_or_create_canonical_concept(self, entity_name: str, entity_vector: List[float]) -> Tuple[str, bool]:
        """
        获取或创建规范概念，实现实体对齐逻辑
        
        Args:
            entity_name: 实体名称
            entity_vector: 实体向量
            
        Returns:
            Tuple[str, bool]: (canonical_concept_id, 是否是新创建的概念)
        """
        try:
            # 在概念索引中查找相似概念
            similar_concept = self.vector_store.find_similar_concept(entity_vector, threshold=0.85)
            
            if similar_concept:
                # 找到相似概念，返回已存在的规范概念ID
                logger.info(f"找到相似概念: {entity_name} -> {similar_concept['name']} (相似度: {1 - similar_concept['distance']:.3f})")
                return similar_concept['id'], False
            else:
                # 创建新概念
                concept_id = f"concept_{uuid.uuid4().hex[:8]}"
                success = self.vector_store.add_concept(concept_id, entity_name, entity_vector)
                
                if success:
                    logger.info(f"创建新概念: {entity_name} -> {concept_id}")
                    return concept_id, True
                else:
                    # 如果添加失败，使用备选ID生成策略
                    concept_id = f"concept_{hash(entity_name)}"
                    logger.warning(f"使用备选ID: {entity_name} -> {concept_id}")
                    return concept_id, True
                    
        except Exception as e:
            logger.error(f"获取或创建规范概念失败: {entity_name}, {e}")
            # 错误情况下返回基于名称的ID
            concept_id = f"concept_{hash(entity_name)}"
            return concept_id, True

    def ingest_file(self, file_path: str) -> Dict[str, Any]:
        """
        处理单个文件并添加到记忆

        Args:
            file_path: 文件路径

        Returns:
            Dict[str, Any]: 处理结果
        """
        try:
            path = Path(file_path)
            
            if not path.exists():
                return {
                    'success': False,
                    'error': f'文件不存在: {file_path}',
                    'file_path': file_path
                }

            logger.info(f"开始处理文件: {file_path}")

            # 解析文件内容
            chunks = self.file_processor.parse_file(file_path)
            
            if not chunks:
                return {
                    'success': False,
                    'error': '文件解析失败或内容为空',
                    'file_path': file_path
                }

            # 获取文件元数据
            metadata = self.file_processor.get_file_metadata(file_path)
            
            # 如果是对话记录文件，进行特殊处理
            if path.suffix.lower() == '.json' and 'conversation' in path.name.lower():
                return self._ingest_conversation_file(file_path, chunks, metadata)
            
            # 处理普通文件
            return self._ingest_regular_file(file_path, chunks, metadata)

        except Exception as e:
            logger.error(f"处理文件失败 {file_path}: {e}")
            return {
                'success': False,
                'error': str(e),
                'file_path': file_path
            }

    def _ingest_conversation_file(self, file_path: str, chunks: List[str], metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理对话记录文件，构建时间轴记忆图谱

        Args:
            file_path: 文件路径
            chunks: 文本块
            metadata: 文件元数据

        Returns:
            Dict[str, Any]: 处理结果
        """
        try:
            logger.info(f"开始处理对话文件: {file_path}")
            
            # 提取对话记录
            conversations = self.file_processor.extract_conversations_with_time(file_path)
            
            # 处理每条对话记录
            processed_count = 0
            for conv in conversations:
                try:
                    # 创建日志节点（核心时间节点）
                    log_id = f"conv_{processed_count}_{hash(conv.get('content', ''))}"
                    content = conv.get('content', '')
                    timestamp = conv.get('create_time', '')
                    
                    if not content:
                        continue
                    
                    # 添加日志节点
                    if not self.graph_store.add_log(
                        log_id=log_id,
                        content=content,
                        timestamp=timestamp,
                        log_type="conversation"
                    ):
                        logger.error(f"添加日志节点失败: {log_id}")
                        continue
                    
                    # 神经处理内容
                    neural_result = self.neural_processor.process_text(content)
                    
                    # 添加概念节点和提及关系（使用实体对齐）
                    for entity in neural_result.get('entities', []):
                        if not entity.strip():  # 跳过空实体
                            continue
                        
                        # 为每个实体生成向量用于实体对齐
                        entity_vector = self.neural_processor.embed_text(entity)
                        if not entity_vector:  # 如果向量化失败，跳过该实体
                            logger.warning(f"实体向量化失败: {entity}")
                            continue
                        
                        # 使用实体对齐逻辑获取或创建规范概念
                        canonical_concept_id, is_new = self._get_or_create_canonical_concept(entity, entity_vector)
                        
                        if self.graph_store.add_concept(
                            concept_id=canonical_concept_id,
                            name=entity,
                            vector=entity_vector
                        ):
                            # 建立日志-概念关系
                            if not self.graph_store.add_mentions_relation(
                                log_id=log_id,
                                concept_id=canonical_concept_id
                            ):
                                logger.error(f"添加提及关系失败: {log_id} -> {canonical_concept_id}")
                        else:
                            logger.error(f"添加概念节点失败: {canonical_concept_id}")
                    
                    # 添加三元组关系
                    for subject, relation, obj in neural_result.get('triplets', []):
                        # 根据关系类型创建不同的节点和关系
                        if relation in ["完成", "贡献于"]:
                            # 创建项目节点
                            project_id = f"project_{obj}_{processed_count}"
                            if self.graph_store.add_project(
                                project_id=project_id,
                                name=obj
                            ):
                                # 建立日志-项目关系
                                if not self.graph_store.add_contributes_to_relation(
                                    log_id=log_id,
                                    project_id=project_id
                                ):
                                    logger.error(f"添加贡献关系失败: {log_id} -> {project_id}")
                            else:
                                logger.error(f"添加项目节点失败: {project_id}")
                    
                        elif relation in ["属于", "关于"]:
                            # 创建目标节点
                            goal_id = f"goal_{obj}_{processed_count}"
                            if self.graph_store.add_goal(
                                goal_id=goal_id,
                                title=obj
                            ):
                                # 建立项目-目标关系
                                project_id = f"project_{subject}_{processed_count}"
                                if self.graph_store.add_project(
                                    project_id=project_id,
                                    name=subject
                                ):
                                    if not self.graph_store.add_belongs_to_relation(
                                        project_id=project_id,
                                        goal_id=goal_id
                                    ):
                                        logger.error(f"添加属于关系失败: {project_id} -> {goal_id}")
                                else:
                                    logger.error(f"添加项目节点失败: {project_id}")
                            else:
                                logger.error(f"添加目标节点失败: {goal_id}")
                
                    processed_count += 1
                
                except Exception as e:
                    logger.error(f"处理对话记录失败: {e}")
                    continue
            
            # 同时向向量存储添加内容（用于模糊检索）
            path = Path(file_path)
            metadatas = [metadata for _ in chunks]
            ids = [f"{path.stem}_{i}" for i in range(len(chunks))]

            vector_success = self.vector_store.add_documents(
                documents=chunks,
                metadatas=metadatas,
                ids=ids
            )

            if vector_success:
                logger.info(f"对话文件处理成功: {file_path}, 处理 {processed_count} 条记录")
                return {
                    'success': True,
                    'file_path': file_path,
                    'conversations_processed': processed_count,
                    'chunks_added': len(chunks),
                    'metadata': metadata
                }
            else:
                return {
                    'success': False,
                    'error': '添加到向量存储失败',
                    'file_path': file_path
                }

        except Exception as e:
            logger.error(f"处理对话文件失败 {file_path}: {e}")
            return {
                'success': False,
                'error': str(e),
                'file_path': file_path
            }

    def _ingest_regular_file(self, file_path: str, chunks: List[str], metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理普通文件

        Args:
            file_path: 文件路径
            chunks: 文本块
            metadata: 文件元数据

        Returns:
            Dict[str, Any]: 处理结果
        """
        try:
            # 添加到向量存储
            metadatas = [metadata for _ in chunks]
            ids = [f"{Path(file_path).stem}_{i}" for i in range(len(chunks))]

            success = self.vector_store.add_documents(
                documents=chunks,
                metadatas=metadatas,
                ids=ids
            )

            if success:
                logger.info(f"文件处理成功: {file_path}, 添加 {len(chunks)} 个片段")
                return {
                    'success': True,
                    'file_path': file_path,
                    'chunks_added': len(chunks),
                    'metadata': metadata
                }
            else:
                return {
                    'success': False,
                    'error': '添加到向量存储失败',
                    'file_path': file_path
                }

        except Exception as e:
            logger.error(f"处理文件失败 {file_path}: {e}")
            return {
                'success': False,
                'error': str(e),
                'file_path': file_path
            }

    def ingest_files(self, file_paths: List[str]) -> Dict[str, Any]:
        """
        批量处理文件并添加到记忆

        Args:
            file_paths: 文件路径列表

        Returns:
            Dict[str, Any]: 批量处理结果
        """
        results = {
            'total': len(file_paths),
            'success': 0,
            'failed': 0,
            'details': []
        }

        for file_path in file_paths:
            result = self.ingest_file(file_path)
            results['details'].append(result)
            
            if result['success']:
                results['success'] += 1
            else:
                results['failed'] += 1

        logger.info(f"批量处理完成: 成功 {results['success']}, 失败 {results['failed']}")
        return results

    def ingest_text(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        直接添加文本到记忆

        Args:
            text: 文本内容
            metadata: 元数据

        Returns:
            Dict[str, Any]: 处理结果
        """
        try:
            if not text or not text.strip():
                return {
                    'success': False,
                    'error': '文本内容为空'
                }

            # 神经处理文本
            neural_result = self.neural_processor.process_text(text)
            
            # 创建日志节点
            log_id = f"text_{hash(text)}"
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            if not self.graph_store.add_log(
                log_id=log_id,
                content=text,
                timestamp=timestamp,
                log_type="manual"
            ):
                logger.error(f"添加日志节点失败: {log_id}")
                return {
                    'success': False,
                    'error': '添加日志节点失败'
                }
            
            # 添加概念节点和提及关系（使用实体对齐）
            for entity in neural_result.get('entities', []):
                if not entity.strip():  # 跳过空实体
                    continue
                    
                # 为每个实体生成向量用于实体对齐
                entity_vector = self.neural_processor.embed_text(entity)
                if not entity_vector:  # 如果向量化失败，跳过该实体
                    logger.warning(f"实体向量化失败: {entity}")
                    continue
                    
                # 使用实体对齐逻辑获取或创建规范概念
                canonical_concept_id, is_new = self._get_or_create_canonical_concept(entity, entity_vector)
                
                if self.graph_store.add_concept(
                    concept_id=canonical_concept_id,
                    name=entity,
                    vector=entity_vector
                ):
                    # 建立日志-概念关系
                    if not self.graph_store.add_mentions_relation(
                        log_id=log_id,
                        concept_id=canonical_concept_id
                    ):
                        logger.error(f"添加提及关系失败: {log_id} -> {canonical_concept_id}")
                else:
                    logger.error(f"添加概念节点失败: {canonical_concept_id}")
            
            # 添加三元组关系
            for subject, relation, obj in neural_result.get('triplets', []):
                # 根据关系类型创建不同的节点和关系
                if relation in ["完成", "贡献于"]:
                    # 创建项目节点
                    project_id = f"project_{obj}_{hash(text)}"
                    if self.graph_store.add_project(
                        project_id=project_id,
                        name=obj
                    ):
                        # 建立日志-项目关系
                        if not self.graph_store.add_contributes_to_relation(
                            log_id=log_id,
                            project_id=project_id
                        ):
                            logger.error(f"添加贡献关系失败: {log_id} -> {project_id}")
                    else:
                        logger.error(f"添加项目节点失败: {project_id}")
                
                elif relation in ["属于", "关于"]:
                    # 创建目标节点
                    goal_id = f"goal_{obj}_{hash(text)}"
                    if self.graph_store.add_goal(
                        goal_id=goal_id,
                        title=obj
                    ):
                        # 建立项目-目标关系
                        project_id = f"project_{subject}_{hash(text)}"
                        if self.graph_store.add_project(
                            project_id=project_id,
                            name=subject
                        ):
                            if not self.graph_store.add_belongs_to_relation(
                                project_id=project_id,
                                goal_id=goal_id
                            ):
                                logger.error(f"添加属于关系失败: {project_id} -> {goal_id}")
                        else:
                            logger.error(f"添加项目节点失败: {project_id}")
                    else:
                        logger.error(f"添加目标节点失败: {goal_id}")
            
            # 同时向向量存储添加内容（用于模糊检索）
            chunks = self.file_processor._chunk_text(text)
            metadatas = [metadata or {} for _ in chunks]
            ids = [f"text_{i}_{hash(chunk)}" for i, chunk in enumerate(chunks)]

            vector_success = self.vector_store.add_documents(
                documents=chunks,
                metadatas=metadatas,
                ids=ids
            )

            if vector_success:
                logger.info(f"文本添加成功: {len(chunks)} 个片段")
                return {
                    'success': True,
                    'chunks_added': len(chunks),
                    'entities_processed': len(neural_result.get('entities', [])),
                    'triplets_processed': len(neural_result.get('triplets', []))
                }
            else:
                return {
                    'success': False,
                    'error': '添加到向量存储失败'
                }

        except Exception as e:
            logger.error(f"添加文本失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def query_memory(
        self,
        query: str,
        n_results: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        查询记忆

        Args:
            query: 查询文本
            n_results: 返回结果数量
            filter_metadata: 元数据过滤条件

        Returns:
            List[Dict[str, Any]]: 查询结果列表
        """
        try:
            logger.info(f"查询记忆: {query}")
            
            # 向量搜索（模糊检索）
            vector_results = self.vector_store.similarity_search(
                query=query,
                n_results=n_results,
                where=filter_metadata
            )
            
            # 图谱查询（结构化检索）
            graph_results = self._query_graph(query)
            
            # 合并结果，优先返回图谱结果
            all_results = graph_results + vector_results
            
            # 去重并限制结果数量
            unique_results = []
            seen_content = set()
            
            for result in all_results:
                content = result.get('content', '')
                if content and content not in seen_content:
                    seen_content.add(content)
                    unique_results.append(result)
                    
                    if len(unique_results) >= n_results:
                        break
            
            logger.info(f"搜索完成，找到 {len(unique_results)} 个相关结果")
            return unique_results
        except Exception as e:
            logger.error(f"查询记忆失败: {e}")
            return []

    def _query_graph(self, query: str) -> List[Dict[str, Any]]:
        """
        查询图数据库，结合时间轴和实体关系

        Args:
            query: 查询文本

        Returns:
            List[Dict[str, Any]]: 查询结果列表
        """
        try:
            results = []
            
            # 1. 提取查询中的实体（概念）
            neural_result = self.neural_processor.process_text(query)
            entities = neural_result.get('entities', [])
            
            # 2. 按概念查询
            for entity in entities:
                concept_results = self.graph_store.query_by_concept(entity)
                for res in concept_results:
                    log = res.get('l', {})
                    project = res.get('p', {})
                    concept = res.get('c', {})
                    
                    if log:
                        results.append({
                            'content': log.get('content', ''),
                            'type': 'graph_concept_match',
                            'timestamp': str(log.get('timestamp', '')),
                            'metadata': {
                                'concept': concept.get('name', ''),
                                'project': project.get('name', '') if project else None
                            }
                        })
            
            # 3. 如果结果不足，按时间范围进行关键词匹配
            if len(results) < 5:
                # 查询最近的日志
                recent_logs = self.graph_store.query_by_time_range(
                    start_time="2025-01-01 00:00:00",
                    end_time="2026-12-31 23:59:59"
                )
                
                for log in recent_logs:
                    content = log.get('content', '')
                    if query.lower() in content.lower():
                        # 避免重复
                        if not any(r['content'] == content for r in results):
                            results.append({
                                'content': content,
                                'type': 'graph_keyword_match',
                                'timestamp': str(log.get('timestamp', '')),
                                'metadata': {'id': log.get('id', '')}
                            })
                    
                    if len(results) >= 10:
                        break
            
            return results
        except Exception as e:
            logger.error(f"图谱查询失败: {e}")
            return []

    def get_stats(self) -> Dict[str, Any]:
        """
        获取记忆统计信息

        Returns:
            Dict[str, Any]: 统计信息
        """
        try:
            # 向量存储统计
            vector_stats = self.vector_store.get_stats()
            
            # 图数据库统计
            graph_stats = self.graph_store.get_stats()
            
            return {
                'vector_store': vector_stats,
                'graph_store': graph_stats
            }
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return {
                'error': str(e)
            }

    def clear_memory(self) -> Dict[str, Any]:
        """
        清空所有记忆

        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            # 清空向量存储
            vector_success = self.vector_store.clear_collection()
            
            # 清空图数据库
            graph_success = self._clear_graph_database()
            
            if vector_success and graph_success:
                logger.info("记忆已清空，包括向量存储和图数据库")
                return {
                    'success': True,
                    'message': '记忆已清空，包括向量存储和图数据库'
                }
            else:
                return {
                    'success': False,
                    'error': '清空记忆失败'
                }
        except Exception as e:
            logger.error(f"清空记忆失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def _clear_graph_database(self) -> bool:
        """
        清空图数据库
        
        Returns:
            bool: 是否清空成功
        """
        try:
            # 删除所有节点表数据（保留表结构）
            # 使用DETACH DELETE来删除有关系的节点
            node_tables = ["User", "Goal", "Project", "Task", "Log", "Concept"]
            for table in node_tables:
                try:
                    self.graph_store.conn.execute(f"MATCH (n:{table}) DETACH DELETE n")
                    logger.info(f"已清空 {table} 节点表")
                except Exception as e:
                    logger.warning(f"清空 {table} 节点表失败: {e}")
            
            return True
        except Exception as e:
            logger.error(f"清空图数据库失败: {e}")
            return False

    def delete_by_file(self, file_path: str) -> Dict[str, Any]:
        """
        删除指定文件的所有记忆

        Args:
            file_path: 文件路径

        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            path = Path(file_path)
            prefix = path.stem
            
            # 从向量存储删除
            stats = self.get_stats()
            vector_stats = stats.get('vector_store', {})
            if 'total_documents' in vector_stats and vector_stats['total_documents'] > 0:
                all_results = self.vector_store.collection.get()
                
                ids_to_delete = []
                for doc_id in all_results['ids']:
                    if doc_id.startswith(prefix):
                        ids_to_delete.append(doc_id)
                
                if ids_to_delete:
                    vector_success = self.vector_store.delete_by_ids(ids_to_delete)
                    if not vector_success:
                        logger.error(f"从向量存储删除失败")
            
            # 从图数据库删除（简化实现）
            # 实际应用中需要更复杂的删除逻辑
            graph_success = True  # 简化实现
            
            if vector_success and graph_success:
                logger.info(f"已删除文件 {file_path} 的相关记忆")
                return {
                    'success': True,
                    'deleted_count': len(ids_to_delete) if 'ids_to_delete' in locals() else 0,
                    'file_path': file_path
                }
            
            return {
                'success': False,
                'error': '未找到相关记忆',
                'file_path': file_path
            }
        except Exception as e:
            logger.error(f"删除记忆失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'file_path': file_path
            }
