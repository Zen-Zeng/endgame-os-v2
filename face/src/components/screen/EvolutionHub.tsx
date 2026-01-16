import { useState, useEffect } from 'react';
import { 
  Upload, 
  BrainCircuit, 
  Share2, 
  Target, 
  Zap,
  Loader2,
  CheckCircle2,
  XCircle
} from 'lucide-react';
import Button from '../ui/Button';
import api from '../../lib/api';
import clsx from 'clsx';

interface TaskStatus {
  id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress: number;
  message?: string;
  error?: string;
}

interface EvolutionHubProps {
  onEvolutionComplete?: () => void;
  className?: string;
}

const pipelineSteps = [
  { id: 'upload', label: '上传记忆', icon: Upload },
  { id: 'structure', label: '结构化', icon: BrainCircuit },
  { id: 'vectorize', label: '向量化', icon: Share2 },
  { id: 'graph', label: '图谱化', icon: Target },
];

export default function EvolutionHub({ onEvolutionComplete, className }: EvolutionHubProps) {
  const [isTraining, setIsTraining] = useState(false);
  const [trainingProgress, setTrainingProgress] = useState<number | null>(null);
  const [trainingMessage, setTrainingMessage] = useState<string>('');
  const [isProcessing, setIsProcessing] = useState(false);

  const getCurrentStepIndex = (message: string) => {
    if (!message) return -1;
    if (message.includes('上传') || message.includes('解析')) return 0;
    if (message.includes('DeepSeek') || message.includes('结构化')) return 1;
    if (message.includes('向量化')) return 2;
    if (message.includes('图谱') || message.includes('关系') || message.includes('写入')) return 3;
    return 0;
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    try {
      setIsProcessing(true);
      for (const file of Array.from(files)) {
        const formData = new FormData();
        formData.append('file', file);
        
        setTrainingMessage(`正在上传: ${file.name}...`);
        const response: any = await api.post('/archives/upload', formData);
        
        if (file.name.toLowerCase().endsWith('.json')) {
          setTrainingMessage('正在解析对话主题...');
          await api.post(`/archives/split/${response.id}`);
        }
      }
      alert('记忆素材上传成功！建议稍后进行批量训练。');
      onEvolutionComplete?.();
    } catch (error: any) {
      console.error('上传失败:', error);
      alert(`上传失败: ${error.response?.data?.detail || error.message}`);
    } finally {
      setIsProcessing(false);
      setTrainingMessage('');
    }
  };

  const handleVisionInjection = async (files: File[]) => {
    try {
      setIsProcessing(true);
      setIsTraining(true);
      for (const file of files) {
        const formData = new FormData();
        formData.append('file', file);
        
        setTrainingMessage(`Injecting: ${file.name}...`);
        const uploadRes: any = await api.post('/archives/upload', formData);
        
        const trainResponse: any = await api.post('/memory/train', { 
          filenames: [uploadRes.filename] 
        });
        
        const taskId = trainResponse.task_id;
        await pollStatus(taskId);
      }
      onEvolutionComplete?.();
    } catch (e: any) {
      console.error("Evolution Failed", e);
      alert(`Evolution Failed: ${e.message}`);
    } finally {
      setIsProcessing(false);
      setIsTraining(false);
      setTrainingProgress(null);
      setTrainingMessage('');
    }
  };

  const pollStatus = (taskId: string) => {
    return new Promise<void>((resolve, reject) => {
      const timer = setInterval(async () => {
        try {
          const status = await api.get<TaskStatus>(`/memory/tasks/${taskId}`);
          setTrainingProgress(status.progress);
          setTrainingMessage(status.message || '进化中...');
          
          if (status.status === 'completed' || status.status === 'failed') {
            clearInterval(timer);
            if (status.status === 'failed') reject(new Error(status.error || '训练失败'));
            else resolve();
          }
        } catch (error) {
          clearInterval(timer);
          reject(error);
        }
      }, 1500);
    });
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) {
      await handleVisionInjection(files);
    }
  };

  return (
    <div className={clsx("flex flex-col gap-4", className)}>
      {/* 进化进度指示器 */}
      {isTraining && (
        <div className="p-4 bg-[var(--md-sys-color-primary-container)] text-[var(--md-sys-color-on-primary-container)] rounded-2xl border border-[var(--md-sys-color-primary)]/20 shadow-lg animate-in fade-in zoom-in duration-300">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <div className="p-2 bg-[var(--md-sys-color-primary)] text-[var(--md-sys-color-on-primary)] rounded-lg">
                <BrainCircuit size={18} className="animate-pulse" />
              </div>
              <div>
                <h4 className="font-black text-sm uppercase tracking-wider">系统进化中 / Evolving</h4>
                <p className="text-[10px] opacity-70 font-bold">{trainingMessage}</p>
              </div>
            </div>
            <span className="text-xl font-black">{trainingProgress || 0}%</span>
          </div>

          <div className="flex items-center justify-between gap-1 mb-4">
            {pipelineSteps.map((step, idx) => {
              const activeIdx = getCurrentStepIndex(trainingMessage);
              const isCompleted = idx < activeIdx;
              const isActive = idx === activeIdx;
              const Icon = step.icon;
              
              return (
                <div key={step.id} className="flex-1 flex flex-col items-center gap-1.5">
                  <div className={clsx(
                    "w-8 h-8 rounded-full flex items-center justify-center transition-all duration-500",
                    isActive ? "bg-[var(--md-sys-color-primary)] text-[var(--md-sys-color-on-primary)] scale-110 shadow-md" : 
                    isCompleted ? "bg-[var(--md-sys-color-primary)]/20 text-[var(--md-sys-color-primary)]" : "bg-[var(--md-sys-color-surface-variant)] text-[var(--md-sys-color-outline)] opacity-40"
                  )}>
                    {isCompleted ? <CheckCircle2 size={14} /> : <Icon size={14} />}
                  </div>
                  <span className="text-[8px] font-black uppercase text-center opacity-60 leading-tight">{step.label}</span>
                </div>
              );
            })}
          </div>

          <div className="h-1.5 w-full bg-[var(--md-sys-color-surface-variant)]/30 rounded-full overflow-hidden">
            <div 
              className="h-full bg-[var(--md-sys-color-primary)] transition-all duration-300"
              style={{ width: `${trainingProgress || 0}%` }}
            />
          </div>
        </div>
      )}

      {/* 快捷上传/注入入口 */}
      <div 
        className={clsx(
          "relative group p-6 rounded-[var(--md-sys-shape-corner-extra-large)] border-2 border-dashed transition-all duration-300 flex flex-col items-center justify-center gap-4 text-center cursor-pointer",
          isProcessing ? "border-[var(--md-sys-color-primary)] bg-[var(--md-sys-color-primary)]/5" : "border-[var(--md-sys-color-outline-variant)] hover:border-[var(--md-sys-color-primary)] hover:bg-[var(--md-sys-color-surface-container-high)]"
        )}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
        onClick={() => document.getElementById('evolution-upload-input')?.click()}
      >
        <input
          id="evolution-upload-input"
          type="file"
          className="hidden"
          onChange={handleFileUpload}
          multiple
        />
        
        <div className={clsx(
          "w-16 h-16 rounded-3xl flex items-center justify-center transition-all duration-500",
          isProcessing ? "bg-[var(--md-sys-color-primary)] text-[var(--md-sys-color-on-primary)] rotate-180" : "bg-[var(--md-sys-color-surface-container-highest)] text-[var(--md-sys-color-primary)] group-hover:scale-110 group-hover:rotate-12"
        )}>
          {isProcessing ? <Loader2 size={32} className="animate-spin" /> : <Upload size={32} />}
        </div>

        <div className="space-y-1">
          <h4 className="font-black text-sm uppercase tracking-widest">注入记忆 / Ingest Memory</h4>
          <p className="text-[10px] text-[var(--md-sys-color-on-surface-variant)] font-bold opacity-60">支持拖拽文件或点击上传 (PDF, MD, JSON, TXT)</p>
        </div>

        {/* Floating Quick Action */}
        <div className="absolute top-2 right-2">
          <div className="p-1.5 bg-[var(--md-sys-color-tertiary-container)] text-[var(--md-sys-color-on-tertiary-container)] rounded-lg shadow-sm">
            <Zap size={14} className="animate-pulse" />
          </div>
        </div>
      </div>
    </div>
  );
}
