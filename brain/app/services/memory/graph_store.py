"""
SQLite 图谱存储实现 (Final Stable Version)
提供工业级的稳定性，并支持前端 3D 图谱可视化
"""
import sqlite3
import json
import logging
import threading
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GraphStore:
    def __init__(self, db_path: str = "./data/brain.db"):
        self.db_path = db_path
        self._lock = threading.Lock()
        self._init_db()

    def _get_conn(self):
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        try:
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
            with self._lock, self._get_conn() as conn:
                conn.execute("PRAGMA journal_mode=WAL;")
                # 节点表
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS nodes (
                        id TEXT PRIMARY KEY,
                        type TEXT NOT NULL,
                        name TEXT,
                        content TEXT,
                        attributes JSON,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_nodes_type ON nodes(type);")
                # 边表
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS edges (
                        source TEXT NOT NULL,
                        target TEXT NOT NULL,
                        relation TEXT NOT NULL,
                        properties JSON,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (source, target, relation),
                        FOREIGN KEY(source) REFERENCES nodes(id),
                        FOREIGN KEY(target) REFERENCES nodes(id)
                    );
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_edges_source ON edges(source);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_edges_target ON edges(target);")
            logger.info(f"SQLite GraphStore 初始化成功: {self.db_path}")
        except Exception as e:
            logger.error(f"SQLite 初始化失败: {e}")
            raise

    # --- 通用写入 ---
    def _upsert_node(self, conn, node_id, node_type, name="", content="", **kwargs):
        attributes = json.dumps(kwargs, ensure_ascii=False)
        conn.execute(
            "INSERT OR REPLACE INTO nodes (id, type, name, content, attributes) VALUES (?, ?, ?, ?, ?)",
            (node_id, node_type, name, content, attributes)
        )

    def _upsert_edge(self, conn, source, target, relation, **kwargs):
        props = json.dumps(kwargs, ensure_ascii=False)
        conn.execute(
            "INSERT OR IGNORE INTO edges (source, target, relation, properties) VALUES (?, ?, ?, ?)",
            (source, target, relation, props)
        )

    # --- 核心业务接口 ---
    def add_log(self, log_id: str, content: str, timestamp: str, log_type: str = "chat") -> bool:
        try:
            with self._lock, self._get_conn() as conn:
                self._upsert_node(conn, log_id, "Log", name=log_type, content=content, timestamp=timestamp)
            return True
        except Exception as e:
            logger.error(f"Add Log Failed: {e}")
            return False

    def add_concepts_batch(self, concepts: List[Dict[str, Any]]) -> bool:
        try:
            data = []
            for c in concepts:
                attr = json.dumps({"vector": c.get('vector')}, ensure_ascii=False)
                data.append((c['id'], "Concept", c['name'], "", attr))
            with self._lock, self._get_conn() as conn:
                conn.executemany(
                    "INSERT OR IGNORE INTO nodes (id, type, name, content, attributes) VALUES (?, ?, ?, ?, ?)",
                    data
                )
            return True
        except Exception: return False

    def add_mentions_batch(self, relations: List[Tuple[str, str]]) -> bool:
        try:
            data = [(src, tgt, "MENTIONS", "{}") for src, tgt in relations]
            with self._lock, self._get_conn() as conn:
                conn.executemany(
                    "INSERT OR IGNORE INTO edges (source, target, relation, properties) VALUES (?, ?, ?, ?)",
                    data
                )
            return True
        except Exception: return False

    # --- 兼容性接口 ---
    def add_user(self, name: str, vision: str):
        with self._lock, self._get_conn() as conn: self._upsert_node(conn, name, "User", name=name, vision=vision)
    def add_goal(self, goal_id: str, title: str, deadline: str = None, status: str = "active"):
        with self._lock, self._get_conn() as conn: self._upsert_node(conn, goal_id, "Goal", name=title, deadline=deadline, status=status)
    def add_project(self, project_id: str, name: str, sector: str = None):
        with self._lock, self._get_conn() as conn: self._upsert_node(conn, project_id, "Project", name=name, sector=sector)
    def add_task(self, task_id: str, title: str, status: str = "pending"):
        with self._lock, self._get_conn() as conn: self._upsert_node(conn, task_id, "Task", name=title, status=status)

    # 关系
    def add_has_goal_relation(self, u, g): self.add_edge(u, g, "HAS_GOAL")
    def add_belongs_to_relation(self, p, g): self.add_edge(p, g, "BELONGS_TO")
    def add_blocked_by_relation(self, t1, t2): self.add_edge(t1, t2, "BLOCKED_BY")
    def add_contributes_to_relation(self, l, p): self.add_edge(l, p, "CONTRIBUTES_TO")
    def add_mentions_relation(self, l, c): self.add_edge(l, c, "MENTIONS")

    def add_edge(self, source, target, relation):
        try:
            with self._lock, self._get_conn() as conn:
                self._upsert_edge(conn, source, target, relation)
            return True
        except Exception: return False

    # --- 查询接口 ---
    def get_all_graph_data(self) -> Dict[str, Any]:
        """
        修复 AttributeError: 获取全量图谱数据用于前端可视化
        限制返回 500 个节点以防卡顿
        """
        try:
            nodes = []
            links = []
            with self._get_conn() as conn:
                # 获取最新的 500 个节点
                n_rows = conn.execute("SELECT id, type, name, content FROM nodes ORDER BY created_at DESC LIMIT 500").fetchall()
                node_ids = set()
                for r in n_rows:
                    node_ids.add(r['id'])
                    # 简单区分 group 用于前端颜色
                    group = 1 if r['type'] == 'User' else 2 if r['type'] == 'Goal' else 3 if r['type'] == 'Project' else 4 if r['type'] == 'Concept' else 5
                    nodes.append({
                        "id": r['id'],
                        "name": r['name'] or r['content'][:20],
                        "group": group,
                        "type": r['type']
                    })
                
                # 获取这些节点之间的关系
                if node_ids:
                    placeholders = ','.join('?' * len(node_ids))
                    query = f"SELECT source, target, relation FROM edges WHERE source IN ({placeholders}) AND target IN ({placeholders})"
                    # 参数需要传两次
                    e_rows = conn.execute(query, list(node_ids) + list(node_ids)).fetchall()
                    for r in e_rows:
                        links.append({
                            "source": r['source'],
                            "target": r['target'],
                            "value": 1,
                            "type": r['relation']
                        })
            
            return {
                "nodes": nodes,
                "links": links,
                "total_nodes": len(nodes),
                "total_links": len(links)
            }
        except Exception as e:
            logger.error(f"Get Graph Data Error: {e}")
            return {"nodes": [], "links": [], "error": str(e)}

    def get_stats(self) -> Dict[str, Any]:
        try:
            with self._get_conn() as conn:
                n = conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
                e = conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
                return {"node_counts": {"total": n}, "relation_counts": {"total": e}}
        except Exception: return {}

    def clear_all_data(self):
        try:
            with self._lock, self._get_conn() as conn:
                conn.execute("DELETE FROM edges")
                conn.execute("DELETE FROM nodes")
            logger.info("SQLite 数据已清空")
        except Exception: pass