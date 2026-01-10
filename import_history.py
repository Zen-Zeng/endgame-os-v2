import json
import uuid
from datetime import datetime
from pathlib import Path

# 路径定义
DATA_DIR = Path("data")
UPLOADS_DIR = Path("brain/uploads")
HISTORY_FILE = UPLOADS_DIR / "yue_conversations.json"
CONVERSATIONS_FILE = DATA_DIR / "conversations.json"
MESSAGES_FILE = DATA_DIR / "messages.json"

USER_ID = "user_bancozy"

def import_chatgpt_history():
    if not HISTORY_FILE.exists():
        print(f"找不到历史文件: {HISTORY_FILE}")
        return

    print(f"正在处理历史文件: {HISTORY_FILE}")
    
    try:
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            history_data = json.load(f)
    except Exception as e:
        print(f"加载历史文件失败: {e}")
        return

    # 加载现有数据
    try:
        if CONVERSATIONS_FILE.exists():
            with open(CONVERSATIONS_FILE, 'r', encoding='utf-8') as f:
                conversations_db = json.load(f)
        else:
            conversations_db = {}
            
        if MESSAGES_FILE.exists():
            with open(MESSAGES_FILE, 'r', encoding='utf-8') as f:
                messages_db = json.load(f)
        else:
            messages_db = {}
    except:
        conversations_db = {}
        messages_db = {}

    import_count = 0
    msg_count = 0

    for chat in history_data:
        title = chat.get("title") or "历史对话"
        create_time = chat.get("create_time")
        update_time = chat.get("update_time")
        
        # 转换时间戳
        created_at = datetime.fromtimestamp(create_time).isoformat() if create_time else datetime.now().isoformat()
        updated_at = datetime.fromtimestamp(update_time).isoformat() if update_time else created_at
        
        conv_id = f"hist_{uuid.uuid4().hex[:8]}"
        
        # 提取消息
        messages = []
        mapping = chat.get("mapping", {})
        
        # ChatGPT 格式是树状的，这里简单扁平化处理
        for node_id, node in mapping.items():
            msg_obj = node.get("message")
            if not msg_obj:
                continue
                
            author = msg_obj.get("author", {})
            role = author.get("role")
            
            # 只提取 user 和 assistant 消息
            if role not in ["user", "assistant"]:
                continue
                
            content_obj = msg_obj.get("content", {})
            parts = content_obj.get("parts", [])
            content = "".join([p for p in parts if isinstance(p, str)])
            
            if not content.strip():
                continue
                
            msg_create_time = msg_obj.get("create_time")
            msg_created_at = datetime.fromtimestamp(msg_create_time).isoformat() if msg_create_time else created_at
            
            messages.append({
                "id": f"msg_{uuid.uuid4().hex[:8]}",
                "conversation_id": conv_id,
                "role": role,
                "content": content,
                "created_at": msg_created_at
            })

        if not messages:
            continue

        # 按时间排序消息
        messages.sort(key=lambda x: x["created_at"])
        
        # 存入数据库
        conversations_db[conv_id] = {
            "id": conv_id,
            "user_id": USER_ID,
            "title": title,
            "created_at": created_at,
            "updated_at": updated_at,
            "message_count": len(messages)
        }
        messages_db[conv_id] = messages
        
        import_count += 1
        msg_count += len(messages)

    # 保存合并后的数据
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONVERSATIONS_FILE, 'w', encoding='utf-8') as f:
        json.dump(conversations_db, f, ensure_ascii=False, indent=2)
    with open(MESSAGES_FILE, 'w', encoding='utf-8') as f:
        json.dump(messages_db, f, ensure_ascii=False, indent=2)

    print(f"成功导入 {import_count} 个会话，共 {msg_count} 条消息。")
    print(f"数据已同步至 {CONVERSATIONS_FILE}")

if __name__ == "__main__":
    import_chatgpt_history()
