#!/usr/bin/env python
"""
启动Endgame OS v2.0 后端服务
"""
import sys
import importlib

# 添加当前目录到Python路径
sys.path.append('/Users/andornot/endgame-os-v2/brain')

# 强制清除代理环境变量，确保纯净直连模式
import os
proxy_vars = ['http_proxy', 'https_proxy', 'all_proxy', 'HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY']
for var in proxy_vars:
    if var in os.environ:
        del os.environ[var]
print("✅ 已强制清除所有代理环境变量，系统将以直连模式运行")

# 应用importlib.metadata的猴子补丁
try:
    import importlib.metadata
    # 在Python 3.9中，packages_distributions被重命名为distributions
    if not hasattr(importlib.metadata, 'packages_distributions'):
        import importlib.metadata
        import collections
        
        # 模拟packages_distributions的行为
        def packages_distributions():
            dists = list(importlib.metadata.distributions())
            # 按包名分组
            packages = collections.defaultdict(list)
            for dist in dists:
                # 获取包名
                pkg_name = dist.metadata['Name']
                packages[pkg_name].append(dist)
            return dict(packages)
        
        setattr(importlib.metadata, 'packages_distributions', packages_distributions)
    print("✅ importlib.metadata 猴子补丁已应用")
except Exception as e:
    print(f"❌ 应用猴子补丁时出错: {e}")
    sys.exit(1)

# 导入主模块并运行
if __name__ == "__main__":
    # 直接导入主模块中的main函数并运行
    from app.main import main
    # 导入配置
    from app.core.config import UVICORN_CONFIG
    
    # 使用配置中的主机地址和端口
    import sys
    host = UVICORN_CONFIG.get("host", "0.0.0.0")
    port = UVICORN_CONFIG.get("port", 8080)
    sys.argv = [sys.argv[0], f"--host={host}", f"--port={port}"]
    main()