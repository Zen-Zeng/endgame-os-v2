Endgame OS v2.0 - 详细技术架构规范

1. 技术栈清单 (Strict Stack)

Frontend (The Face):

React 18 (Vite)

TypeScript

Tailwind CSS + Shadcn/UI (组件库)

Zustand (状态管理)

React Markdown + Recharts

Backend (The Brain):

Python 3.11+

FastAPI (Web 框架)

LangGraph (Agent 编排)

KuzuDB (嵌入式图数据库)

ChromaDB (嵌入式向量数据库)

PyTorch + Transformers (本地 NLP)

Shell (The Body - Phase 2):

Tauri v2 (Rust)

2. 数据库 Schema 定义 (Database Schema)

2.1 KuzuDB (Graph Memory)

必须在 backend/app/core/graph_schema.py 中实现。

// 节点定义 (Nodes)
CREATE NODE TABLE User (name STRING, vision STRING, PRIMARY KEY (name));
CREATE NODE TABLE Goal (id STRING, title STRING, deadline DATE, status STRING, PRIMARY KEY (id));
CREATE NODE TABLE Project (id STRING, name STRING, sector STRING, PRIMARY KEY (id));
CREATE NODE TABLE Task (id STRING, title STRING, status STRING, PRIMARY KEY (id));
CREATE NODE TABLE Log (id STRING, content STRING, timestamp TIMESTAMP, type STRING, PRIMARY KEY (id));
CREATE NODE TABLE Concept (id STRING, name STRING, vector FLOAT[768], PRIMARY KEY (id));

// 关系定义 (Edges)
CREATE REL TABLE HAS_GOAL (FROM User TO Goal);
CREATE REL TABLE BELONGS_TO (FROM Project TO Goal);
CREATE REL TABLE BLOCKED_BY (FROM Task TO Task);
CREATE REL TABLE CONTRIBUTES_TO (FROM Log TO Project);
CREATE REL TABLE MENTIONS (FROM Log TO Concept);


2.2 ChromaDB (Vector Memory)

Collection Name: endgame_memory

Metadata: {"type": "chat|file", "timestamp": int, "h3_impact": str}

Embedding Model: sentence-transformers/all-MiniLM-L6-v2 (本地)

3. API 接口定义 (FastAPI)

3.1 核心对话接口

Endpoint: POST /api/v1/chat/completions

Request:

{
  "messages": [{"role": "user", "content": "..."}],
  "context": {
    "current_h3": {"mind": 80, ...},
    "active_file": "path/to/file.md"
  },
  "stream": true
}


Response (SSE Stream):

Event: token (文本流)

Event: tool_call (技能调用)

Event: memory_update (图谱更新通知)

3.2 记忆摄入接口

Endpoint: POST /api/v1/memory/ingest

Request:

{
  "content": "文件内容或文本片段",
  "source_type": "file_upload",
  "metadata": {"filename": "prd.md"}
}


Process:

Neural Processor 提取实体 (Entities) 和关系 (Triplets)。

写入 KuzuDB。

生成 Vector 写入 ChromaDB。

4. LangGraph 工作流 (The Reasoning Loop)

文件: backend/app/brain/workflow.py

State 定义:

class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    h3_state: dict
    next_step: str


Nodes (节点):

retrieve_memory: 根据用户输入查询 KuzuDB + Chroma。

architect_think: 核心 LLM 节点，基于 System Prompt 进行 CoT 思考。

check_alignment: (Conditional) 检查 LLM 生成的计划是否符合 5 年目标。

execute_tool: 如果需要，调用 Python Tools (日历/文件)。

Graph:
START -> retrieve_memory -> architect_think -> (if tool) -> execute_tool -> architect_think -> END

5. 项目目录结构

endgame-os/
├── brain/                  # Python Backend
│   ├── app/
│   │   ├── api/            # Routes
│   │   ├── core/           # Config, DB connection
│   │   ├── brain/          # LangGraph logic
│   │   ├── services/       # Neural processing, File watchers
│   │   └── tools/          # Anthropic style tools
│   ├── data/               # Local DB storage (gitignored)
│   └── main.py
├── face/                   # React Frontend
│   ├── src/
│   │   ├── components/     # UI Components
│   │   ├── hooks/          # API Hooks
│   │   └── stores/         # Zustand
│   └── index.html
└── body/                   # Tauri Shell (Phase 2)
