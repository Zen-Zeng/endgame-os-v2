import { useState } from 'react';
import { X, Target, Flag, AlertCircle, Loader2 } from 'lucide-react';
import { api } from '../../lib/api';
import Button from '../ui/Button';
import clsx from 'clsx';

interface CreateGoalModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export default function CreateGoalModal({ isOpen, onClose, onSuccess }: CreateGoalModalProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [formData, setFormData] = useState({
    name: '',
    content: '',
    priority: 'medium'
  });

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.name.trim()) {
      setError('请输入目标名称');
      return;
    }

    try {
      setLoading(true);
      setError(null);
      
      // 注意：根据后端 API，参数是通过查询参数传递的
      await api.post(`/goals/create?name=${encodeURIComponent(formData.name)}&content=${encodeURIComponent(formData.content)}&priority=${formData.priority}`);
      
      onSuccess();
      onClose();
      // 重置表单
      setFormData({ name: '', content: '', priority: 'medium' });
    } catch (err: any) {
      setError(err.message || '创建目标失败，请重试');
    } finally {
      setLoading(false);
    }
  };

  const priorities = [
    { value: 'low', label: '低优先级', color: 'bg-blue-500' },
    { value: 'medium', label: '中优先级', color: 'bg-amber-500' },
    { value: 'high', label: '高优先级', color: 'bg-rose-500' },
  ];

  return (
    <div className="fixed inset-0 z-[110] flex items-center justify-center p-4">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />
      
      {/* Modal Content */}
      <div className="relative w-full max-w-lg bg-[var(--md-sys-color-surface)] rounded-[32px] shadow-2xl border border-[var(--md-sys-color-outline-variant)] overflow-hidden flex flex-col animate-in fade-in zoom-in duration-200">
        <div className="flex items-center justify-between p-6 border-b border-[var(--md-sys-color-outline-variant)]">
          <h3 className="text-xl font-black flex items-center gap-2">
            <Target className="text-[var(--md-sys-color-primary)]" />
            创建新目标
          </h3>
          <button 
            onClick={onClose}
            className="p-2 rounded-full hover:bg-[var(--md-sys-color-surface-variant)] transition-colors"
          >
            <X size={20} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          {error && (
            <div className="flex items-center gap-2 p-4 bg-[var(--md-sys-color-error-container)] text-[var(--md-sys-color-on-error-container)] rounded-2xl text-sm font-bold">
              <AlertCircle size={18} />
              {error}
            </div>
          )}

          <div className="space-y-2">
            <label className="text-xs font-black uppercase tracking-widest opacity-50 ml-1">目标名称</label>
            <input
              autoFocus
              type="text"
              placeholder="例如：完成个人品牌重塑"
              className="w-full px-5 py-4 rounded-2xl bg-[var(--md-sys-color-surface-container-highest)] border border-transparent focus:border-[var(--md-sys-color-primary)] outline-none transition-all font-bold"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            />
          </div>

          <div className="space-y-2">
            <label className="text-xs font-black uppercase tracking-widest opacity-50 ml-1">详细描述 (愿景内容)</label>
            <textarea
              placeholder="描述这个目标完成后的理想状态..."
              rows={4}
              className="w-full px-5 py-4 rounded-2xl bg-[var(--md-sys-color-surface-container-highest)] border border-transparent focus:border-[var(--md-sys-color-primary)] outline-none transition-all text-sm leading-relaxed resize-none"
              value={formData.content}
              onChange={(e) => setFormData({ ...formData, content: e.target.value })}
            />
          </div>

          <div className="space-y-2">
            <label className="text-xs font-black uppercase tracking-widest opacity-50 ml-1">优先级</label>
            <div className="flex gap-2">
              {priorities.map((p) => (
                <button
                  key={p.value}
                  type="button"
                  onClick={() => setFormData({ ...formData, priority: p.value })}
                  className={clsx(
                    "flex-1 py-3 rounded-2xl text-xs font-black uppercase tracking-tighter transition-all border-2",
                    formData.priority === p.value 
                      ? "border-[var(--md-sys-color-primary)] bg-[var(--md-sys-color-primary-container)] text-[var(--md-sys-color-on-primary-container)]" 
                      : "border-transparent bg-[var(--md-sys-color-surface-container-high)] text-[var(--md-sys-color-outline)] hover:bg-[var(--md-sys-color-surface-variant)]"
                  )}
                >
                  <div className="flex items-center justify-center gap-2">
                    <div className={clsx("w-2 h-2 rounded-full", p.color)} />
                    {p.label}
                  </div>
                </button>
              ))}
            </div>
          </div>

          <div className="pt-4 flex gap-3">
            <Button 
              type="button" 
              variant="outlined" 
              fullWidth 
              onClick={onClose}
              disabled={loading}
            >
              取消
            </Button>
            <Button 
              type="submit" 
              variant="filled" 
              fullWidth 
              loading={loading}
              icon={!loading && <Flag size={18} />}
            >
              创建目标
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
