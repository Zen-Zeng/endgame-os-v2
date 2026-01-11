from app.services.memory.graph_store import GraphStore
import json

def test_query():
    store = GraphStore()
    user_id = "user_bancozy"
    
    print(f"Querying for user: {user_id}")
    data = store.get_all_graph_data(user_id)
    
    nodes = data.get("nodes", [])
    links = data.get("links", [])
    
    print(f"Nodes found: {len(nodes)}")
    for n in nodes:
        if n['type'] in ['Self', 'Vision', 'Goal', 'Project']:
            print(f" - {n['type']}: {n['label']} ({n['id']})")
            
    print(f"Links found: {len(links)}")
    for l in links:
        print(f" - {l['source']} -> {l['type']} -> {l['target']}")

if __name__ == "__main__":
    test_query()
