"""
记忆语义合并服务 (Memory Consolidator)
负责识别、仲裁并合并图谱中的语义重复节点。
"""
import logging
import json
import asyncio
from typing import List, Dict, Any, Set
import numpy as np
from sklearn.cluster import AgglomerativeClustering
from app.services.memory.memory_service import get_memory_service
from app.services.neural.processor import get_processor

logger = logging.getLogger(__name__)

class MemoryConsolidator:
    def __init__(self):
        self.memory_service = get_memory_service()
        self.neural_processor = get_processor()
        self.similarity_threshold = 0.85  # 相似度阈值

    async def consolidate_memory(self, user_id: str, progress_callback=None) -> Dict[str, Any]:
        """
        执行全量记忆合并
        1. 获取所有 Concept/Task 节点
        2. 向量聚类
        3. LLM 仲裁
        4. 执行合并
        """
        try:
            if progress_callback: progress_callback(10, "正在扫描全量节点...")
            
            # 1. 获取候选节点
            graph = self.memory_service.graph_store
            concepts = graph.get_nodes_by_type(user_id, "Concept")
            tasks = graph.get_nodes_by_type(user_id, "Task")
            
            # 暂时只处理 Concept，风险较低
            candidate_nodes = concepts
            if not candidate_nodes:
                return {"merged_count": 0, "message": "没有足够的节点进行合并"}

            node_map = {n['id']: n for n in candidate_nodes}
            node_ids = list(node_map.keys())
            
            # 2. 获取向量并聚类
            if progress_callback: progress_callback(30, "正在进行语义聚类分析...")
            
            # 从 VectorStore 或重新计算 Embedding
            names = [n['name'] for n in candidate_nodes]
            logger.info(f"Computing embeddings for {len(names)} nodes...")
            embeddings = self.memory_service.neural_processor.embed_batch(names)
            
            if len(embeddings) < 2:
                return {"merged_count": 0, "message": "节点数量过少，无需合并"}

            logger.info("Embeddings computed. Starting clustering...")
            # 使用层次聚类
            # 1 - cosine_similarity = distance
            # Normalize embeddings first
            normalized_embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)
            
            clustering = AgglomerativeClustering(
                n_clusters=None,
                distance_threshold=1 - self.similarity_threshold,
                metric='cosine',
                linkage='average'
            )
            labels = clustering.fit_predict(normalized_embeddings)
            
            # 分组
            clusters: Dict[int, List[str]] = {}
            for idx, label in enumerate(labels):
                if label not in clusters: clusters[label] = []
                clusters[label].append(node_ids[idx])
            
            # 筛选出数量 > 1 的组
            merge_candidates = [ids for ids in clusters.values() if len(ids) > 1]
            
            logger.info(f"Found {len(merge_candidates)} clusters to analyze.")
            
            if not merge_candidates:
                return {"merged_count": 0, "message": "未发现相似度高的节点群组"}

            if progress_callback: progress_callback(50, f"发现 {len(merge_candidates)} 组相似概念，正在进行智能仲裁...")

            merged_count = 0
            
            # 3. LLM 仲裁与合并
            for group_ids in merge_candidates:
                nodes_in_group = [node_map[nid] for nid in group_ids]
                node_names = [n['name'] for n in nodes_in_group]
                
                logger.info(f"Arbitrating merge for: {node_names}")
                
                # 调用 LLM 判断
                arbitration = await self.neural_processor.arbitrate_merge(node_names)
                
                if arbitration['should_merge']:
                    logger.info(f"Merge approved: {arbitration.get('master_name')}")
                    master_name = arbitration['master_name']
                    # 找到最匹配 master_name 的节点作为主节点，或者新建/指定一个
                    # 简单策略：选择群组中名字最接近 master_name 的，或者第一个
                    master_node_id = group_ids[0]
                    # 如果 LLM 给了新的名字，我们可能需要更新主节点的名字
                    
                    # 执行图谱合并
                    self._merge_graph_nodes(user_id, master_node_id, group_ids[1:], master_name)
                    merged_count += len(group_ids) - 1
                else:
                    logger.info(f"Merge rejected by LLM: {arbitration.get('reason', 'No reason provided')}")
            
            if progress_callback: progress_callback(100, "合并完成")
            
            return {
                "merged_count": merged_count, 
                "groups_analyzed": len(merge_candidates),
                "message": f"成功合并 {merged_count} 个重复节点"
            }

        except Exception as e:
            logger.error(f"Consolidation Failed: {e}")
            raise e

    def _merge_graph_nodes(self, user_id: str, master_id: str, slave_ids: List[str], new_master_name: str = None):
        """
        物理合并节点：
        1. 将 Slave 的边重定向到 Master
        2. 合并 Slave 的属性 (Dossier) 到 Master
        3. 删除 Slave
        4. 更新 Master 名字 (可选)
        """
        graph = self.memory_service.graph_store
        with graph._lock, graph._get_conn() as conn:
            # 1. 属性合并
            master_row = conn.execute("SELECT attributes, content FROM nodes WHERE id=?", (master_id,)).fetchone()
            if not master_row: return
            
            master_attrs = json.loads(master_row['attributes']) if master_row['attributes'] else {}
            master_dossier = master_attrs.get('dossier', {})
            
            for sid in slave_ids:
                slave_row = conn.execute("SELECT attributes FROM nodes WHERE id=?", (sid,)).fetchone()
                if slave_row and slave_row['attributes']:
                    slave_attrs = json.loads(slave_row['attributes'])
                    slave_dossier = slave_attrs.get('dossier', {})
                    # 深度合并 Dossier
                    for k, v in slave_dossier.items():
                        if k not in master_dossier:
                            master_dossier[k] = v
                        elif isinstance(master_dossier[k], list) and isinstance(v, list):
                            master_dossier[k] = list(set(master_dossier[k] + v))
            
            master_attrs['dossier'] = master_dossier
            
            # 更新主节点
            update_sql = "UPDATE nodes SET attributes = ?"
            params = [json.dumps(master_attrs, ensure_ascii=False)]
            
            if new_master_name:
                update_sql += ", name = ?"
                params.append(new_master_name)
            
            update_sql += " WHERE id = ?"
            params.append(master_id)
            
            conn.execute(update_sql, params)
            
            # 2. 边重定向 (Incoming & Outgoing)
            # 处理重复边：如果重定向后导致重复 (A->Master 和 A->Slave 变成两个 A->Master)，SQLite IGNORE 会忽略
            # 但我们需要先 DELETE 冲突的，或者让应用层逻辑处理。简单起见，使用 UPDATE OR IGNORE
            
            for sid in slave_ids:
                # Redirect Incoming: X -> Slave  =>  X -> Master
                try:
                    conn.execute("UPDATE OR IGNORE edges SET target = ? WHERE target = ?", (master_id, sid))
                except: pass # 忽略主键冲突
                
                # Redirect Outgoing: Slave -> Y  =>  Master -> Y
                try:
                    conn.execute("UPDATE OR IGNORE edges SET source = ? WHERE source = ?", (master_id, sid))
                except: pass
                
                # 删除 Slave 节点 (级联删除剩余的边 - 如果没有定义级联，需手动删)
                conn.execute("DELETE FROM edges WHERE source = ? OR target = ?", (sid, sid))
                conn.execute("DELETE FROM nodes WHERE id = ?", (sid,))
                
            logger.info(f"Merged {slave_ids} into {master_id} ('{new_master_name}')")

