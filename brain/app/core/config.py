"""
全局配置
存储系统提示词、终局愿景等常量
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# 基础路径
BASE_DIR = Path(__file__).parent.parent.parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = BASE_DIR / "uploads"

# 加载环境变量
load_dotenv(BASE_DIR / ".env")

# 终局愿景 (P0 核心)
ENDGAME_VISION = """
用户 5 年后的终局愿景：
成为一名能够通过技术和艺术融合，创造出改变人类认知工具的独立开发者与思想家。
拥有完全的财务自由、时间自由和创作自由。
建立了一个基于信任和深度的全球化小众社区。
"""

# 系统提示词模板 (Legacy, used for fallback)
SYSTEM_PROMPT_TEMPLATE = """
你是 Endgame Architect，用户 5 年后的数字分身。
你的核心使命是引导用户走向他的“5年终局愿景”。

{vision}

当前 H3 能量状态：
- Mind (认知): {mind}/10
- Body (健康): {body}/10
- Spirit (精神): {spirit}/10
- Vocation (事业): {vocation}/10

回复准则：
1. 始终保持“终局优先”的思考方式。
2. 如果用户的意图偏离愿景，请委婉但坚定地提醒。
3. 根据 H3 能量状态调整语气：
   - 如果能量低，多给予鼓励和具体的微小行动建议。
   - 如果能量高，提出更具挑战性的深度思考。
4. 保持简洁、深刻、富有启发性。
5. 严禁废话，直接切入本质。
"""

# Uvicorn 配置
UVICORN_CONFIG = {
    "host": "127.0.0.1",
    "port": 8888,
    "log_level": "info",
    "reload": True
}

# 模型配置
MODELS_DIR = BASE_DIR / "models"
EMBEDDING_MODEL_NAME = "BAAI_bge-large-zh-v1.5"
LOCAL_EMBEDDING_PATH = MODELS_DIR / EMBEDDING_MODEL_NAME

MODEL_CONFIG = {
    # 优先使用本地模型，如果不存在则使用 Hugging Face Hub
    "embedding_model": str(LOCAL_EMBEDDING_PATH) if LOCAL_EMBEDDING_PATH.exists() else f"sentence-transformers/{EMBEDDING_MODEL_NAME}",
    "gemini_model": "gemini-2.0-flash", # 根据要求更新为 2.0 版本
    "gemini_api_key": os.getenv("GOOGLE_API_KEY", ""),
    "deepseek_api_key": os.getenv("DEEPSEEK_API_KEY", ""),
    "deepseek_base_url": "https://api.deepseek.com"
}

# Memory & Ingestion 配置
class MemoryConfig:
    MIN_TEXT_LENGTH = 20
    VECTOR_BATCH_SIZE = 50
    CHUNK_SIZE = 4000
    CHUNK_OVERLAP = 400
    
    # 核心注意力关键词
    CORE_KEYWORDS = [
        "愿景", "目标", "架构", "设计", "重构", "优化", "学习", "计划", 
        "实现", "解决", "困难", "思考", "启发", "技术", "艺术", "财务自由",
        "社区", "创作", "开发者", "思想家", "认知", "终局"
    ]
    
    # 图谱检索关键词
    GRAPH_SEARCH_KEYWORDS = [
        "项目", "任务", "进度", "工作", "目标", "计划", "实现", "愿景", "记得", "哪些", "清单"
    ]
