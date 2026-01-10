
import asyncio
import os
import sys
from pathlib import Path

# 将 brain 目录添加到路径
sys.path.append(str(Path(__file__).parent))

from app.services.memory.memory_service import get_memory_service
from app.core.config import UPLOAD_DIR

async def test_memory_ingestion():
    print("🚀 开始测试记忆摄取系统...")
    
    # 确保上传目录存在
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    
    # 1. 创建一个模拟的对话记录文件
    test_file = UPLOAD_DIR / "test_dialog.txt"
    test_content = """
    用户: 我想在 5 年内成为一名独立的软件架构师。
    架构师: 这是一个宏伟的目标。你需要掌握分布式系统、云原生架构以及 AI 集成。
    用户: 我目前正在学习 Python 和 Rust。
    架构师: Python 非常适合快速原型开发，而 Rust 提供了极高的性能和内存安全性。
    """
    with open(test_file, "w", encoding="utf-8") as f:
        f.write(test_content)
    
    print(f"📝 已创建测试文件: {test_file}")
    
    # 2. 获取 MemoryService 实例
    service = get_memory_service()
    
    # 3. 执行摄取 (同步部分: 向量化)
    print("⏳ 正在进行向量化摄取 (同步)...")
    result = service.ingest_file(str(test_file))
    print(f"✅ 向量化完成: {result}")
    
    # 4. 等待一段时间让后台图谱提取运行 (异步部分)
    print("⏳ 等待后台图谱提取 (Gemini)...")
    await asyncio.sleep(5) 
    
    print("🏁 测试脚本运行结束。请检查控制台日志中的 Gemini 提取情况。")

if __name__ == "__main__":
    asyncio.run(test_memory_ingestion())
