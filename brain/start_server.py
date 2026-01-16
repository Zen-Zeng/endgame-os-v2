#!/usr/bin/env python
"""
Endgame OS v2.0 - 后端服务启动脚本
负责环境初始化、代理配置加载及 Uvicorn 服务器启动
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# 1. 基础环境配置
# 将当前目录添加到 Python 路径，确保 app 模块可导入
CURRENT_DIR = Path(__file__).parent.absolute()
sys.path.append(str(CURRENT_DIR))

# 2. 代理与环境变量管理
# 强制从 .env 加载配置，override=True 确保覆盖系统可能存在的旧代理变量
load_dotenv(dotenv_path=CURRENT_DIR / ".env", override=True)

def setup_proxy():
    """统一管理代理环境变量，确保大小写一致并覆盖系统旧变量"""
    proxy_map = {
        'HTTP_PROXY': os.environ.get('HTTP_PROXY'),
        'HTTPS_PROXY': os.environ.get('HTTPS_PROXY'),
        'ALL_PROXY': os.environ.get('ALL_PROXY')
    }
    
    for key, value in proxy_map.items():
        if value:
            # 同时设置大写和小写版本
            os.environ[key] = value
            os.environ[key.lower()] = value
            
def print_env_status():
    """打印当前网络环境状态"""
    # 优先检查常用的大写变量
    proxy = os.environ.get('HTTPS_PROXY') or os.environ.get('HTTP_PROXY') or os.environ.get('ALL_PROXY')
    
    if proxy:
        print(f"🌐 网络代理已就绪: {proxy}")
    else:
        print("✨ 系统运行在直连模式 (No Proxy)")

# 3. 启动服务器
if __name__ == "__main__":
    print("🚀 Endgame OS Brain 正在启动...")
    setup_proxy()
    print_env_status()
    
    try:
        from app.main import main
        from app.core.config import UVICORN_CONFIG
        
        # 准备命令行参数以符合 app.main:main 的解析逻辑
        host = UVICORN_CONFIG.get("host", "127.0.0.1")
        port = UVICORN_CONFIG.get("port", 8888)
        
        sys.argv = [sys.argv[0], f"--host={host}", f"--port={port}"]
        
        # 执行主应用启动
        main()
    except ImportError as e:
        print(f"❌ 启动失败: 找不到核心模块 ({e})")
        print("💡 请检查是否已安装所有依赖: pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 运行过程中出现异常: {e}")
        sys.exit(1)
