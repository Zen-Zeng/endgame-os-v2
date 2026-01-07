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
from concurrent.futures import ThreadPoolExecutor, as_completed
from .vector_store import VectorStore
from .file_processor import FileProcessor
from .graph_store import GraphStore
from ..neural.processor import NeuralProcessor, create_processor

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
        # 启用真实神经处理，由于 NeuralProcessor 已改为延迟加载，这里不会阻塞启动
        self.neural_processor = create_processor(offline_mode=False)
        logger.info("记忆服务初始化成功（神经处理器已就绪，将在首次使用时加载模型）")

    def clear_all_memories(self):
        """清除所有记忆数据（向量存储和图谱存储）"""
        try:
            logger.info("开始全面清理记忆数据...")
            self.vector_store.clear_all_data()
            self.graph_store.clear_all_data()
            logger.info("记忆数据清理完成")
        except Exception as e:
            logger.error(f"清理记忆数据失败: {e}")
            raise e

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
            
            # 如果是 JSON 文件，尝试作为对话记录进行处理
            if path.suffix.lower() == '.json':
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

    def _ingest_regular_file(self, file_path: str, chunks: List[str], metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理普通文本文件的逻辑，使用并行神经提取和批量图谱写入
        """
        try:
            logger.info(f"开始处理普通文件: {file_path}, 共 {len(chunks)} 个片段")
            
            # 1. 记录日志节点 (作为整个文件的父节点或上下文)
            file_id = f"file_{uuid.uuid4().hex[:8]}"
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            file_content = f"文件: {Path(file_path).name}\n元数据: {json.dumps(metadata, ensure_ascii=False)}"
            
            self.graph_store.add_log(log_id=file_id, content=file_content, timestamp=timestamp, log_type="file_upload")
            
            # 2. 并行处理片段提取实体
            extracted_entities = []
            
            def process_chunk(chunk_text: str, idx: int):
                try:
                    # 为每个片段创建一个子日志节点
                    chunk_id = f"{file_id}_chunk_{idx}"
                    self.graph_store.add_log(log_id=chunk_id, content=chunk_text[:200] + "...", timestamp=timestamp, log_type="file_chunk")
                    
                    # 神经提取
                    neural_result = self.neural_processor.process_text(chunk_text)
                    entities = neural_result.get('entities', [])
                    
                    return chunk_id, entities
                except Exception as e:
                    logger.error(f"处理片段 {idx} 失败: {e}")
                    return None, []

            # 使用分批处理加速，限制并发避免内存溢出
            all_relations = []
            all_concepts_to_add = []
            batch_size = 20
            
            for i in range(0, len(chunks), batch_size):
                batch_chunks = chunks[i:i + batch_size]
                logger.info(f"正在处理文档分块批次: {i//batch_size + 1}/{(len(chunks)-1)//batch_size + 1}")
                
                with ThreadPoolExecutor(max_workers=2) as executor:
                    futures = [executor.submit(process_chunk, chunk, i + j) for j, chunk in enumerate(batch_chunks)]
                    for future in as_completed(futures):
                        chunk_id, entities = future.result()
                        if not chunk_id: continue
                        
                        for entity in entities:
                            if not entity.strip(): continue
                            entity_vector = self.neural_processor.embed_text(entity)
                            if not entity_vector: continue
                            
                            canonical_id, is_new = self._get_or_create_canonical_concept(entity, entity_vector)
                            
                            if is_new:
                                all_concepts_to_add.append({
                                    'id': canonical_id,
                                    'name': entity,
                                    'vector': entity_vector
                                })
                            
                            all_relations.append((chunk_id, canonical_id))
                
                # 及时写入并清理，避免大文件处理时列表过长耗尽内存
                if len(all_concepts_to_add) > 100:
                    self.graph_store.add_concepts_batch(all_concepts_to_add)
                    all_concepts_to_add = []
                
                if len(all_relations) > 300:
                    self.graph_store.add_mentions_batch(all_relations)
                    all_relations = []
            
            # 3. 批量写入图谱
            if all_concepts_to_add:
                self.graph_store.add_concepts_batch(all_concepts_to_add)
            
            if all_relations:
                self.graph_store.add_mentions_batch(all_relations)
            
            return {
                "success": True, 
                "file_path": file_path, 
                "chunks_processed": len(chunks),
                "entities_found": len(all_relations)
            }
        except Exception as e:
            logger.error(f"处理普通文件失败: {e}")
            return {"success": False, "error": str(e)}

    def _ingest_conversation_file(self, file_path: str, chunks: List[str], metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理对话记录文件，使用并行处理和批量写入优化大文件支持
        """
        try:
            logger.info(f"开始高性能处理对话文件: {file_path}")
            conversations = self.file_processor.extract_conversations_with_time(file_path)
            
            if not conversations:
                return {"success": True, "processed_count": 0, "message": "没有找到有效的对话记录"}

            all_concepts_to_add = []
            all_relations = []
            processed_count = 0
            
            def process_single_conv(conv, idx):
                content = conv.get('content', '')
                timestamp = conv.get('create_time', '')
                if not content: return None
                
                log_id = f"conv_{uuid.uuid4().hex[:6]}_{idx}"
                
                # 先同步写入日志节点（KuzuDB 在多线程写入同一表时可能需要更谨慎，但 Log 是主干）
                if self.graph_store.add_log(log_id=log_id, content=content, timestamp=timestamp, log_type="conversation"):
                    # 神经提取实体
                    neural_result = self.neural_processor.process_text(content)
                    entities_data = []
                    
                    for entity in neural_result.get('entities', []):
                        if not entity.strip(): continue
                        entity_vector = self.neural_processor.embed_text(entity)
                        if not entity_vector: continue
                        
                        canonical_id, is_new = self._get_or_create_canonical_concept(entity, entity_vector)
                        entities_data.append({
                            'id': canonical_id,
                            'name': entity,
                            'vector': entity_vector,
                            'is_new': is_new,
                            'log_id': log_id
                        })
                    return entities_data
                return None

            # 限制并发数，避免资源耗尽（对于 MPS 设备，过高并发反而降低性能且易崩溃）
            # 使用更稳健的批量处理方式
            batch_size = 50
            for i in range(0, len(conversations), batch_size):
                batch = conversations[i:i + batch_size]
                logger.info(f"正在处理对话批次: {i//batch_size + 1}/{(len(conversations)-1)//batch_size + 1}")
                
                with ThreadPoolExecutor(max_workers=2) as executor:
                    futures = [executor.submit(process_single_conv, conv, i + j) for j, conv in enumerate(batch)]
                    
                    for future in as_completed(futures):
                        result = future.result()
                        if result:
                            processed_count += 1
                            for item in result:
                                if item['is_new']:
                                    all_concepts_to_add.append({
                                        'id': item['id'],
                                        'name': item['name'],
                                        'vector': item['vector']
                                    })
                                all_relations.append((item['log_id'], item['id']))
                
                # 每处理一批，如果积累了较多概念或关系，先写入一次，释放内存
                if len(all_concepts_to_add) > 200:
                    unique_concepts = {c['id']: c for c in all_concepts_to_add}.values()
                    self.graph_store.add_concepts_batch(list(unique_concepts))
                    all_concepts_to_add = []
                
                if len(all_relations) > 500:
                    self.graph_store.add_mentions_batch(all_relations)
                    all_relations = []

            # 批量写入概念和关系
            if all_concepts_to_add:
                # 去重（不同片段可能发现相同的新概念）
                unique_concepts = {c['id']: c for c in all_concepts_to_add}.values()
                self.graph_store.add_concepts_batch(list(unique_concepts))
            
            if all_relations:
                self.graph_store.add_mentions_batch(all_relations)
            
            logger.info(f"对话文件处理完成: {processed_count} 条记录, {len(all_relations)} 个关联")
            return {"success": True, "processed_count": processed_count, "relations_count": len(all_relations)}
            
        except Exception as e:
            logger.error(f"处理对话文件失败: {e}")
            return {"success": False, "error": str(e)}


# 全局单例
_memory_service_instance = None

def get_memory_service() -> MemoryService:
    """获取记忆服务单例"""
    global _memory_service_instance
    if _memory_service_instance is None:
        _memory_service_instance = MemoryService()
    return _memory_service_instance
