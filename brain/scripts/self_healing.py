import sqlite3
import json
import logging
from pathlib import Path
import sys

# Add parent directory to sys.path to import app modules
sys.path.append(str(Path(__file__).parent.parent.parent))

from brain.app.core.config import DATA_DIR

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def self_healing(user_id: str):
    db_path = DATA_DIR / "brain.db"
    if not db_path.exists():
        logger.error(f"Database not found at {db_path}")
        return

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        logger.info(f"Starting self-healing for user: {user_id}")

        # 1. Fix Vision Nodes
        cursor.execute("SELECT id, name, content, attributes FROM nodes WHERE user_id = ? AND type = 'Vision'", (user_id,))
        vision_nodes = cursor.fetchall()

        target_vision_id = f"vision_{user_id}"
        
        if len(vision_nodes) > 1 or (len(vision_nodes) == 1 and vision_nodes[0]['id'] != target_vision_id):
            logger.info(f"Merging {len(vision_nodes)} vision nodes into {target_vision_id}")
            
            merged_content = []
            merged_attributes = {}
            
            for vn in vision_nodes:
                if vn['content']: merged_content.append(vn['content'])
                if vn['attributes']:
                    try:
                        attrs = json.loads(vn['attributes'])
                        merged_attributes.update(attrs)
                    except: pass
            
            # Upsert the normalized Vision node
            cursor.execute("""
                INSERT OR REPLACE INTO nodes (id, user_id, type, name, content, status, attributes)
                VALUES (?, ?, 'Vision', ?, ?, 'confirmed', ?)
            """, (
                target_vision_id, 
                user_id, 
                vision_nodes[0]['name'] if vision_nodes else "My Vision",
                "\n".join(merged_content),
                json.dumps(merged_attributes)
            ))

            # Re-link edges
            for vn in vision_nodes:
                old_id = vn['id']
                if old_id == target_vision_id: continue
                
                # Update source of edges
                cursor.execute("UPDATE edges SET source = ? WHERE source = ? AND user_id = ?", (target_vision_id, old_id, user_id))
                # Update target of edges
                cursor.execute("UPDATE edges SET target = ? WHERE target = ? AND user_id = ?", (target_vision_id, old_id, user_id))
                
                # Delete old node
                cursor.execute("DELETE FROM nodes WHERE id = ?", (old_id,))

        # 2. Fix Self Node
        cursor.execute("SELECT id FROM nodes WHERE user_id = ? AND type = 'Self'", (user_id,))
        self_nodes = cursor.fetchall()
        
        if len(self_nodes) > 1 or (len(self_nodes) == 1 and self_nodes[0]['id'] != user_id):
            logger.info(f"Normalizing Self node ID to {user_id}")
            for sn in self_nodes:
                old_id = sn['id']
                if old_id == user_id: continue
                
                cursor.execute("UPDATE edges SET source = ? WHERE source = ? AND user_id = ?", (user_id, old_id, user_id))
                cursor.execute("UPDATE edges SET target = ? WHERE target = ? AND user_id = ?", (user_id, old_id, user_id))
                cursor.execute("DELETE FROM nodes WHERE id = ?", (old_id,))
            
            # Ensure Self node exists
            cursor.execute("INSERT OR IGNORE INTO nodes (id, user_id, type, name, content, status) VALUES (?, ?, 'Self', 'Self', 'The Owner', 'confirmed')", (user_id, user_id))

        # 3. Ensure Self -> OWNS -> Vision relation
        cursor.execute("INSERT OR IGNORE INTO edges (source, target, relation, user_id) VALUES (?, ?, 'OWNS', ?)", (user_id, target_vision_id, user_id))

        # 4. Fix Orphan Goals (not connected to Vision)
        cursor.execute("""
            SELECT id FROM nodes 
            WHERE user_id = ? AND type = 'Goal' 
            AND id NOT IN (SELECT target FROM edges WHERE source = ? AND relation = 'HAS_GOAL')
        """, (user_id, target_vision_id))
        orphan_goals = cursor.fetchall()
        for og in orphan_goals:
            logger.info(f"Linking orphan goal {og['id']} to vision")
            cursor.execute("INSERT OR IGNORE INTO edges (source, target, relation, user_id) VALUES (?, ?, 'HAS_GOAL', ?)", (target_vision_id, og['id'], user_id))

        conn.commit()
        logger.info("Self-healing completed successfully.")

    except Exception as e:
        conn.rollback()
        logger.error(f"Self-healing failed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    # Default user for testing, or take from args
    uid = sys.argv[1] if len(sys.argv) > 1 else "andornot"
    self_healing(uid)
