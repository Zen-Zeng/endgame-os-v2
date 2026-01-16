import sqlite3
import json
import logging
from datetime import datetime, date
from pathlib import Path
from typing import List, Dict, Any, Optional
from .config import DATA_DIR

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            self.db_path = DATA_DIR / "brain.db"
        else:
            self.db_path = db_path
            
        self._init_db()

    def _get_conn(self):
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """初始化数据库表"""
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            with self._get_conn() as conn:
                # H3 能量表
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS h3_energy (
                        user_id TEXT NOT NULL,
                        date TEXT NOT NULL,
                        mind INTEGER NOT NULL,
                        body INTEGER NOT NULL,
                        spirit INTEGER NOT NULL,
                        vocation INTEGER NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (user_id, date)
                    );
                """)
                
                # H3 校准记录表
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS h3_calibrations (
                        id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        energy_data JSON NOT NULL,
                        mood_note TEXT,
                        blockers JSON,
                        wins JSON,
                        calibration_type TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                
                # 用户人格配置表
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS persona_configs (
                        user_id TEXT PRIMARY KEY,
                        config_data JSON NOT NULL,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                
                conn.commit()
            logger.info(f"SQLite 数据库初始化成功: {self.db_path}")
        except Exception as e:
            logger.error(f"SQLite 初始化失败: {e}")

    # --- H3 Energy ---
    def save_h3_energy(self, user_id: str, energy_data: Dict[str, Any]):
        try:
            with self._get_conn() as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO h3_energy (user_id, date, mind, body, spirit, vocation, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    user_id,
                    str(energy_data['date']),
                    energy_data['mind'],
                    energy_data['body'],
                    energy_data['spirit'],
                    energy_data['vocation'],
                    energy_data.get('created_at', datetime.now().isoformat())
                ))
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"Save H3 Energy Failed: {e}")
            return False

    def get_h3_energy_history(self, user_id: str, days: int = 7) -> List[Dict[str, Any]]:
        try:
            with self._get_conn() as conn:
                rows = conn.execute("""
                    SELECT * FROM h3_energy 
                    WHERE user_id = ? 
                    ORDER BY date DESC LIMIT ?
                """, (user_id, days)).fetchall()
                
                result = []
                for row in rows:
                    d = dict(row)
                    # 转换回 H3Energy 模型期望的格式
                    result.append({
                        "user_id": d["user_id"],
                        "date": d["date"],
                        "mind": d["mind"],
                        "body": d["body"],
                        "spirit": d["spirit"],
                        "vocation": d["vocation"],
                        "created_at": d["created_at"]
                    })
                return sorted(result, key=lambda x: x["date"])
        except Exception as e:
            logger.error(f"Get H3 History Failed: {e}")
            return []

    def clear_h3_data(self, user_id: str):
        """清空用户的 H3 能量和校准记录"""
        try:
            with self._get_conn() as conn:
                conn.execute("DELETE FROM h3_energy WHERE user_id = ?", (user_id,))
                conn.execute("DELETE FROM h3_calibrations WHERE user_id = ?", (user_id,))
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"Clear H3 Data Failed: {e}")
            return False

    def clear_persona_config(self, user_id: str):
        """清空用户的人格配置"""
        try:
            with self._get_conn() as conn:
                conn.execute("DELETE FROM persona_configs WHERE user_id = ?", (user_id,))
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"Clear Persona Config Failed: {e}")
            return False

    # --- H3 Calibrations ---
    def save_h3_calibration(self, calibration_data: Dict[str, Any]):
        try:
            with self._get_conn() as conn:
                conn.execute("""
                    INSERT INTO h3_calibrations (id, user_id, energy_data, mood_note, blockers, wins, calibration_type, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    calibration_data['id'],
                    calibration_data['user_id'],
                    json.dumps(calibration_data['energy']),
                    calibration_data.get('mood_note'),
                    json.dumps(calibration_data.get('blockers', [])),
                    json.dumps(calibration_data.get('wins', [])),
                    calibration_data.get('calibration_type', 'manual'),
                    calibration_data.get('created_at', datetime.now().isoformat())
                ))
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"Save H3 Calibration Failed: {e}")
            return False

    def get_h3_calibrations(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        try:
            with self._get_conn() as conn:
                rows = conn.execute("""
                    SELECT * FROM h3_calibrations 
                    WHERE user_id = ? 
                    ORDER BY created_at DESC LIMIT ?
                """, (user_id, limit)).fetchall()
                
                result = []
                for row in rows:
                    d = dict(row)
                    result.append({
                        "id": d["id"],
                        "user_id": d["user_id"],
                        "energy": json.loads(d["energy_data"]),
                        "mood_note": d["mood_note"],
                        "blockers": json.loads(d["blockers"]),
                        "wins": json.loads(d["wins"]),
                        "calibration_type": d["calibration_type"],
                        "created_at": d["created_at"]
                    })
                return result
        except Exception as e:
            logger.error(f"Get Calibrations Failed: {e}")
            return []

    # --- Persona Config ---
    def save_persona_config(self, user_id: str, config: Dict[str, Any]):
        try:
            with self._get_conn() as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO persona_configs (user_id, config_data, updated_at)
                    VALUES (?, ?, ?)
                """, (user_id, json.dumps(config), datetime.now().isoformat()))
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"Save Persona Config Failed: {e}")
            return False

    def get_persona_config(self, user_id: str) -> Optional[Dict[str, Any]]:
        try:
            with self._get_conn() as conn:
                row = conn.execute("SELECT config_data FROM persona_configs WHERE user_id = ?", (user_id,)).fetchone()
                return json.loads(row[0]) if row else None
        except Exception as e:
            logger.error(f"Get Persona Config Failed: {e}")
            return None

# 单例模式
db_manager = DatabaseManager()
