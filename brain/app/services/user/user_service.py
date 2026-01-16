import json
import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

from ...core.config import DATA_DIR

class UserService:
    """
    用户数据持久化服务
    使用 JSON 文件存储用户信息、愿景和人格配置
    """
    def __init__(self, storage_path: Optional[str] = None):
        if storage_path:
            self.storage_path = Path(storage_path)
        else:
            self.storage_path = DATA_DIR / "users.json"
        
        # 确保目录存在
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._data: Dict[str, Any] = self._load_data()

    def _load_data(self) -> Dict[str, Any]:
        """从文件加载数据"""
        if not self.storage_path.exists():
            return {}
        try:
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载用户数据失败: {e}")
            return {}

    def save(self):
        """保存数据到文件"""
        try:
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存用户数据失败: {e}")

    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        return self._data.get(user_id)

    def update_user(self, user_id: str, data: Dict[str, Any]):
        if user_id not in self._data:
            self._data[user_id] = {}
        self._data[user_id].update(data)
        self.save()

    def get_all_users(self) -> Dict[str, Dict[str, Any]]:
        return self._data

    def reset_user_data(self, user_id: str):
        """重置用户基础数据（人格、愿景等）"""
        if user_id in self._data:
            # 保留基本信息，重置配置
            base_info = {
                "id": self._data[user_id].get("id"),
                "email": self._data[user_id].get("email"),
                "name": self._data[user_id].get("name"),
                "created_at": self._data[user_id].get("created_at"),
                "last_active_at": self._data[user_id].get("last_active_at"),
            }
            self._data[user_id] = base_info
            self.save()
            return True
        return False

# 单例模式
user_service = UserService()
