Endgame OS 完整组件原型规范

设计系统: Tailwind CSS
图标库: Lucide React

1. 主布局 (LayoutShell.tsx)

结构: h-screen w-screen bg-slate-950 text-slate-50 flex flex-col

背景: 使用 CSS Mesh Gradient 动态展示当前 H3 能量的主色调。

2. 晨间唤醒组件 (MorningBriefing.tsx)

2.1 倒计时标头

UI: 居中大字，字体 font-mono。

Data: const daysLeft = targetDate - currentDate。

2.2 H3 校准器

UI: 4 个垂直排列的 Slider 组。

Code:

<div className="flex items-center gap-4">
  <span className="text-blue-400 w-12">MIND</span>
  <Slider 
    value={[mindScore]} 
    onValueChange={updateStore} 
    className="flex-1"
    max={100}
  />
  <span className="font-bold">{mindScore}%</span>
</div>


2.3 启动按钮

交互: 只有当所有 4 个维度都确认后，按钮才从 disabled 变为 active。

动画: 点击后，界面使用 Framer Motion 执行 AnimatePresence 退出，主聊天界面滑入。

3. 主控聊天界面 (ChatInterface.tsx)

3.1 消息气泡 (MessageBubble)

User: bg-slate-700/50 rounded-2xl rounded-tr-sm ml-auto max-w-[80%].

Architect: bg-transparent text-slate-200 w-full text-left.

Thinking State: 当 AI 思考时，显示脉冲动画 animate-pulse text-slate-500 "Architect is analyzing memory..."。

3.2 技能调用展示 (ToolCallBlock)

如果 Architect 调用了 check_calendar，UI 不应只显示结果，应显示过程：

[ 🗓️ Checking Calendar... ] (Loading spinner)
-> Found 2 events.


样式: text-xs font-mono text-green-400 bg-slate-900/50 p-2 rounded border border-green-900/50.

3.3 输入区域 (InputArea)

组件: TextareaAutosize (from libraries)。

功能栏:

UploadButton: 触发文件选择。

GraphToggle: 切换右侧侧边栏显示“实时记忆图谱”。

4. 记忆图谱仪表盘 (GraphDashboard.tsx)

4.1 3D 力导向图

库: react-force-graph-3d 或 plotly.js。

数据映射:

Node Color: Project(Blue), Goal(Gold), Log(Gray).

Node Size: 基于 degree (连接数) 或 importance。

交互: 点击节点 -> 打开侧滑面板 (NodeDetailsPanel)，显示该节点相关的具体对话记录。

5. 状态管理 (Zustand Stores)

useH3Store

interface H3State {
  scores: { mind: number, body: number, spirit: number, vocation: number };
  history: H3Log[];
  setScore: (type: string, val: number) => void;
  analysis: string; // Architect 的评价
}


useChatStore

interface ChatState {
  messages: Message[];
  isStreaming: boolean;
  activeContextFiles: string[]; // 当前拖入的文件
  sendMessage: (text: string) => Promise<void>;
}
