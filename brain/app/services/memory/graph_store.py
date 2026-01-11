"""
SQLite 图谱存储实现 (Final Stable Version - Multi-User Support)
提供工业级的稳定性，并支持前端 3D 图谱可视化，强制用户隔离。
"""
import sqlite3
import json
import logging
import threading
import hashlib
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GraphStore:
    def __init__(self, db_path: str = "./data/brain.db"):
        self.db_path = db_path
        self._lock = threading.Lock()
        self._init_db()

    def _get_stable_id(self, text: str) -> str:
        """生成稳定的 ID，防止 Python hash() 随机化问题"""
        return f"con_{hashlib.md5(text.encode('utf-8')).hexdigest()[:16]}"

    def _get_conn(self):
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        try:
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
            with self._lock, self._get_conn() as conn:
                conn.execute("PRAGMA journal_mode=WAL;")
                # 节点表 - 增加 user_id
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS nodes (
                        id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        type TEXT NOT NULL,
                        name TEXT,
                        content TEXT,
                        attributes JSON,
                        status TEXT DEFAULT 'confirmed',
                        time_metadata JSON,
                        strategic_role TEXT, -- Phase 2: 战略角色
                        energy_impact INTEGER, -- Phase 2: 能量影响
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                
                # [Strategic Brain] 自动迁移：检查并添加 status, time_metadata, strategic_role, energy_impact 列
                try:
                    # 检查列是否存在
                    cursor = conn.execute("PRAGMA table_info(nodes)")
                    columns = [row['name'] for row in cursor.fetchall()]
                    
                    if 'status' not in columns:
                        logger.info("Migrating database: Adding 'status' column to nodes table...")
                        conn.execute("ALTER TABLE nodes ADD COLUMN status TEXT DEFAULT 'confirmed'")
                        
                    if 'time_metadata' not in columns:
                        logger.info("Migrating database: Adding 'time_metadata' column to nodes table...")
                        conn.execute("ALTER TABLE nodes ADD COLUMN time_metadata JSON")

                    if 'strategic_role' not in columns:
                        logger.info("Migrating database: Adding 'strategic_role' column to nodes table...")
                        conn.execute("ALTER TABLE nodes ADD COLUMN strategic_role TEXT")

                    if 'energy_impact' not in columns:
                        logger.info("Migrating database: Adding 'energy_impact' column to nodes table...")
                        conn.execute("ALTER TABLE nodes ADD COLUMN energy_impact INTEGER")
                        
                except Exception as e:
                    logger.warning(f"Database migration check warning: {e}")

                conn.execute("CREATE INDEX IF NOT EXISTS idx_nodes_user ON nodes(user_id);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_nodes_type ON nodes(type);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_nodes_status ON nodes(status);")
                # 边表 - 增加 user_id 并修改主键
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS edges (
                        source TEXT NOT NULL,
                        target TEXT NOT NULL,
                        relation TEXT NOT NULL,
                        user_id TEXT NOT NULL,
                        properties JSON,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (source, target, relation, user_id),
                        FOREIGN KEY(source) REFERENCES nodes(id),
                        FOREIGN KEY(target) REFERENCES nodes(id)
                    );
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_edges_user ON edges(user_id);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_edges_source ON edges(source);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_edges_target ON edges(target);")

                # 3. 经验表 (存储进化出来的智慧)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS experiences (
                        id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        trigger_scenario TEXT,
                        insight TEXT,
                        strategy TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_experiences_user ON experiences(user_id);")
            logger.info(f"SQLite GraphStore 初始化成功: {self.db_path}")
        except Exception as e:
            logger.error(f"SQLite 初始化失败: {e}")
            raise

    # --- 通用写入 ---
    def _upsert_node(self, conn, user_id, node_id, node_type, name="", content="", status="confirmed", time_metadata=None, strategic_role=None, energy_impact=None, **kwargs):
        attributes = json.dumps(kwargs, ensure_ascii=False)
        time_meta_json = json.dumps(time_metadata, ensure_ascii=False) if time_metadata else None
        
        # 检查表是否有新列，如果没有则添加（为了兼容旧库）
        try:
            conn.execute(
                "INSERT OR REPLACE INTO nodes (id, user_id, type, name, content, attributes, status, time_metadata, strategic_role, energy_impact) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (node_id, user_id, node_type, name, content, attributes, status, time_meta_json, strategic_role, energy_impact)
            )
        except sqlite3.OperationalError:
            # 如果是旧表结构，先尝试添加列 (虽然 _init_db 应该已经处理了，但为了健壮性保留)
            try:
                # 尝试添加可能缺失的列
                columns_to_add = {
                    "status": "TEXT DEFAULT 'confirmed'",
                    "time_metadata": "JSON",
                    "strategic_role": "TEXT",
                    "energy_impact": "INTEGER"
                }
                for col, type_def in columns_to_add.items():
                    try:
                        conn.execute(f"ALTER TABLE nodes ADD COLUMN {col} {type_def}")
                    except sqlite3.OperationalError:
                        pass # 列可能已存在

                # 重试插入
                conn.execute(
                    "INSERT OR REPLACE INTO nodes (id, user_id, type, name, content, attributes, status, time_metadata, strategic_role, energy_impact) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (node_id, user_id, node_type, name, content, attributes, status, time_meta_json, strategic_role, energy_impact)
                )
            except Exception as e:
                logger.error(f"Schema migration failed in _upsert_node: {e}")
                raise

    def _upsert_edge(self, conn, user_id, source, target, relation, **kwargs):
        props = json.dumps(kwargs, ensure_ascii=False)
        conn.execute(
            "INSERT OR IGNORE INTO edges (source, target, relation, user_id, properties) VALUES (?, ?, ?, ?, ?)",
            (source, target, relation, user_id, props)
        )

    def _ensure_tables(self):
        """确保必要的表存在，如果不存在则初始化"""
        try:
            with self._lock, self._get_conn() as conn:
                cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='nodes'")
                if not cursor.fetchone():
                    logger.warning("检测到数据库表缺失，正在初始化...")
                    self._init_db()
                
                # 额外检查 experiences 表 (针对迁移场景)
                cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='experiences'")
                if not cursor.fetchone():
                    logger.warning("检测到 experiences 表缺失，正在初始化...")
                    self._init_db()
        except Exception as e:
            logger.error(f"检查表结构失败: {e}")

    def sync_user_to_self_node(self, user_id: str, vision_data: Optional[Dict[str, Any]] = None):
        """
        [Strategic Brain] 核心方法：确保 User 配置同步到图谱的 Self 节点
        """
        try:
            self._ensure_tables()
            with self._lock, self._get_conn() as conn:
                # 1. 确保 Self 节点存在
                self._upsert_node(
                    conn, 
                    user_id, 
                    user_id, # Self 节点的 ID 就是 user_id
                    "Self", 
                    name="Me", 
                    content="The Owner of this Endgame OS",
                    status="confirmed"
                )
                
                # 2. 如果有愿景数据，同步 Vision 节点
                if vision_data:
                    vision_id = f"vision_{user_id}"
                    # 提取时间元数据
                    time_meta = {
                        "start_date": vision_data.get("chapter_start_date"),
                        "target_date": vision_data.get("target_date")
                    }
                    
                    self._upsert_node(
                        conn,
                        user_id,
                        vision_id,
                        "Vision",
                        name=vision_data.get("title", "My Vision"),
                        content=vision_data.get("description", ""),
                        status="confirmed",
                        time_metadata=time_meta,
                        # 额外属性
                        core_values=vision_data.get("core_values", []),
                        milestones=vision_data.get("key_milestones", [])
                    )
                    
                    # 3. 建立 Self -> OWNS -> Vision 关系
                    self._upsert_edge(conn, user_id, user_id, vision_id, "OWNS")
                    
            logger.info(f"User {user_id} sync to Self/Vision nodes completed.")
            return True
        except Exception as e:
            logger.error(f"Sync User to Self Node Failed: {e}")
            return False

    # --- 核心业务接口 ---
    def add_log(self, user_id: str, log_id: str, content: str, timestamp: str, log_type: str = "chat") -> bool:
        try:
            self._ensure_tables()
            with self._lock, self._get_conn() as conn:
                self._upsert_node(conn, user_id, log_id, "Log", name=log_type, content=content, timestamp=timestamp)
            return True
        except Exception as e:
            logger.error(f"Add Log Failed: {e}")
            return False

    def add_person(self, user_id: str, name: str, role: str, energy_impact: int) -> bool:
        """
        [Phase 2] 新增关键人物节点
        role: Mentor, Partner, Drainer
        energy_impact: +1 (Boost), -1 (Drain), 0 (Neutral)
        """
        try:
            self._ensure_tables()
            person_id = self._get_stable_id(name)
            with self._lock, self._get_conn() as conn:
                self._upsert_node(
                    conn,
                    user_id,
                    person_id,
                    "Person",
                    name=name,
                    strategic_role=role,
                    energy_impact=energy_impact,
                    status="confirmed"
                )
            return True
        except Exception as e:
            logger.error(f"Add Person Failed: {e}")
            return False

    def add_concepts_batch(self, user_id: str, concepts: List[Dict[str, Any]]) -> bool:
        try:
            self._ensure_tables()
            data = []
            for c in concepts:
                attr = json.dumps({"vector": c.get('vector')}, ensure_ascii=False)
                # 注意：这里只插入基本字段，不覆盖可能已存在的 Person 特殊字段
                data.append((c['id'], user_id, "Concept", c['name'], "", attr))
            with self._lock, self._get_conn() as conn:
                conn.executemany(
                    "INSERT OR REPLACE INTO nodes (id, user_id, type, name, content, attributes) VALUES (?, ?, ?, ?, ?, ?)",
                    data
                )
            return True
        except Exception: return False

    def add_mentions_batch(self, user_id: str, relations: List[Tuple[str, str]]) -> bool:
        try:
            self._ensure_tables()
            data = [(src, tgt, "MENTIONS", user_id, "{}") for src, tgt in relations]
            with self._lock, self._get_conn() as conn:
                conn.executemany(
                    "INSERT OR IGNORE INTO edges (source, target, relation, user_id, properties) VALUES (?, ?, ?, ?, ?)",
                    data
                )
            return True
        except Exception: return False

    def upsert_entities_batch(self, user_id: str, entities: List[Dict[str, Any]]) -> bool:
        """批量更新实体及其元数据，支持档案深度合并"""
        try:
            self._ensure_tables()
            with self._lock, self._get_conn() as conn:
                for e in entities:
                    name = e.get("name")
                    if not name: continue
                    
                    node_id = self._get_stable_id(name)
                    node_type = e.get("type", "Concept")
                    content = e.get("content", "")
                    new_dossier = e.get("dossier", {})
                    
                    # 1. 获取现有属性
                    cursor = conn.execute("SELECT attributes FROM nodes WHERE id = ? AND user_id = ?", (node_id, user_id))
                    row = cursor.fetchone()
                    
                    current_attrs = {}
                    if row and row['attributes']:
                        try:
                            current_attrs = json.loads(row['attributes'])
                        except: pass
                    
                    # 2. 合并档案信息 (Dossier)
                    if "dossier" not in current_attrs:
                        current_attrs["dossier"] = {}
                    
                    # 深度合并逻辑：更新或添加新字段
                    if isinstance(new_dossier, dict):
                        for k, v in new_dossier.items():
                            if isinstance(v, list) and k in current_attrs["dossier"] and isinstance(current_attrs["dossier"][k], list):
                                # 列表类型：去重合并
                                current_attrs["dossier"][k] = list(set(current_attrs["dossier"][k] + v))
                            else:
                                # 其他类型：直接更新
                                current_attrs["dossier"][k] = v
                    
                    # 3. 执行更新或插入
                    attr_json = json.dumps(current_attrs, ensure_ascii=False)
                    conn.execute("""
                        INSERT INTO nodes (id, user_id, type, name, content, attributes)
                        VALUES (?, ?, ?, ?, ?, ?)
                        ON CONFLICT(id) DO UPDATE SET
                            type = excluded.type,
                            content = CASE WHEN excluded.content != '' THEN excluded.content ELSE nodes.content END,
                            attributes = ?
                    """, (node_id, user_id, node_type, name, content, attr_json, attr_json))
                
            return True
        except Exception as e:
            logger.error(f"Upsert Entities Batch Failed: {e}")
            return False

    def upsert_relations_batch(self, user_id: str, relations: List[Dict[str, Any]]) -> bool:
        """批量更新关系及其属性"""
        try:
            self._ensure_tables()
            edge_data = []
            for r in relations:
                src_name = r.get("source")
                tgt_name = r.get("target")
                rel = r.get("relation")
                
                if not src_name or not tgt_name or not rel: continue
                
                src_id = self._get_stable_id(src_name)
                tgt_id = self._get_stable_id(tgt_name)
                
                # 准备边数据
                edge_data.append((src_id, tgt_id, rel, user_id, json.dumps(r.get("properties", {}))))
            
            with self._lock, self._get_conn() as conn:
                conn.executemany(
                    "INSERT OR IGNORE INTO edges (source, target, relation, user_id, properties) VALUES (?, ?, ?, ?, ?)",
                    edge_data
                )
            return True
        except Exception as e:
            logger.error(f"Upsert Relations Batch Failed: {e}")
            return False

    def add_triplets_batch(self, user_id: str, triplets: List[Tuple[str, str, str]]) -> bool:
        """批量添加三元组 (subj, rel, obj)"""
        try:
            node_data = []
            edge_data = []
            
            for subj, rel, obj in triplets:
                if not subj or not obj or not rel: continue
                
                subj_id = self._get_stable_id(subj)
                obj_id = self._get_stable_id(obj)
                
                # 准备节点数据 (Concept)
                node_data.append((subj_id, user_id, "Concept", subj, "", "{}"))
                node_data.append((obj_id, user_id, "Concept", obj, "", "{}"))
                
                # 准备边数据
                edge_data.append((subj_id, obj_id, rel, user_id, "{}"))
            
            with self._lock, self._get_conn() as conn:
                # 批量插入节点 (IGNORE 如果已存在)
                conn.executemany(
                    "INSERT OR IGNORE INTO nodes (id, user_id, type, name, content, attributes) VALUES (?, ?, ?, ?, ?, ?)",
                    node_data
                )
                # 批量插入边
                conn.executemany(
                    "INSERT OR IGNORE INTO edges (source, target, relation, user_id, properties) VALUES (?, ?, ?, ?, ?)",
                    edge_data
                )
            return True
        except Exception as e:
            logger.error(f"Add Triplets Batch Failed: {e}")
            return False

    def add_experience(self, user_id: str, exp_id: str, trigger: str, insight: str, strategy: str) -> bool:
        """记录一条进化出来的经验"""
        try:
            self._ensure_tables()
            with self._lock, self._get_conn() as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO experiences (id, user_id, trigger_scenario, insight, strategy) VALUES (?, ?, ?, ?, ?)",
                    (exp_id, user_id, trigger, insight, strategy)
                )
            return True
        except Exception as e:
            logger.error(f"添加经验失败: {e}")
            return False

    def get_all_experiences(self, user_id: str) -> List[Dict[str, Any]]:
        """获取用户的所有经验"""
        try:
            with self._get_conn() as conn:
                rows = conn.execute("SELECT * FROM experiences WHERE user_id = ?", (user_id,)).fetchall()
                return [dict(row) for row in rows]
        except Exception: return []

    # --- 查询接口 ---
    def get_all_graph_data(self, user_id: str = "default_user", *args, **kwargs) -> Dict[str, Any]:
        """优化：获取特定用户的图谱数据用于前端可视化"""
        # 兼容性处理
        actual_user_id = user_id
        if not actual_user_id and args:
            actual_user_id = args[0]
            
        try:
            nodes = []
            links = []
            with self._get_conn() as conn:
                # 1. 获取该用户的节点
                # Phase 2: 获取 strategic_role 和 energy_impact
                c_rows = conn.execute(
                    "SELECT id, type, name, content, attributes, strategic_role, energy_impact FROM nodes WHERE user_id=? AND type='Concept' ORDER BY created_at DESC LIMIT 300",
                    (actual_user_id,)
                ).fetchall()
                
                l_rows = conn.execute(
                    "SELECT id, type, name, content, attributes, strategic_role, energy_impact FROM nodes WHERE user_id=? AND type!='Concept' ORDER BY created_at DESC LIMIT 200",
                    (actual_user_id,)
                ).fetchall()
                
                all_rows = list(c_rows) + list(l_rows)
                node_ids = set()
                
                for r in all_rows:
                    node_ids.add(r['id'])
                    group = 1 if r['type'] == 'User' else 2 if r['type'] == 'Goal' else 3 if r['type'] == 'Project' else 4 if r['type'] == 'Concept' else 5
                    # 准备前端显示数据
                    display_data = {
                        "类型": r['type'],
                        "描述": r['content'] or "无详细内容"
                    }
                    
                    # Phase 2: 显示战略属性
                    if r['strategic_role']:
                        display_data["战略角色"] = r['strategic_role']
                    if r['energy_impact']:
                        display_data["能量影响"] = str(r['energy_impact'])
                    
                    # 如果有档案信息，也加入显示
                    attrs = json.loads(r['attributes']) if r['attributes'] else {}
                    dossier = attrs.get('dossier', {})
                    if dossier:
                        for k, v in dossier.items():
                            key_name = f"档案_{k}"
                            if isinstance(v, list):
                                display_data[key_name] = ", ".join(v)
                            else:
                                display_data[key_name] = str(v)

                    nodes.append({
                        "id": r['id'],
                        "label": r['name'] or (r['content'][:20] if r['content'] else "Unknown"),
                        "group": group,
                        "type": r['type'],
                        "content": r['content'],
                        "attributes": attrs,
                        "data": display_data
                    })

                # 2. 获取该用户的边 (增加 LIMIT 并优先返回战略层级关系)
                if node_ids:
                    placeholders = ','.join('?' * len(node_ids))
                    query = f"""
                        SELECT source, target, relation 
                        FROM edges 
                        WHERE user_id=? AND (source IN ({placeholders}) OR target IN ({placeholders}))
                        ORDER BY CASE WHEN relation IN ('OWNS', 'DECOMPOSES_TO', 'ACHIEVED_BY', 'CONSISTS_OF') THEN 0 ELSE 1 END, created_at DESC
                        LIMIT 5000
                    """
                    params = [actual_user_id] + list(node_ids) + list(node_ids)
                    e_rows = conn.execute(query, params).fetchall()
                    
                    existing_ids = node_ids.copy()
                    for r in e_rows:
                        if r['target'] not in existing_ids:
                            nodes.append({"id": r['target'], "label": r['target'], "group": 4, "type": "Concept"})
                            existing_ids.add(r['target'])
                        if r['source'] not in existing_ids:
                            nodes.append({"id": r['source'], "label": r['source'], "group": 4, "type": "Concept"})
                            existing_ids.add(r['source'])
                            
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

    def get_stats(self, user_id: str = "default_user", *args, **kwargs) -> Dict[str, Any]:
        # 兼容性处理
        actual_user_id = user_id
        if not actual_user_id and args:
            actual_user_id = args[0]
            
        try:
            with self._get_conn() as conn:
                n = conn.execute("SELECT COUNT(*) FROM nodes WHERE user_id=?", (actual_user_id,)).fetchone()[0]
                e = conn.execute("SELECT COUNT(*) FROM edges WHERE user_id=?", (actual_user_id,)).fetchone()[0]
                
                # 增加各类型节点的统计
                type_counts = conn.execute(
                    "SELECT type, COUNT(*) as count FROM nodes WHERE user_id=? GROUP BY type", 
                    (actual_user_id,)
                ).fetchall()
                
                return {
                    "node_counts": {
                        "total": n,
                        **{row["type"]: row["count"] for row in type_counts}
                    },
                    "relation_counts": {"total": e}
                }
        except Exception: return {}

    def get_nodes_by_type(self, user_id: str, node_type: str) -> List[Dict[str, Any]]:
        """获取特定类型的节点"""
        try:
            with self._get_conn() as conn:
                rows = conn.execute(
                    "SELECT id, type, name, content, attributes FROM nodes WHERE user_id=? AND type=?",
                    (user_id, node_type)
                ).fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Get Nodes By Type Failed: {e}")
            return []

    def get_sub_entities(self, user_id: str, parent_id: str, relation_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取子实体（如目标下的项目，项目下的任务）"""
        try:
            with self._get_conn() as conn:
                query = """
                    SELECT n.id, n.type, n.name, n.content, n.attributes, e.relation
                    FROM nodes n
                    JOIN edges e ON n.id = e.target
                    WHERE e.source = ? AND e.user_id = ?
                """
                params = [parent_id, user_id]
                if relation_type:
                    query += " AND e.relation = ?"
                    params.append(relation_type)
                
                rows = conn.execute(query, params).fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Get Sub Entities Failed: {e}")
            return []

    def clear_all_data(self, user_id: str = None):
        """清空数据：如果提供 user_id 则只清空该用户的数据，否则清空全部"""
        try:
            with self._lock, self._get_conn() as conn:
                if user_id:
                    conn.execute("DELETE FROM edges WHERE user_id=?", (user_id,))
                    conn.execute("DELETE FROM nodes WHERE user_id=?", (user_id,))
                    logger.info(f"用户 {user_id} 的 SQLite 数据已清空")
                else:
                    conn.execute("DELETE FROM edges")
                    conn.execute("DELETE FROM nodes")
                    logger.info("所有 SQLite 数据已清空")
        except Exception as e:
            logger.error(f"Clear data failed: {e}")
