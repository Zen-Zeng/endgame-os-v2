"""
KuzuDB 图数据库封装
用于存储 Endgame OS 的神经记忆图谱
"""
import kuzu
import logging
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GraphStore:
    """
    KuzuDB 图数据库类
    提供节点和关系的创建、查询和管理功能
    """

    def __init__(self, db_path: str = "./data/kuzu"):
        """
        初始化 KuzuDB 数据库

        Args:
            db_path: 数据库存储路径
        """
        self.db_path = db_path
        self.db = None
        self._initialize_db()

    def _initialize_db(self):
        """
        初始化数据库连接并创建 Schema
        """
        try:
            # 确保数据目录存在
            from pathlib import Path
            db_dir = Path(self.db_path).parent
            db_dir.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"KuzuDB 存储路径: {self.db_path}")

            # 创建数据库连接
            self.db = kuzu.Database(self.db_path)
            
            # 创建连接
            self.conn = kuzu.Connection(self.db)
            logger.info("KuzuDB 连接创建成功")

            # 初始化 Schema
            self._create_schema()
            logger.info("KuzuDB Schema 初始化完成")

        except Exception as e:
            logger.error(f"KuzuDB 初始化失败: {e}")
            raise

    def _create_schema(self):
        """
        创建图数据库 Schema
        根据技术架构规范定义节点和关系
        """
        try:
            # 节点定义 (Nodes)
            self.conn.execute("CREATE NODE TABLE IF NOT EXISTS User (name STRING, vision STRING, PRIMARY KEY (name))")
            self.conn.execute("CREATE NODE TABLE IF NOT EXISTS Goal (id STRING, title STRING, deadline DATE, status STRING, PRIMARY KEY (id))")
            self.conn.execute("CREATE NODE TABLE IF NOT EXISTS Project (id STRING, name STRING, sector STRING, PRIMARY KEY (id))")
            self.conn.execute("CREATE NODE TABLE IF NOT EXISTS Task (id STRING, title STRING, status STRING, PRIMARY KEY (id))")
            self.conn.execute("CREATE NODE TABLE IF NOT EXISTS Log (id STRING, content STRING, timestamp TIMESTAMP, type STRING, PRIMARY KEY (id))")
            self.conn.execute("CREATE NODE TABLE IF NOT EXISTS Concept (id STRING, name STRING, vector FLOAT[768], PRIMARY KEY (id))")

            # 关系定义 (Edges)
            self.conn.execute("CREATE REL TABLE IF NOT EXISTS HAS_GOAL (FROM User TO Goal)")
            self.conn.execute("CREATE REL TABLE IF NOT EXISTS BELONGS_TO (FROM Project TO Goal)")
            self.conn.execute("CREATE REL TABLE IF NOT EXISTS BLOCKED_BY (FROM Task TO Task)")
            self.conn.execute("CREATE REL TABLE IF NOT EXISTS CONTRIBUTES_TO (FROM Log TO Project)")
            self.conn.execute("CREATE REL TABLE IF NOT EXISTS MENTIONS (FROM Log TO Concept)")

            logger.info("Schema 创建完成")
        except Exception as e:
            logger.error(f"Schema 创建失败: {e}")
            raise

    def add_user(self, name: str, vision: str) -> bool:
        """
        添加用户节点

        Args:
            name: 用户名
            vision: 用户愿景

        Returns:
            bool: 是否添加成功
        """
        try:
            query = f"CREATE (u:User {{name: '{name}', vision: '{vision}'}})"
            self.conn.execute(query)
            return True
        except Exception as e:
            logger.error(f"添加用户节点失败: {e}")
            return False

    def add_goal(self, goal_id: str, title: str, deadline: str = None, status: str = "active") -> bool:
        """
        添加目标节点

        Args:
            goal_id: 目标ID
            title: 目标标题
            deadline: 截止日期
            status: 目标状态

        Returns:
            bool: 是否添加成功
        """
        try:
            deadline_str = f"'{deadline}'" if deadline else "NULL"
            query = f"CREATE (g:Goal {{id: '{goal_id}', title: '{title}', deadline: {deadline_str}, status: '{status}'}})"
            self.conn.execute(query)
            return True
        except Exception as e:
            logger.error(f"添加目标节点失败: {e}")
            return False

    def add_project(self, project_id: str, name: str, sector: str = None) -> bool:
        """
        添加项目节点

        Args:
            project_id: 项目ID
            name: 项目名称
            sector: 项目领域

        Returns:
            bool: 是否添加成功
        """
        try:
            sector_str = f"'{sector}'" if sector else "NULL"
            query = f"CREATE (p:Project {{id: '{project_id}', name: '{name}', sector: {sector_str}}})"
            self.conn.execute(query)
            return True
        except Exception as e:
            logger.error(f"添加项目节点失败: {e}")
            return False

    def add_task(self, task_id: str, title: str, status: str = "pending") -> bool:
        """
        添加任务节点

        Args:
            task_id: 任务ID
            title: 任务标题
            status: 任务状态

        Returns:
            bool: 是否添加成功
        """
        try:
            query = f"CREATE (t:Task {{id: '{task_id}', title: '{title}', status: '{status}'}})"
            self.conn.execute(query)
            return True
        except Exception as e:
            logger.error(f"添加任务节点失败: {e}")
            return False

    def add_log(self, log_id: str, content: str, timestamp: str, log_type: str = "chat") -> bool:
        """
        添加日志节点（核心时间节点）

        Args:
            log_id: 日志ID
            content: 日志内容
            timestamp: 时间戳
            log_type: 日志类型

        Returns:
            bool: 是否添加成功
        """
        try:
            query = f"CREATE (l:Log {{id: '{log_id}', content: '{content}', timestamp: TIMESTAMP('{timestamp}'), type: '{log_type}'}})"
            self.conn.execute(query)
            return True
        except Exception as e:
            logger.error(f"添加日志节点失败: {e}")
            return False

    def add_concept(self, concept_id: str, name: str, vector: List[float] = None) -> bool:
        """
        添加概念节点（实体节点）

        Args:
            concept_id: 概念ID
            name: 概念名称
            vector: 向量表示

        Returns:
            bool: 是否添加成功
        """
        try:
            if vector:
                vector_str = str(vector).replace('[', '').replace(']', '')
                query = f"CREATE (c:Concept {{id: '{concept_id}', name: '{name}', vector: [{vector_str}]}})"
            else:
                query = f"CREATE (c:Concept {{id: '{concept_id}', name: '{name}'}})"
            
            self.conn.execute(query)
            return True
        except Exception as e:
            logger.error(f"添加概念节点失败: {e}")
            return False

    def add_has_goal_relation(self, user_name: str, goal_id: str) -> bool:
        """
        添加用户-目标关系

        Args:
            user_name: 用户名
            goal_id: 目标ID

        Returns:
            bool: 是否添加成功
        """
        try:
            query = f"MATCH (u:User {{name: '{user_name}'}}), (g:Goal {{id: '{goal_id}'}}) CREATE (u)-[:HAS_GOAL]->(g)"
            self.conn.execute(query)
            return True
        except Exception as e:
            logger.error(f"添加HAS_GOAL关系失败: {e}")
            return False

    def add_belongs_to_relation(self, project_id: str, goal_id: str) -> bool:
        """
        添加项目-目标关系

        Args:
            project_id: 项目ID
            goal_id: 目标ID

        Returns:
            bool: 是否添加成功
        """
        try:
            query = f"MATCH (p:Project {{id: '{project_id}'}}), (g:Goal {{id: '{goal_id}'}}) CREATE (p)-[:BELONGS_TO]->(g)"
            self.conn.execute(query)
            return True
        except Exception as e:
            logger.error(f"添加BELONGS_TO关系失败: {e}")
            return False

    def add_blocked_by_relation(self, task_id_1: str, task_id_2: str) -> bool:
        """
        添加任务-任务阻塞关系

        Args:
            task_id_1: 任务ID1
            task_id_2: 任务ID2

        Returns:
            bool: 是否添加成功
        """
        try:
            query = f"MATCH (t1:Task {{id: '{task_id_1}'}}), (t2:Task {{id: '{task_id_2}'}}) CREATE (t1)-[:BLOCKED_BY]->(t2)"
            self.conn.execute(query)
            return True
        except Exception as e:
            logger.error(f"添加BLOCKED_BY关系失败: {e}")
            return False

    def add_contributes_to_relation(self, log_id: str, project_id: str) -> bool:
        """
        添加日志-项目贡献关系

        Args:
            log_id: 日志ID
            project_id: 项目ID

        Returns:
            bool: 是否添加成功
        """
        try:
            query = f"MATCH (l:Log {{id: '{log_id}'}}), (p:Project {{id: '{project_id}'}}) CREATE (l)-[:CONTRIBUTES_TO]->(p)"
            self.conn.execute(query)
            return True
        except Exception as e:
            logger.error(f"添加CONTRIBUTES_TO关系失败: {e}")
            return False

    def add_mentions_relation(self, log_id: str, concept_id: str) -> bool:
        """
        添加日志-概念提及关系

        Args:
            log_id: 日志ID
            concept_id: 概念ID

        Returns:
            bool: 是否添加成功
        """
        try:
            query = f"MATCH (l:Log {{id: '{log_id}'}}), (c:Concept {{id: '{concept_id}'}}) CREATE (l)-[:MENTIONS]->(c)"
            self.conn.execute(query)
            return True
        except Exception as e:
            logger.error(f"添加MENTIONS关系失败: {e}")
            return False

    def query_by_time_range(self, start_time: str, end_time: str) -> List[Dict[str, Any]]:
        """
        按时间范围查询日志

        Args:
            start_time: 开始时间
            end_time: 结束时间

        Returns:
            List[Dict[str, Any]]: 查询结果
        """
        try:
            query = f"MATCH (l:Log) WHERE l.timestamp >= TIMESTAMP('{start_time}') AND l.timestamp <= TIMESTAMP('{end_time}') RETURN l ORDER BY l.timestamp DESC"
            result = self.conn.execute(query)
            if result:
                return result.get_as_arrow().to_pylist()
            return []
        except Exception as e:
            logger.error(f"时间范围查询失败: {e}")
            return []

    def query_related_concepts(self, log_id: str) -> List[Dict[str, Any]]:
        """
        查询日志相关的概念

        Args:
            log_id: 日志ID

        Returns:
            List[Dict[str, Any]]: 相关概念列表
        """
        try:
            query = f"MATCH (l:Log {{id: '{log_id}'}})-[:MENTIONS]->(c:Concept) RETURN c"
            result = self.conn.execute(query)
            if result:
                return result.get_as_arrow().to_pylist()
            return []
        except Exception as e:
            logger.error(f"查询相关概念失败: {e}")
            return []

    def get_stats(self) -> Dict[str, Any]:
        """
        获取图数据库统计信息

        Returns:
            Dict[str, Any]: 统计信息
        """
        try:
            stats = {}
            
            # 节点统计
            node_counts = {}
            for node_type in ["User", "Goal", "Project", "Task", "Log", "Concept"]:
                try:
                    count_result = self.conn.execute(f"MATCH (n:{node_type}) RETURN count(n) AS count")
                    result_list = count_result.get_as_arrow().to_pylist()
                    if result_list:
                        node_counts[node_type] = result_list[0]["count"]
                    else:
                        node_counts[node_type] = 0
                except Exception as e:
                    logger.error(f"查询 {node_type} 节点数量失败: {e}")
                    node_counts[node_type] = 0
            
            stats["node_counts"] = node_counts
            
            # 关系统计
            rel_counts = {}
            for rel_type in ["HAS_GOAL", "BELONGS_TO", "BLOCKED_BY", "CONTRIBUTES_TO", "MENTIONS"]:
                try:
                    count_result = self.conn.execute(f"MATCH ()-[:{rel_type}]->() RETURN count(*) AS count")
                    result_list = count_result.get_as_arrow().to_pylist()
                    if result_list:
                        rel_counts[rel_type] = result_list[0]["count"]
                    else:
                        rel_counts[rel_type] = 0
                except Exception as e:
                    logger.error(f"查询 {rel_type} 关系数量失败: {e}")
                    rel_counts[rel_type] = 0
            
            stats["relation_counts"] = rel_counts
            stats["db_path"] = self.db_path
            
            return stats
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return {"error": str(e)}

    def query_by_concept(self, concept_name: str) -> List[Dict[str, Any]]:
        """
        按概念名称查询相关的日志和项目

        Args:
            concept_name: 概念名称

        Returns:
            List[Dict[str, Any]]: 相关结果列表
        """
        try:
            query = f"MATCH (c:Concept {{name: '{concept_name}'}})<-[:MENTIONS]-(l:Log) OPTIONAL MATCH (l)-[:CONTRIBUTES_TO]->(p:Project) RETURN l, p, c"
            result = self.conn.execute(query)
            return result.get_as_arrow().to_pylist()
        except Exception as e:
            logger.error(f"按概念查询失败: {e}")
            return []

    def deep_graph_inference(self, concept_name: str, max_depth: int = 3) -> List[Dict[str, Any]]:
        """
        深度图谱推理查询，支持多跳关系查询
        
        Args:
            concept_name: 起始概念名称
            max_depth: 最大查询深度
            
        Returns:
            List[Dict[str, Any]]: 推理结果列表
        """
        try:
            results = []
            
            # 第一层：直接提及该概念的日志
            direct_query = f"""
            MATCH (c:Concept {{name: '{concept_name}'}})<-[:MENTIONS]-(l:Log)
            RETURN l.content, l.timestamp, '{concept_name}' as source_concept, 'direct_mention' as relation_type
            ORDER BY l.timestamp DESC
            LIMIT 20
            """
            direct_result = self.conn.execute(direct_query)
            if direct_result:
                result_list = direct_result.get_as_arrow().to_pylist()
                for row in result_list:
                    results.append({
                        "content": row.get("l.content", ""),
                        "timestamp": str(row.get("l.timestamp", "")),
                        "related_concept": row.get("source_concept", ""),
                        "relation_type": row.get("relation_type", ""),
                        "type": "deep_graph_inference"
                    })
            
            # 第二层：通过项目间接关联的日志
            if max_depth >= 2:
                project_query = f"""
                MATCH (c:Concept {{name: '{concept_name}'}})<-[:MENTIONS]-(l:Log)-[:CONTRIBUTES_TO]->(p:Project)
                OPTIONAL MATCH (other_log:Log)-[:CONTRIBUTES_TO]->(p)
                WHERE other_log.id <> l.id
                RETURN DISTINCT other_log.content, other_log.timestamp, p.name as project_name, 'project_related' as relation_type
                ORDER BY other_log.timestamp DESC
                LIMIT 15
                """
                project_result = self.conn.execute(project_query)
                if project_result:
                    result_list = project_result.get_as_arrow().to_pylist()
                    for row in result_list:
                        results.append({
                            "content": row.get("other_log.content", ""),
                            "timestamp": str(row.get("other_log.timestamp", "")),
                            "related_project": row.get("project_name", ""),
                            "relation_type": row.get("relation_type", ""),
                            "type": "deep_graph_inference"
                        })
            
            # 第三层：通过目标关联的更深层关系
            if max_depth >= 3:
                goal_query = f"""
                MATCH (c:Concept {{name: '{concept_name}'}})<-[:MENTIONS]-(l:Log)-[:CONTRIBUTES_TO]->(p:Project)-[:BELONGS_TO]->(g:Goal)
                OPTIONAL MATCH (other_project:Project)-[:BELONGS_TO]->(g)
                WHERE other_project.id <> p.id
                RETURN DISTINCT other_project.name, g.title as goal_title, 'goal_related' as relation_type
                LIMIT 10
                """
                goal_result = self.conn.execute(goal_query)
                if goal_result:
                    result_list = goal_result.get_as_arrow().to_pylist()
                    for row in result_list:
                        results.append({
                            "content": f"相关项目: {row.get('other_project.name', '')}",
                            "related_goal": row.get('goal_title', ''),
                            "relation_type": row.get('relation_type', ''),
                            "type": "deep_graph_inference"
                        })
            
            logger.info(f"深度图谱推理完成，概念: {concept_name}, 深度: {max_depth}, 结果: {len(results)}")
            return results
            
        except Exception as e:
            logger.error(f"深度图谱推理失败: {e}")
            return []

    def find_concept_connections(self, concept_names: List[str], min_confidence: float = 0.7) -> List[Dict[str, Any]]:
        """
        查找多个概念之间的关联关系
        
        Args:
            concept_names: 概念名称列表
            min_confidence: 最小置信度阈值
            
        Returns:
            List[Dict[str, Any]]: 关联关系列表
        """
        try:
            connections = []
            
            # 构建概念列表字符串
            concept_list = "', '".join(concept_names)
            concept_list = f"'{concept_list}'"
            
            # 查询共同出现的日志
            common_logs_query = f"""
            MATCH (c1:Concept)<-[:MENTIONS]-(l:Log)-[:MENTIONS]->(c2:Concept)
            WHERE c1.name IN [{concept_list}] AND c2.name IN [{concept_list}] AND c1.name <> c2.name
            RETURN c1.name, c2.name, l.content, l.timestamp, count(l) as co_occurrence_count
            ORDER BY co_occurrence_count DESC
            LIMIT 20
            """
            result = self.conn.execute(common_logs_query)
            
            if result:
                result_list = result.get_as_arrow().to_pylist()
                for row in result_list:
                    co_occurrence = row.get('co_occurrence_count', 0)
                    confidence = min(1.0, co_occurrence / 10.0)  # 简单置信度计算
                    if confidence >= min_confidence:
                        connections.append({
                            "concept1": row.get('c1.name', ''),
                            "concept2": row.get('c2.name', ''),
                            "shared_content": row.get('l.content', ''),
                            "timestamp": str(row.get('l.timestamp', '')),
                            "co_occurrence_count": co_occurrence,
                            "confidence": confidence,
                            "type": "concept_connection"
                        })
            
            logger.info(f"概念关联查询完成，找到 {len(connections)} 个关联")
            return connections
            
        except Exception as e:
            logger.error(f"概念关联查询失败: {e}")
            return []

    def close(self):
        """
        关闭数据库连接
        """
        try:
            if self.conn:
                self.conn.close()
                logger.info("KuzuDB 连接已关闭")
        except Exception as e:
            logger.error(f"关闭连接失败: {e}")
