import { useState, useEffect } from 'react';
import { 
  X, Target, Briefcase, CheckCircle2, Circle, 
  ChevronRight, ChevronDown, Clock, Loader2,
  Plus, MoreVertical, Link as LinkIcon
} from 'lucide-react';
import { api } from '../../lib/api';
import clsx from 'clsx';

interface Task {
  id: string;
  name: string;
  type: string;
  content: string;
  dossier: {
    status: string;
    priority: string;
    progress: number;
    created_at: string;
  };
}

interface Project {
  id: string;
  name: string;
  type: string;
  content: string;
  tasks_count: number;
  tasks?: Task[];
  dossier: {
    status: string;
    sector?: string;
    progress: number;
    created_at: string;
  };
}

interface Goal {
  id: string;
  name: string;
  type: string;
  content: string;
  projects_count: number;
  projects?: Project[];
  dossier: {
    status: string;
    deadline?: string;
    priority: string;
    progress: number;
    created_at: string;
  };
}

interface GoalDetailModalProps {
  isOpen: boolean;
  onClose: () => void;
  goal: Goal | null;
}

export default function GoalDetailModal({ isOpen, onClose, goal }: GoalDetailModalProps) {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(false);
  const [expandedProjects, setExpandedProjects] = useState<Record<string, boolean>>({});
  const [projectTasks, setProjectTasks] = useState<Record<string, Task[]>>({});
  const [tasksLoading, setTasksLoading] = useState<Record<string, boolean>>({});
  
  // 新增：创建状态
  const [isCreatingProject, setIsCreatingProject] = useState(false);
  const [newProjectName, setNewProjectName] = useState('');
  const [isCreatingTask, setIsCreatingTask] = useState<string | null>(null);
  const [newTaskName, setNewTaskName] = useState('');

  // 新增：关联已有项目状态
  const [isLinkingProject, setIsLinkingProject] = useState(false);
  const [availableProjects, setAvailableProjects] = useState<Project[]>([]);
  const [linkingLoading, setLinkingLoading] = useState(false);

  useEffect(() => {
    if (isOpen && goal) {
      fetchProjects();
    } else {
      setProjects([]);
      setExpandedProjects({});
      setProjectTasks({});
      setIsLinkingProject(false);
    }
  }, [isOpen, goal]);

  const fetchAvailableProjects = async () => {
    try {
      setLinkingLoading(true);
      // 获取所有项目节点
      const allProjects = await api.get<any[]>('/memory/nodes?type=Project');
      
      // 过滤掉已经关联的项目
      const currentProjectIds = new Set(projects.map(p => p.id));
      const filtered = allProjects.filter(p => !currentProjectIds.has(p.id));
      
      setAvailableProjects(filtered.map(p => ({
        id: p.id,
        name: p.label || p.name,
        type: 'Project',
        content: p.content,
        tasks_count: 0,
        dossier: { status: 'active', progress: 0, created_at: new Date().toISOString() }
      })));
    } catch (e) {
      console.error('Fetch available projects error', e);
    } finally {
      setLinkingLoading(false);
    }
  };

  const handleLinkProject = async (projectId: string) => {
    if (!goal) return;
    try {
      await api.post('/memory/edges', {
        source: projectId,
        target: goal.id,
        relation: 'BELONGS_TO'
      });
      setIsLinkingProject(false);
      fetchProjects(); // 重新加载关联项目
    } catch (e) {
      console.error('Link project error', e);
      alert('关联失败');
    }
  };

  useEffect(() => {
    if (isLinkingProject) {
      fetchAvailableProjects();
    }
  }, [isLinkingProject]);

  const fetchProjects = async () => {
    if (!goal) return;
    try {
      setLoading(true);
      const data = await api.get<Project[]>(`/goals/${goal.id}/projects`);
      setProjects(data || []);
    } catch (e) {
      console.error('Fetch projects error', e);
    } finally {
      setLoading(false);
    }
  };

  const fetchTasks = async (projectId: string) => {
    try {
      setTasksLoading(prev => ({ ...prev, [projectId]: true }));
      const data = await api.get<Task[]>(`/goals/projects/${projectId}/tasks`);
      setProjectTasks(prev => ({ ...prev, [projectId]: data || [] }));
    } catch (e) {
      console.error('Fetch tasks error', e);
    } finally {
      setTasksLoading(prev => ({ ...prev, [projectId]: false }));
    }
  };

  const toggleProject = (projectId: string) => {
    const isExpanded = !expandedProjects[projectId];
    setExpandedProjects(prev => ({ ...prev, [projectId]: isExpanded }));
    
    if (isExpanded && !projectTasks[projectId]) {
      fetchTasks(projectId);
    }
  };

  const handleCreateProject = async () => {
    if (!goal || !newProjectName.trim()) return;
    try {
      const data = await api.post<Project>('/goals/projects/create', {
        goal_id: goal.id,
        name: newProjectName.trim(),
        content: ""
      });
      if (data) {
        setProjects(prev => [...prev, data]);
        setNewProjectName('');
        setIsCreatingProject(false);
      }
    } catch (e) {
      console.error('Create project error', e);
    }
  };

  const handleCreateTask = async (projectId: string) => {
    if (!newTaskName.trim()) return;
    try {
      const data = await api.post<Task>('/goals/tasks/create', {
        project_id: projectId,
        name: newTaskName.trim(),
        content: "",
        priority: "medium"
      });
      if (data) {
        setProjectTasks(prev => ({
          ...prev,
          [projectId]: [...(prev[projectId] || []), data]
        }));
        setNewTaskName('');
        setIsCreatingTask(null);
        
        // 更新项目的任务计数
        setProjects(prev => prev.map(p => 
          p.id === projectId ? { ...p, tasks_count: (p.tasks_count || 0) + 1 } : p
        ));
      }
    } catch (e) {
      console.error('Create task error', e);
    }
  };

  if (!isOpen || !goal) return null;

  return (
    <div className="fixed inset-0 z-[110] flex items-center justify-center p-4">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />
      
      {/* Modal Content */}
      <div className="relative w-full max-w-2xl max-h-[90vh] bg-[var(--md-sys-color-surface)] rounded-[32px] shadow-2xl border border-[var(--md-sys-color-outline-variant)] overflow-hidden flex flex-col animate-in fade-in zoom-in duration-200">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-[var(--md-sys-color-outline-variant)] bg-[var(--md-sys-color-surface-container-low)]">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-2xl bg-[var(--md-sys-color-primary-container)] flex items-center justify-center text-[var(--md-sys-color-primary)]">
              <Target size={24} />
            </div>
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className="text-[10px] font-black uppercase px-2 py-0.5 bg-[var(--md-sys-color-secondary-container)] text-[var(--md-sys-color-on-secondary-container)] rounded-full">
                  {goal.dossier.priority}
                </span>
                <span className="text-[10px] font-black uppercase px-2 py-0.5 bg-[var(--md-sys-color-tertiary-container)] text-[var(--md-sys-color-on-tertiary-container)] rounded-full">
                  {goal.dossier.status}
                </span>
              </div>
              <h3 className="text-xl font-black">{goal.name}</h3>
            </div>
          </div>
          <button 
            onClick={onClose}
            className="p-2 rounded-full hover:bg-[var(--md-sys-color-surface-variant)] transition-colors"
          >
            <X size={20} />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-8">
          {/* Description */}
          <section>
            <h4 className="text-xs font-black uppercase tracking-widest opacity-50 mb-3 ml-1">愿景描述 / VISION</h4>
            <p className="text-sm leading-relaxed text-[var(--md-sys-color-on-surface-variant)] bg-[var(--md-sys-color-surface-container-lowest)] p-4 rounded-2xl border border-[var(--md-sys-color-outline-variant)]">
              {goal.content || "未定义详细愿景内容..."}
            </p>
          </section>

          {/* Progress */}
          <section className="bg-[var(--md-sys-color-primary-container)]/30 p-6 rounded-[24px]">
            <div className="flex justify-between items-end mb-3">
              <div>
                <h4 className="text-xs font-black uppercase tracking-widest opacity-50 mb-1">推进进度 / PROGRESS</h4>
                <div className="text-2xl font-black text-[var(--md-sys-color-primary)]">{goal.dossier.progress}%</div>
              </div>
              {goal.dossier.deadline && (
                <div className="text-right">
                  <h4 className="text-xs font-black uppercase tracking-widest opacity-50 mb-1">目标期限 / DEADLINE</h4>
                  <div className="text-sm font-bold flex items-center gap-1">
                    <Clock size={14} />
                    {new Date(goal.dossier.deadline).toLocaleDateString()}
                  </div>
                </div>
              )}
            </div>
            <div className="h-3 bg-[var(--md-sys-color-surface-container-highest)] rounded-full overflow-hidden">
              <div 
                className="h-full bg-[var(--md-sys-color-primary)] transition-all duration-500" 
                style={{ width: `${goal.dossier.progress}%` }} 
              />
            </div>
          </section>

          {/* Projects Hierarchy */}
          <section>
            <div className="flex items-center justify-between mb-4">
              <h4 className="text-xs font-black uppercase tracking-widest opacity-50 ml-1">关联项目与任务 / PROJECTS & TASKS</h4>
              <div className="flex items-center gap-4">
                {!isLinkingProject && !isCreatingProject && (
                  <button 
                    onClick={() => setIsLinkingProject(true)}
                    className="flex items-center gap-1 text-[10px] font-black uppercase text-[var(--md-sys-color-secondary)] hover:underline"
                  >
                    <LinkIcon size={14} /> 关联已有项目
                  </button>
                )}
                {!isCreatingProject && !isLinkingProject && (
                  <button 
                    onClick={() => setIsCreatingProject(true)}
                    className="flex items-center gap-1 text-[10px] font-black uppercase text-[var(--md-sys-color-primary)] hover:underline"
                  >
                    <Plus size={14} /> 新增项目
                  </button>
                )}
              </div>
            </div>

            {isLinkingProject && (
              <div className="mb-4 p-4 border-2 border-dashed border-[var(--md-sys-color-secondary)] rounded-2xl bg-[var(--md-sys-color-secondary-container)]/10 animate-in slide-in-from-top-2">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-[10px] font-black uppercase text-[var(--md-sys-color-secondary)]">选择要关联的已有项目</span>
                  <button 
                    onClick={() => setIsLinkingProject(false)}
                    className="text-[10px] font-black uppercase text-[var(--md-sys-color-outline)]"
                  >
                    取消
                  </button>
                </div>
                
                {linkingLoading ? (
                  <div className="flex justify-center py-4">
                    <Loader2 size={20} className="animate-spin text-[var(--md-sys-color-secondary)]" />
                  </div>
                ) : availableProjects.length === 0 ? (
                  <div className="text-center py-4 text-[10px] font-bold opacity-50 uppercase">
                    暂无可关联的闲置项目
                  </div>
                ) : (
                  <div className="grid grid-cols-1 gap-2 max-h-48 overflow-y-auto pr-2">
                    {availableProjects.map(p => (
                      <button
                        key={p.id}
                        onClick={() => handleLinkProject(p.id)}
                        className="flex items-center justify-between p-3 rounded-xl bg-[var(--md-sys-color-surface)] border border-[var(--md-sys-color-outline-variant)] hover:border-[var(--md-sys-color-secondary)] hover:bg-[var(--md-sys-color-secondary-container)]/10 transition-all text-left group"
                      >
                        <div className="flex items-center gap-3">
                          <Briefcase size={14} className="text-[var(--md-sys-color-secondary)]" />
                          <span className="text-xs font-bold">{p.name}</span>
                        </div>
                        <LinkIcon size={14} className="opacity-0 group-hover:opacity-100 transition-opacity text-[var(--md-sys-color-secondary)]" />
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}

            {isCreatingProject && (
              <div className="mb-4 p-4 border-2 border-dashed border-[var(--md-sys-color-primary)] rounded-2xl bg-[var(--md-sys-color-primary-container)]/10 animate-in slide-in-from-top-2">
                <input
                  autoFocus
                  type="text"
                  placeholder="输入项目名称..."
                  className="w-full bg-transparent border-none outline-none text-sm font-bold mb-3"
                  value={newProjectName}
                  onChange={(e) => setNewProjectName(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleCreateProject()}
                />
                <div className="flex justify-end gap-2">
                  <button 
                    onClick={() => setIsCreatingProject(false)}
                    className="px-3 py-1 text-[10px] font-black uppercase text-[var(--md-sys-color-outline)]"
                  >
                    取消
                  </button>
                  <button 
                    onClick={handleCreateProject}
                    disabled={!newProjectName.trim()}
                    className="px-3 py-1 text-[10px] font-black uppercase bg-[var(--md-sys-color-primary)] text-[var(--md-sys-color-on-primary)] rounded-lg disabled:opacity-50"
                  >
                    确认创建
                  </button>
                </div>
              </div>
            )}

            {loading ? (
              <div className="flex flex-col items-center justify-center py-12 gap-3 opacity-50">
                <Loader2 size={24} className="animate-spin" />
                <span className="text-xs font-bold uppercase">正在加载项目层级...</span>
              </div>
            ) : projects.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 gap-3 border-2 border-dashed border-[var(--md-sys-color-outline-variant)] rounded-3xl opacity-50">
                <Briefcase size={32} />
                <span className="text-xs font-bold uppercase">暂无关联项目</span>
              </div>
            ) : (
              <div className="space-y-3">
                {projects.map(project => (
                  <div 
                    key={project.id} 
                    className="border border-[var(--md-sys-color-outline-variant)] rounded-2xl overflow-hidden bg-[var(--md-sys-color-surface-container-low)]"
                  >
                    {/* Project Header */}
                    <div 
                      className="p-4 flex items-center justify-between cursor-pointer hover:bg-[var(--md-sys-color-surface-container-high)] transition-colors"
                      onClick={() => toggleProject(project.id)}
                    >
                      <div className="flex items-center gap-3">
                        <div className={clsx(
                          "w-8 h-8 rounded-lg flex items-center justify-center",
                          project.dossier.status === 'completed' ? "bg-green-100 text-green-700" : "bg-[var(--md-sys-color-secondary-container)] text-[var(--md-sys-color-secondary)]"
                        )}>
                          {project.dossier.status === 'completed' ? <CheckCircle2 size={16} /> : <Briefcase size={16} />}
                        </div>
                        <div>
                          <h5 className="text-sm font-bold">{project.name}</h5>
                          <div className="flex items-center gap-2 text-[10px] opacity-60 font-bold uppercase">
                            <span>{project.tasks_count} 任务</span>
                            <span>•</span>
                            <span>{project.dossier.progress}% 完成</span>
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        {expandedProjects[project.id] ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
                      </div>
                    </div>

                    {/* Project Tasks (Expanded) */}
                    {expandedProjects[project.id] && (
                      <div className="px-4 pb-4 bg-[var(--md-sys-color-surface)] border-t border-[var(--md-sys-color-outline-variant)] animate-in slide-in-from-top-2 duration-200">
                        {tasksLoading[project.id] ? (
                          <div className="flex items-center justify-center py-4 gap-2 opacity-40">
                            <Loader2 size={14} className="animate-spin" />
                            <span className="text-[10px] font-black uppercase">加载任务中...</span>
                          </div>
                        ) : !projectTasks[project.id] || projectTasks[project.id].length === 0 ? (
                          <div className="py-4 text-center opacity-40">
                            <span className="text-[10px] font-black uppercase italic">此项目暂无明确任务</span>
                          </div>
                        ) : (
                          <div className="pt-3 space-y-2">
                            {projectTasks[project.id].map(task => (
                              <div 
                                key={task.id}
                                className="flex items-center justify-between p-3 rounded-xl bg-[var(--md-sys-color-surface-container-lowest)] border border-[var(--md-sys-color-outline-variant)] hover:border-[var(--md-sys-color-primary)] transition-all group"
                              >
                                <div className="flex items-center gap-3">
                                  {task.dossier.status === 'completed' ? (
                                    <CheckCircle2 size={16} className="text-green-500" />
                                  ) : (
                                    <Circle size={16} className="text-[var(--md-sys-color-outline)]" />
                                  )}
                                  <span className={clsx(
                                    "text-xs font-medium",
                                    task.dossier.status === 'completed' && "line-through opacity-50"
                                  )}>
                                    {task.name}
                                  </span>
                                </div>
                                <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                                  <button className="p-1 rounded-full hover:bg-[var(--md-sys-color-surface-variant)]">
                                    <MoreVertical size={14} />
                                  </button>
                                </div>
                              </div>
                            ))}
                            
                            {isCreatingTask === project.id ? (
                              <div className="mt-2 p-3 rounded-xl bg-[var(--md-sys-color-primary-container)]/10 border border-dashed border-[var(--md-sys-color-primary)] animate-in zoom-in-95 duration-200">
                                <input
                                  autoFocus
                                  type="text"
                                  placeholder="任务名称..."
                                  className="w-full bg-transparent border-none outline-none text-xs font-bold mb-2"
                                  value={newTaskName}
                                  onChange={(e) => setNewTaskName(e.target.value)}
                                  onKeyDown={(e) => e.key === 'Enter' && handleCreateTask(project.id)}
                                />
                                <div className="flex justify-end gap-2">
                                  <button 
                                    onClick={() => setIsCreatingTask(null)}
                                    className="text-[10px] font-black uppercase text-[var(--md-sys-color-outline)]"
                                  >
                                    取消
                                  </button>
                                  <button 
                                    onClick={() => handleCreateTask(project.id)}
                                    disabled={!newTaskName.trim()}
                                    className="text-[10px] font-black uppercase text-[var(--md-sys-color-primary)] disabled:opacity-50"
                                  >
                                    添加
                                  </button>
                                </div>
                              </div>
                            ) : (
                              <button 
                                onClick={() => setIsCreatingTask(project.id)}
                                className="w-full py-2 flex items-center justify-center gap-2 text-[10px] font-black uppercase text-[var(--md-sys-color-outline)] hover:text-[var(--md-sys-color-primary)] border border-dashed border-[var(--md-sys-color-outline-variant)] rounded-xl mt-2 transition-colors"
                              >
                                <Plus size={14} /> 添加任务
                              </button>
                            )}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </section>
        </div>

        {/* Footer */}
        <div className="p-6 border-t border-[var(--md-sys-color-outline-variant)] flex justify-end bg-[var(--md-sys-color-surface-container-low)]">
          <button 
            onClick={onClose}
            className="px-6 py-2 rounded-full bg-[var(--md-sys-color-primary)] text-[var(--md-sys-color-on-primary)] font-black uppercase text-xs tracking-widest shadow-lg shadow-[var(--md-sys-color-primary)]/20 hover:scale-105 transition-transform"
          >
            完成回顾
          </button>
        </div>
      </div>
    </div>
  );
}
