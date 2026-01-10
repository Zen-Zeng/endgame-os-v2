import json
import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class UserService:
    """
    用户数据持久化服务
    使用 JSON 文件存储用户信息、愿景和人格配置
    """
    def __init__(self, storage_path: str = "data/users.json"):
        self.storage_path = Path(storage_path)
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

# 单例模式
user_service = UserService()
