import sys
import os
from pathlib import Path

# 添加项目根目录到 sys.path
sys.path.append(str(Path(__file__).parent))

from app.services.memory.memory_service import MemoryService
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_pipeline():
    # 初始化记忆服务
    # 使用测试目录
    test_chroma_path = "./data/test_chroma"
    test_kuzu_path = "./data/test_kuzu"
    
    # 清理旧的测试数据
    import shutil
    if os.path.exists(test_chroma_path):
        if os.path.isdir(test_chroma_path):
            shutil.rmtree(test_chroma_path)
        else:
            os.remove(test_chroma_path)
            
    if os.path.exists(test_kuzu_path):
        if os.path.isdir(test_kuzu_path):
            shutil.rmtree(test_kuzu_path)
        else:
            os.remove(test_kuzu_path)
    
    # 不要手动创建目录，让数据库驱动自己处理
    # Path(test_chroma_path).mkdir(parents=True, exist_ok=True)
    # Path(test_kuzu_path).mkdir(parents=True, exist_ok=True)
        
    memory_service = MemoryService(
        persist_directory=test_chroma_path,
        graph_db_path=test_kuzu_path
    )
    
    # 1. 测试文件导入
    test_file = "/Users/andornot/endgame-os-v2/brain/uploads/conversations.json"
    logger.info(f"开始导入测试文件: {test_file}")
    
    # 只处理前几条记录以节省时间
    # 我们需要修改 ingest_file 或者创建一个临时的测试文件
    # 这里我们直接调用 ingest_file，它会处理整个文件
    result = memory_service.ingest_file(test_file)
    logger.info(f"导入结果: {result}")
    
    if not result['success']:
        logger.error(f"导入失败: {result.get('error')}")
        return

    # 2. 测试统计信息
    stats = memory_service.get_stats()
    logger.info(f"记忆统计: {stats}")

    # 3. 测试查询
    query = "Endgame OS"
    logger.info(f"开始查询: {query}")
    query_results = memory_service.query_memory(query)
    
    logger.info(f"查询到 {len(query_results)} 个结果:")
    for i, res in enumerate(query_results):
        logger.info(f"结果 {i+1} [{res.get('type')}]: {res.get('content')[:100]}...")
        if 'metadata' in res:
            logger.info(f"  元数据: {res.get('metadata')}")

if __name__ == "__main__":
    test_pipeline()
