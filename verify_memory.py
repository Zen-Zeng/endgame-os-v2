
import os
import json
import time
import subprocess

def call_api(method, path, data=None):
    url = f"http://127.0.0.1:8888/api/v1{path}"
    headers = ["-H", "Authorization: Bearer test_token_999", "-H", "Content-Type: application/json"]
    
    # 禁用代理，确保直连本地服务器
    env = os.environ.copy()
    for var in ['http_proxy', 'https_proxy', 'all_proxy', 'HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY']:
        if var in env:
            del env[var]
    
    cmd = ["curl", "-s", "-X", method, url] + headers
    if data:
        cmd += ["-d", json.dumps(data)]
    
    result = subprocess.run(cmd, capture_output=True, text=True, env=env)
    if not result.stdout:
        print(f"DEBUG: curl output is empty. stderr: {result.stderr}")
        return None
    
    try:
        # 如果是 SSE 流式响应，提取 data: 部分
        if "data: " in result.stdout:
            lines = result.stdout.split("\n")
            full_text = ""
            for line in lines:
                if line.startswith("data: "):
                    content = line[6:].strip()
                    if content and content != "[DONE]":
                        try:
                            data_json = json.loads(content)
                            if "choices" in data_json:
                                full_text += data_json["choices"][0].get("delta", {}).get("content", "")
                            elif "content" in data_json:
                                full_text += data_json["content"]
                        except:
                            full_text += content
            return full_text
        return json.loads(result.stdout)
    except Exception as e:
        print(f"DEBUG: Parse error: {e}")
        return result.stdout

def verify():
    # 1. 发送一条包含项目信息的对话
    print("--- 发送训练对话 ---")
    chat_payload = {
        "message": "我现在正在启动一个新项目，叫做『认知重构系统』。这个项目的目标是利用大语言模型来优化人类的思考流程，计划在2026年底完成。目前我已经完成了架构设计，下一步是开发原型。",
        # "conversation_id": "verify_conv_123" # 不要指定ID，让它自动创建
    }
    
    # 提取对话ID
    url = f"http://127.0.0.1:8888/api/v1/chat/send"
    env = os.environ.copy()
    for var in ['http_proxy', 'https_proxy', 'all_proxy', 'HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY']:
        if var in env: del env[var]
        
    cmd = ["curl", "-s", "-X", "POST", url, 
           "-H", "Authorization: Bearer test_token_999", 
           "-H", "Content-Type: application/json",
           "-d", json.dumps(chat_payload)]
    
    result = subprocess.run(cmd, capture_output=True, text=True, env=env)
    
    conv_id = None
    if "data: " in result.stdout:
        for line in result.stdout.split("\n"):
            if "conversation_id" in line:
                try:
                    data = json.loads(line[6:])
                    conv_id = data.get("conversation_id")
                    if conv_id: break
                except: continue

    if not conv_id:
        print(f"未能获取会话ID。输出: {result.stdout}")
        return

    print(f"训练对话发送成功。会话ID: {conv_id}")
    
    # 等待后台记忆处理完成（提取三元组需要时间）
    print("等待 15 秒让后台处理记忆...")
    time.sleep(15)
    
    # 2. 检查图谱中是否出现了该项目
    print("\n--- 检查知识图谱 ---")
    graph_data = call_api("GET", "/memory/graph")
    
    if isinstance(graph_data, dict):
        nodes = graph_data.get("nodes", [])
        project_nodes = [n for n in nodes if "认知重构" in n.get("label", "")]
        
        if project_nodes:
            print(f"✅ 成功在图谱中找到节点: {project_nodes[0]['label']}")
        else:
            print("未能直接在图谱中找到匹配节点，尝试查看最近节点...")
            print(f"最近节点: {[n.get('label') for n in nodes[:10]]}")
    else:
        print(f"获取图谱数据失败: {graph_data}")

    # 3. 再次询问分身，看它是否记得
    print("\n--- 询问分身关于项目的记忆 ---")
    query_payload = {
        "message": "你还记得我刚才提到的新项目叫什么名字吗？它的进度如何？",
        "conversation_id": conv_id
    }
    
    full_response = call_api("POST", "/chat/send", query_payload)
    print(f"分身的回答: {full_response}")
    
    if "认知重构" in full_response:
        print("\n✅ 验证成功：分身成功记住了项目并能在对话中引用！")
    else:
        print("\n❌ 验证失败：分身似乎没能从记忆中提取到项目信息。")

if __name__ == "__main__":
    verify()
