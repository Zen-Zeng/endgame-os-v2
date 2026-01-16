import os
import json
import asyncio
import logging
import uuid
from pathlib import Path
from typing import List, Dict, Any
from openai import AsyncOpenAI
from dotenv import load_dotenv

# App imports
from app.services.memory.graph_store import GraphStore
from app.services.memory.vector_store import VectorStore
from app.services.neural import get_processor
from app.core.utils import extract_json
from app.core.config import DATA_DIR, MODEL_CONFIG

# Logging setup
logger = logging.getLogger("ETL")

class ETLPipeline:
    def __init__(self, clear_existing: bool = False):
        self.client = AsyncOpenAI(
            api_key=MODEL_CONFIG.get("deepseek_api_key"), 
            base_url=MODEL_CONFIG.get("deepseek_base_url", "https://api.deepseek.com")
        )
        self.graph_store = GraphStore(db_path=str(DATA_DIR / "brain.db"))
        self.vector_store = VectorStore(persist_directory=str(DATA_DIR / "chroma"))
        self.processor = get_processor()
        self.clear_existing = clear_existing

    async def run(self, file_path: str, vision_content: str = "", identity_instruction: str = ""):
        """Main ETL Flow v3.0 (Memory Airlock)"""
        if self.clear_existing:
            self._clear_data()

        # 1. Read
        logger.info(f"Phase 1: Reading from {file_path}...")
        text = self._read_file(file_path)
        if not text:
            logger.error("File is empty or not found.")
            return

        # 2. Extract (Map)
        logger.info("Phase 2: Extracting entities via DeepSeek (Map)...")
        chunks = self._chunk_text(text, chunk_size=32000)
        logger.info(f"Split into {len(chunks)} chunks.")

        tasks = [self._process_chunk(chunk, i, vision_content, identity_instruction) for i, chunk in enumerate(chunks)]
        chunk_results = await asyncio.gather(*tasks)

        # 3. Consolidate (Reduce)
        logger.info("Phase 3: Consolidating and Aligning Entities (Reduce)...")
        consolidated_data = await self._consolidate_results(chunk_results, vision_content, identity_instruction)

        # 4. Load into Staging (Airlock)
        logger.info("Phase 4: Loading into Memory Airlock (Staging)...")
        success = self.graph_store.add_to_staging(
            user_id="user_bancozy", 
            nodes=consolidated_data.get("nodes", []),
            edges=consolidated_data.get("edges", []),
            source_file=file_path
        )
        
        if success:
            logger.info(f"ETL Complete. {len(consolidated_data.get('nodes', []))} nodes added to staging.")
            logger.info("请前往图谱校准页面进行人工确认和合并。")
        else:
            logger.error("Failed to load data into staging.")

    def _clear_data(self):
        """Wipe existing data for a fresh start"""
        logger.warning("Clearing existing Graph and Vector data...")
        self.graph_store.clear_all_data("user_bancozy")
        self.graph_store.clear_staging("user_bancozy")
        
        try:
            self.vector_store.client.reset()
            self.vector_store._initialize_client()
        except Exception as e:
            logger.error(f"Failed to reset Chroma: {e}")

    def _read_file(self, path: str) -> str:
        try:
            p = Path(path)
            if p.suffix.lower() == '.json':
                return self._parse_json_export(path)
            
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Read error: {e}")
            return ""

    def _parse_json_export(self, path: str) -> str:
        """Parse ChatGPT export JSON into linear text"""
        text_buffer = []
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if isinstance(data, list):
                for conv in data:
                    title = conv.get("title", "Unknown Conversation")
                    text_buffer.append(f"\n\n=== Conversation: {title} ===\n")
                    mapping = conv.get("mapping", {})
                    for key, val in mapping.items():
                        message = val.get("message")
                        if message and message.get("content"):
                            parts = message["content"].get("parts", [])
                            role = message["author"]["role"]
                            content = " ".join([str(p) for p in parts if isinstance(p, str)])
                            if content:
                                text_buffer.append(f"[{role}]: {content}")
            return "\n".join(text_buffer)
        except Exception as e:
            logger.error(f"JSON Parse Error: {e}")
            return ""

    def _chunk_text(self, text: str, chunk_size: int) -> List[str]:
        return [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]

    async def _process_chunk(self, chunk: str, index: int, vision: str, identity: str) -> Dict[str, Any]:
        """Call DeepSeek to structure a single chunk"""
        system_prompt = f"""你是一个高级战略分析师和情报专家，正在为用户的个人操作系统 (Endgame OS) 提取核心情报。

### 1. 核心上下文 (Context)
【我的身份/数字人格指令】: {identity}
【终局愿景 (5年愿景)】: {vision}

### 2. 提取准则 (Extraction Principles)
你必须严格按照以下“事之网”和“人之网”逻辑提取核心实体。**丢弃所有闲聊、琐碎细节、无意义的口水话。**

#### A. 事之网 (Strategic Tasks) - 五层逻辑
- **Vision**: 最高层级的终局愿景（通常只有1个，即上述提供的愿景）。
- **Goal**: 支撑愿景的战略目标（大型里程碑，如“完成A轮融资”）。
- **Project**: 正在执行的战役或项目（如“Endgame OS 开发”）。
- **Task**: 具有明确行动意义的关键任务（如“重构图谱存储模块”）。
- **Insight**: 从中总结出的核心洞察、原则或教训（具有跨项目复用价值）。

#### B. 人之网 (Social Identity) - 身份核心
- **Person**: 关键人物。必须提取具体的人名（如“小熊”、“张熊仪”）。
  *   **注意**：识别并关联绰号、职位（如“老叶”、“叶老师” -> “叶楠”）。
- **Organization**: 组织、团队、公司（如“椒阳团队”、“阿里巴巴”）。

### 3. 关系逻辑 (Relationship Schema) - 必须遵循
- Vision -> DECOMPOSES_TO -> Goal
- Goal -> ACHIEVED_BY -> Project
- Project -> HAS_TASK -> Task
- Task -> GENERATES -> Insight
- **Self -> PARTNERS_WITH -> Person** (Self 代表用户本人，仅与具体的人建立直接战略连接)
- **Person -> BELONGS_TO -> Organization** (人属于组织，而非 Self 直接连接组织)
- Person/Organization -> SUPPORTS -> Project/Goal
- Project/Task -> INVOLVES -> Person

### 4. 关键要求 (Critical Requirements)
- **战略过滤**: 仅提取与“终局愿景”直接或间接相关的实体。忽略琐碎的社交（如：一起吃了个饭，但没聊正事）。
- **实体对齐预判**: 在当前文本块内，如果“小熊”和“张熊仪”指代同一人，请统一使用正式全名。
- **属性丰富**: 在 content 字段中简要描述实体的核心价值、能力标签或项目职责。

### 5. 输出格式 (Output Format - JSON)
{{
  "nodes": [
    {{ "name": "实体名称", "type": "Vision|Goal|Project|Task|Insight|Person|Organization", "content": "核心描述/职责" }}
  ],
  "edges": [
    {{ "source_name": "源节点名称", "target_name": "目标节点名称", "relation": "关系类型" }}
  ]
}}
"""
        try:
            response = await self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"请处理以下文本块并提取战略实体:\n\n{chunk}"}
                ],
                response_format={"type": "json_object"},
                temperature=0.1
            )
            content = response.choices[0].message.content
            return extract_json(content)
        except Exception as e:
            logger.error(f"Chunk {index} failed: {e}")
            return {"nodes": [], "edges": []}

    async def _consolidate_results(self, results: List[Dict[str, Any]], vision: str, identity: str) -> Dict[str, Any]:
        """合并所有分块结果，执行语义聚类、去重与战略对齐"""
        all_nodes = []
        all_edges = []
        
        for r in results:
            all_nodes.extend(r.get("nodes", []))
            all_edges.extend(r.get("edges", []))
            
        if not all_nodes:
            return {"nodes": [], "edges": []}

        # 准备节点摘要进行聚类
        node_summaries = []
        seen_summaries = set()
        for n in all_nodes:
            summary_key = f"{n['name']}|{n['type']}"
            if summary_key not in seen_summaries:
                node_summaries.append({
                    "name": n["name"],
                    "type": n["type"],
                    "content": n.get("content", "")
                })
                seen_summaries.add(summary_key)
        
        consolidation_prompt = f"""你是一个高级数据架构师和实体对齐专家。
以下是从多个文本块中提取的初步实体列表。由于分块提取，存在大量重复和语义重叠。

【核心上下文】
【数字人格/我的身份】: {identity}
【终局愿景】: {vision}

任务：
1. **语义聚类与合并 (Semantic Consolidation)**:
   - **Person 节点 (强制合并)**: 将昵称、职位+姓氏、全名合并。例如：“小熊” + “张熊仪” -> “张熊仪”；“老叶” + “叶楠” -> “叶楠”。
   - **Organization 节点 (强制合并)**: 将缩写、简称与全称合并。例如：“阿里” + “阿里巴巴” -> “阿里巴巴”。
   - **战略节点 (Goal/Project/Task)**: 相似描述的任务应合并为同一个标准节点。

2. **标准名称选取**: 
   - 优先选择最正式、完整、不带冗余修饰的名称作为“标准名称”。

3. **战略过滤 (Strategic Pruning)**:
   - 移除与“终局愿景”无关的杂讯节点。
   - 移除描述过于笼统、缺乏行动价值的节点。

4. **信息融合**: 
   - 将同一实体的多个描述段落融合为一段精炼的 core_description。

### 输出格式 (JSON) - 必须严格遵循:
{{
  "mapping": {{ "原始名称": "标准名称" }},
  "standard_nodes": [
    {{ "name": "标准名称", "type": "Vision|Goal|Project|Task|Insight|Person|Organization", "content": "融合后的精炼描述" }}
  ]
}}
"""
        try:
            # 考虑节点数量，如果过多可能需要分批。此处假设 node_summaries 在合理范围内。
            response = await self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": consolidation_prompt},
                    {"role": "user", "content": f"待合并实体列表: {json.dumps(node_summaries, ensure_ascii=False)}"}
                ],
                response_format={"type": "json_object"},
                temperature=0.1
            )
            consolidation_res = json.loads(response.choices[0].message.content)
            
            mapping = consolidation_res.get("mapping", {})
            standard_nodes_list = consolidation_res.get("standard_nodes", [])
            
            # 建立映射和最终节点列表
            final_nodes = []
            name_to_id = {}
            
            for sn in standard_nodes_list:
                node_id = str(uuid.uuid4())
                name_to_id[sn["name"]] = node_id
                final_nodes.append({
                    "id": node_id,
                    "name": sn["name"],
                    "type": sn["type"],
                    "content": sn.get("content", "")
                })
                
            # 处理边：应用映射并去重
            final_edges = []
            edge_signatures = set()
            
            for e in all_edges:
                # 映射源和目标名称
                src_name = mapping.get(e["source_name"], e["source_name"])
                tgt_name = mapping.get(e["target_name"], e["target_name"])
                
                # 特殊处理：如果 source 或 target 是 "Self" 或 "我"，统一映射到 Self 节点（由后端后续处理）
                if src_name in ["Self", "我", "本人", "本人身份", "主人", "我的"]: src_name = "Self"
                if tgt_name in ["Self", "我", "本人", "本人身份", "主人", "我的"]: tgt_name = "Self"

                src_id = name_to_id.get(src_name)
                tgt_id = name_to_id.get(tgt_name)
                
                # 如果是 Self 节点，后端 add_to_staging 会处理，这里我们保留名称或赋予特殊 ID
                if src_name == "Self": src_id = "SELF_NODE_ID"
                if tgt_name == "Self": tgt_id = "SELF_NODE_ID"

                if src_id and tgt_id and src_id != tgt_id:
                    sig = f"{src_id}-{e['relation']}-{tgt_id}"
                    if sig not in edge_signatures:
                        final_edges.append({
                            "source": src_id,
                            "target": tgt_id,
                            "relation": e["relation"]
                        })
                        edge_signatures.add(sig)
                        
            return {"nodes": final_nodes, "edges": final_edges}
            
        except Exception as e:
            logger.error(f"Consolidation failed: {e}")
            # Fallback: simple deduplication by name
            logger.warning("Falling back to simple deduplication.")
            unique_nodes = {}
            for n in all_nodes:
                unique_nodes[n["name"]] = n
            
            final_nodes = []
            name_to_id = {}
            for name, n in unique_nodes.items():
                nid = str(uuid.uuid4())
                name_to_id[name] = nid
                final_nodes.append({**n, "id": nid})
                
            final_edges = []
            for e in all_edges:
                sid = name_to_id.get(e["source_name"])
                tid = name_to_id.get(e["target_name"])
                if sid and tid:
                    final_edges.append({"source": sid, "target": tid, "relation": e["relation"]})
            return {"nodes": final_nodes, "edges": final_edges}

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("file", help="Path to input file")
    parser.add_argument("--vision", help="Path to Vision Canvas file")
    parser.add_argument("--identity", help="Identity Instruction")
    parser.add_argument("--clear", action="store_true", help="Clear existing data")
    args = parser.parse_args()

    vision_content = ""
    if args.vision:
        try:
            with open(args.vision, 'r', encoding='utf-8') as f:
                vision_content = f.read()
        except Exception as e:
            logger.error(f"Failed to read vision file: {e}")
    
    if not vision_content:
        vision_content = "未设定明确愿景"

    identity = args.identity or "Endgame OS 核心用户"

    etl = ETLPipeline(clear_existing=args.clear)
    asyncio.run(etl.run(args.file, vision_content, identity))
