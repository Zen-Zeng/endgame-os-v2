
import os
import asyncio
import httpx
from google import genai
from dotenv import load_dotenv

# 加载环境变量
load_dotenv(".env")

async def check_proxy(proxy_url):
    print(f"🔍 正在测试代理: {proxy_url} ...")
    try:
        async with httpx.AsyncClient(proxies=proxy_url, timeout=5.0) as client:
            resp = await client.get("https://www.google.com", follow_redirects=True)
            if resp.status_code == 200:
                print(f"✅ 代理可用: {proxy_url}")
                return True
    except Exception as e:
        # print(f"❌ 失败: {str(e)}")
        pass
    return False

async def test_gemini_with_proxy(proxy_url):
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("❌ 错误: 未找到 GOOGLE_API_KEY")
        return

    print(f"🚀 使用代理 {proxy_url} 连接 Gemini API...")
    
    # 设置环境变量，Gemini Client 底层依赖的库通常会读取这些变量
    os.environ["http_proxy"] = proxy_url
    os.environ["https_proxy"] = proxy_url
    os.environ["HTTP_PROXY"] = proxy_url
    os.environ["HTTPS_PROXY"] = proxy_url

    try:
        client = genai.Client(api_key=api_key)
        
        def _sync_generate():
            # 尝试显式传递 http_options (如果库支持)
            # 注意：新版 genai client 可能通过 transport 或环境变量处理代理
            # 这里主要依赖环境变量
            return client.models.generate_content(
                model="gemini-2.0-flash",
                contents="Hello, simply reply 'OK' if you can hear me.",
            )
        
        response = await asyncio.to_thread(_sync_generate)
        print(f"🎉 Gemini 连接成功! 响应: {response.text}")
        return True
        
    except Exception as e:
        print(f"❌ Gemini 连接失败: {str(e)}")
        return False

async def main():
    # 常用代理端口列表
    common_proxies = [
        "http://127.0.0.1:7890", # Clash HTTP
        "http://127.0.0.1:1087", # V2Ray HTTP
        "http://127.0.0.1:1080", # Shadowsocks / Generic SOCKS5 turned HTTP
        "http://127.0.0.1:8080", # Generic
        "socks5://127.0.0.1:7891", # Clash SOCKS
        "socks5://127.0.0.1:1080", # Shadowsocks
        "socks5://127.0.0.1:1086", # V2Ray SOCKS
    ]
    
    working_proxy = None
    
    print("🕵️‍♂️ 开始探测本地代理端口...")
    for proxy in common_proxies:
        if await check_proxy(proxy):
            working_proxy = proxy
            break
            
    if working_proxy:
        print(f"\n✅ 找到可用代理: {working_proxy}")
        success = await test_gemini_with_proxy(working_proxy)
        if success:
            print(f"\n💡 建议: 请将 'HTTPS_PROXY={working_proxy}' 添加到 .env 文件中")
    else:
        print("\n⚠️ 未检测到常用的本地代理端口。")
        print("如果您使用的是 Outline，请在 Outline 客户端中查看 'HTTP Proxy Port' 或 'SOCKS Proxy Port'。")
        print("由于 ss:// 协议无法直接使用，我们需要这个本地转换后的地址。")

if __name__ == "__main__":
    asyncio.run(main())
