import sqlite3
import json
import uuid

DB_PATH = "brain/data/brain.db"

def inject_test_data():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. 直接指定用户
    user_id = "user_bancozy"
    print(f"User ID: {user_id}")
    
    # 2. 检查 Self 节点
    cursor.execute("SELECT id FROM nodes WHERE type='Self' AND user_id=?", (user_id,))
    self_node = cursor.fetchone()
    if not self_node:
        print("Self 节点不存在，正在创建...")
        cursor.execute("INSERT INTO nodes (id, user_id, type, name, status) VALUES (?, ?, 'Self', 'Me', 'confirmed')", (user_id, user_id))
        self_node_id = user_id
    else:
        self_node_id = self_node[0]
        
    # 3. 插入 Vision
    vision_id = f"vision_{uuid.uuid4().hex[:8]}"
    cursor.execute("INSERT INTO nodes (id, user_id, type, name, status) VALUES (?, ?, 'Vision', '成为全栈架构师', 'confirmed')", (vision_id, user_id))
    cursor.execute("INSERT INTO edges (source, target, relation, user_id) VALUES (?, ?, 'OWNS', ?)", (self_node_id, vision_id, user_id))
    
    # 4. 插入 Goal
    goal_id = f"goal_{uuid.uuid4().hex[:8]}"
    cursor.execute("INSERT INTO nodes (id, user_id, type, name, status) VALUES (?, ?, 'Goal', '掌握 Rust 和 WebAssembly', 'confirmed')", (goal_id, user_id))
    cursor.execute("INSERT INTO edges (source, target, relation, user_id) VALUES (?, ?, 'DECOMPOSES_TO', ?)", (vision_id, goal_id, user_id))
    
    # 5. 插入 Project
    project_id = f"proj_{uuid.uuid4().hex[:8]}"
    cursor.execute("INSERT INTO nodes (id, user_id, type, name, status) VALUES (?, ?, 'Project', 'Endgame OS 重构', 'confirmed')", (project_id, user_id))
    cursor.execute("INSERT INTO edges (source, target, relation, user_id) VALUES (?, ?, 'ACHIEVED_BY', ?)", (goal_id, project_id, user_id))
    
    conn.commit()
    print("测试数据注入完成！请刷新页面。")
    conn.close()

if __name__ == "__main__":
    inject_test_data()
