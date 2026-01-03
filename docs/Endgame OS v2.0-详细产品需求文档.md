Endgame OS v2.0 (Rebirth) - 详细产品需求文档

版本: v2.5.0 (Implementation Ready)
阶段: Phase 1 (Web MVP) & Phase 2 (Desktop Native)

1. 核心逻辑定义

1.1 数字人格 (The Architect)

定义: 一个基于 LLM 的 Agent，其 System Prompt 必须包含用户的“5年终局愿景”。

行为准则:

终局优先: 在回答任何问题前，先检索 KuzuDB 中的 Goal 节点，判断用户意图是否偏离。

H3 敏感: 回复的语气需根据用户当前的 H3 (Mind/Body/Spirit) 状态调整（例如：用户 Mind 低时，回复要简短直接）。

主动反问: 如果用户输入模糊，Architect 必须反问以澄清与目标的关联。

1.2 H3 能量系统 (The Bio-Engine)

四个维度:

Mind (心智): 专注力、认知负荷。输入来源：自评、任务复杂度。

Body (身体): 睡眠、运动、精力。输入来源：自评、(P2) Apple Health。

Spirit (精神): 意义感、情绪。输入来源：日记情感分析。

Vocation (事业): 产出效率、主线推进。输入来源：文件产出量、Task 完成度。

计算逻辑 (Phase 1):

用户通过滑块手动输入 0-100 的值。

系统记录历史数据，生成趋势图。

阈值报警: 任意数值 < 40% 触发前端红色警报。

2. 详细功能清单 (Feature List)

2.1 [P1] 晨间唤醒协议 (Morning Protocol)

入口: 每日首次访问 Web 端/打开 App。

流程:

问候: 显示距离 5 年目标的倒计时天数 (e.g., "Day 182/1825")。

昨夜回顾: 从 KuzuDB 读取昨日 Log 和 File 节点，生成 50 字摘要。

状态校准: 强制用户调整 H3 滑块。

今日任务生成: Architect 基于 Project 进度，推荐 3 个 Critical Task。

启动: 用户点击 "Start Day"，进入主控界面。

2.2 [P1] 深度对话与感知 (The Flow)

对话流:

支持 Markdown (代码高亮、表格)。

支持流式输出 (Streaming)。

支持 Action Chips (AI 生成的快捷按钮，如 "创建任务", "保存到笔记")。

记忆摄入 (Ingestion):

文件上传: 拖拽 PDF/MD 文件到聊天框 -> 解析 -> 存入 Vector/Graph。

文本粘贴: 自动识别 URL 并抓取内容 (需后端 Skill 支持)。

2.3 [P2] 神经链路 (Neural Link - Native)

屏幕感知:

后台进程每 60 秒截屏一次。

使用本地 OCR 提取文本。

关键词匹配：如果文本中包含 "YouTube/Bilibili" 且持续时间 > 30min -> 标记为 "Distraction"。

主动干预:

当 "Distraction" 事件触发，且 H3 Vocation < 50% 时 -> 发送系统级 Notification。

3. 商业/用户价值指标

Memory Density (记忆密度): 图谱中 (Log)-[RELATED_TO]->(Project) 的连边数量。

Alignment Score (对齐分): 每日行为与 5 年目标的语义相似度。