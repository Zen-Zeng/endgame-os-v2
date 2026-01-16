
import sys
import os
import json

# Add project root to sys.path
sys.path.append('/Users/andornot/endgame-os-v2/brain')

from app.services.memory.graph_store import GraphStore
from app.core.config import DATA_DIR

def test_graph_data():
    db_path = str(DATA_DIR / "brain.db")
    print(f"Using DB path: {db_path}")
    store = GraphStore(db_path=db_path)
    user_id = "user_bancozy"
    
    print(f"--- Strategic View for {user_id} ---")
    data = store.get_all_graph_data(user_id=user_id, view_type="strategic")
    
    nodes = data.get("nodes", [])
    links = data.get("links", [])
    
    print(f"Total nodes: {len(nodes)}")
    print(f"Total links: {len(links)}")
    
    type_counts = {}
    for node in nodes:
        t = node.get("type")
        type_counts[t] = type_counts.get(t, 0) + 1
    
    print("Node Type Counts in response:")
    for t, count in type_counts.items():
        print(f"  {t}: {count}")
    
    # Check for Goals and their connections
    goals = [n for n in nodes if n.get("type") == "Goal"]
    if goals:
        print(f"Found {len(goals)} Goals.")
        goal_ids = {g['id'] for g in goals}
        
        # Find links connected to goals
        goal_links = [l for l in links if l['source'] in goal_ids or l['target'] in goal_ids]
        print(f"Total links connected to goals: {len(goal_links)}")
        
        for l in goal_links[:5]:
            print(f"  Link: {l['source']} --({l['type']})--> {l['target']}")
    else:
        print("NO GOALS FOUND IN RESPONSE")

if __name__ == "__main__":
    test_graph_data()
