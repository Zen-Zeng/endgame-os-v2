# Endgame OS 记忆图谱优化方案 (Memory Optimization Plan)

## 1. 核心哲学：人优先于事 (People Over Things)
在 Endgame OS 中，记忆不仅仅是数据的堆叠，而是为了实现“社交觉醒”和“战略定位”。
- **人是原点**：所有的项目和任务最终由人驱动。
- **能量建模**：识别人脉中的“价值贡献者”与“能量消耗者”。
- **战略树状结构**：事之网必须严格遵循 `Vision -> Goal -> Project -> Task` 的树状归属。

---

## 2. 阶段一：存量清洗 (Stock Cleaning)
解决当前数据重复、ID 不统一、归一化程度低的问题。

### 2.1 ID 归一化与强一致性
- **Self 节点**：ID 强制固定为 `{user_id}`。
- **Vision 节点**：ID 强制固定为 `vision_{user_id}`。
- **Goal/Project/Task**：基于名称和所属层级的确定性 ID 生成。

### 2.2 存量数据自愈逻辑 (Self-Healing)
- **重复合并**：扫描数据库中类型相同、名称相似（模糊匹配）的节点进行合并。
- **孤儿节点处理**：
  - 找不到 Vision 的 Goal 自动挂载到默认 Vision。
  - 找不到 Project 的 Task 自动归类为 "Inbox" 任务。

---

## 3. 阶段二：增量优化 (Incremental Optimization)
优化数据提取（Ingestion）过程，实现“战略定位”。

### 3.1 战略定位 (Strategic Positioning)
在 LLM 提取新记忆时，注入当前的战略上下文：
- **Context Injection**：将当前的 Vision 和活跃 Goals 作为 System Prompt 的一部分。
- **层级断言**：提取出的新实体必须显式声明其在 `Strategic Tree` 中的位置。

### 3.2 人之网能量建模 (Energy Modeling)
- **情绪反馈提取**：从用户与分身的聊天记录中，提取对特定人员的“主观感受”（感受、疲劳度、兴奋度）。
- **Energy Impact 评分**：
  - `+1 到 +5`：赋能型人脉。
  - `-1 到 -5`：消耗型人脉。
- **协作网络可视化**：人之网不仅展示连接，还展示“连接的粗细”和“节点的亮度”（基于能量影响）。

---

## 4. 阶段三：性能优化 (Performance Optimization)
解决 70+ 节点导致的卡顿，支持千级节点的流畅交互。

### 4.1 前端渲染引擎重构 (PIXI.js LOD)
- **Level of Detail (LOD)**：
  - `Scale < 0.4`：仅渲染圆点，隐藏文字和复杂阴影。
  - `Scale > 0.8`：显示精细标签和边框。
- **Viewport Culling**：只计算和渲染视口内的节点。
- **Web Worker Layout**：将 Force-Directed Layout 的计算从主线程移至 Web Worker，避免 UI 阻塞。

### 4.2 后端查询优化
- **分页加载与按需加载**：初始只加载 `Strategic View` (核心骨架)，点击节点后再展开其关联的详细子节点。
- **图数据缓存**：对频繁访问的视图结果进行 Redis/内存缓存。

---

## 5. 执行计划 (Execution Timeline)
1. **[Day 1] 基础加固**：完成 ID 归一化和默认节点自动创建（已开始）。
2. **[Day 2] 前端加速**：实施 LOD 渲染和 PIXI 性能调优。
3. **[Day 3] 战略定位**：重写 Ingestion Prompt，实现自动归属逻辑。
4. **[Day 4] 存量自愈**：编写并运行一次性数据清洗脚本。
5. **[Day 5] 能量建模**：上线人之网能量分析功能。
