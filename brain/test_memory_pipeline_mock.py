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
    # 初始化记忆服务 - 使用模拟版本
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
    
    # 临时修改导入路径以使用模拟版本
    import app.services.neural.processor as neural_processor
    original_path = neural_processor.__file__
    neural_processor.__file__ = "/Users/andornot/endgame-os-v2/brain/app/services/neural/processor_mock.py"
    
    # 重新导入模块
    import importlib
    importlib.reload(neural_processor)
    
    # 创建记忆服务实例
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
    
    # 4. 测试文本添加
    test_text = "我完成了 Endgame OS 右脑感知层的开发，这个项目属于神经记忆图谱架构的目标。"
    logger.info(f"添加测试文本: {test_text}")
    add_result = memory_service.ingest_text(test_text)
    logger.info(f"添加结果: {add_result}")
    
    # 5. 再次查询验证
    logger.info("再次查询验证新添加的文本")
    query_results = memory_service.query_memory("右脑感知层")
    logger.info(f"查询到 {len(query_results)} 个结果:")
    for i, res in enumerate(query_results):
        logger.info(f"结果 {i+1} [{res.get('type')}]: {res.get('content')[:100]}...")

if __name__ == "__main__":
    test_pipeline()