
import os
import asyncio
from google import genai
from dotenv import load_dotenv

# 加载环境变量
load_dotenv(".env")

async def test_specific_proxy():
    api_key = os.getenv("GOOGLE_API_KEY")
    proxy_url = "http://127.0.0.1:1082"
    
    print(f"🚀 使用指定代理 {proxy_url} 连接 Gemini API...")
    
    # 设置环境变量
    os.environ["http_proxy"] = proxy_url
    os.environ["https_proxy"] = proxy_url
    os.environ["HTTP_PROXY"] = proxy_url
    os.environ["HTTPS_PROXY"] = proxy_url

    try:
        client = genai.Client(api_key=api_key)
        
        def _sync_generate():
            return client.models.generate_content(
                model="gemini-2.0-flash",
                contents="Hello, simply reply 'OK' if you can hear me.",
            )
        
        response = await asyncio.to_thread(_sync_generate)
        print(f"🎉 Gemini 连接成功! 响应: {response.text}")
        
    except Exception as e:
        print(f"❌ Gemini 连接失败: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_specific_proxy())
