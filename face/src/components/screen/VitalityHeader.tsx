import { useState, useEffect } from 'react';
import { 
  Zap, 
  Activity, 
  MessageSquare, 
  Calendar,
  Settings2
} from 'lucide-react';
import { useH3Store, type H3Scores } from '../../stores/useH3Store';
import { useAuthStore } from '../../stores/useAuthStore';
import Button from '../ui/Button';
import clsx from 'clsx';

interface VitalityHeaderProps {
  stats: {
    total_conversations: number;
    streak_days: number;
    energy_points?: number;
  };
  className?: string;
}

const h3Dimensions = [
  { key: 'mind' as keyof H3Scores, label: '心智', icon: '🧠', color: 'var(--md-sys-color-primary)' },
  { key: 'body' as keyof H3Scores, label: '身体', icon: '💪', color: '#aaddbf' },
  { key: 'spirit' as keyof H3Scores, label: '精神', icon: '✨', color: '#ffb4a9' },
  { key: 'vocation' as keyof H3Scores, label: '志业', icon: '🎯', color: '#a8c7fa' },
] as const;

export default function VitalityHeader({ stats, className }: VitalityHeaderProps) {
  const { scores, updateScores } = useH3Store();
  const { user } = useAuthStore();
  const [showCalibration, setShowCalibration] = useState(false);
  const [localScores, setLocalScores] = useState(scores);
  const [isCalibrating, setIsCalibrating] = useState(false);
  const [moodNote, setMoodNote] = useState('');

  useEffect(() => {
    setLocalScores(scores);
  }, [scores]);

  const handleCalibrate = async () => {
    setIsCalibrating(true);
    try {
      await updateScores(localScores, moodNote || '手动校准', 'manual');
      setMoodNote('');
      setShowCalibration(false);
    } catch (e) {
      console.error('Calibration failed', e);
    } finally {
      setIsCalibrating(false);
    }
  };

  const isCompact = className?.includes('!p-0');

  return (
    <div className={clsx(
      "flex flex-col gap-4",
      !isCompact && "p-6 bg-[var(--md-sys-color-surface)] border-b border-[var(--md-sys-color-outline-variant)]",
      className
    )}>
      <div className="flex flex-wrap items-center justify-between gap-6">
        {/* 左侧：基础数据 */}
        <div className="flex items-center gap-8">
          <div className="flex flex-col">
            <span className="text-[var(--md-sys-typescale-label-small-size)] text-[var(--md-sys-color-outline)] uppercase tracking-wider font-bold">对齐天数</span>
            <div className="flex items-center gap-2">
              <Calendar size={isCompact ? 14 : 16} className="text-[var(--md-sys-color-primary)]" />
              <span className={clsx("font-black", isCompact ? "text-lg" : "text-2xl")}>{stats.streak_days}</span>
            </div>
          </div>
          <div className="flex flex-col">
            <span className="text-[var(--md-sys-typescale-label-small-size)] text-[var(--md-sys-color-outline)] uppercase tracking-wider font-bold">对话数</span>
            <div className="flex items-center gap-2">
              <MessageSquare size={isCompact ? 14 : 16} className="text-[var(--md-sys-color-secondary)]" />
              <span className={clsx("font-black", isCompact ? "text-lg" : "text-2xl")}>{stats.total_conversations}</span>
            </div>
          </div>
          <div className="flex flex-col">
            <span className="text-[var(--md-sys-typescale-label-small-size)] text-[var(--md-sys-color-outline)] uppercase tracking-wider font-bold">能量点</span>
            <div className="flex items-center gap-2">
              <Zap size={isCompact ? 14 : 16} className="text-[var(--md-sys-color-tertiary)]" />
              <span className={clsx("font-black", isCompact ? "text-lg" : "text-2xl")}>{stats.energy_points || 0}</span>
            </div>
          </div>
        </div>

        {/* 右侧：极简 H3 能量状态 */}
        <div className={clsx(
          "flex items-center gap-4 bg-[var(--md-sys-color-surface-container-high)] p-2 rounded-2xl border border-[var(--md-sys-color-outline-variant)] shadow-inner",
          isCompact && "scale-90 origin-right"
        )}>
          <div className="flex items-center gap-3 px-2">
            {h3Dimensions.map(dim => (
              <div key={dim.key} className="flex flex-col items-center gap-1 group relative">
                <span className="text-lg">{dim.icon}</span>
                <div className="w-12 h-1.5 bg-[var(--md-sys-color-surface-variant)] rounded-full overflow-hidden">
                  <div 
                    className="h-full transition-all duration-500 ease-out"
                    style={{ 
                      width: `${scores[dim.key]}%`,
                      backgroundColor: dim.color 
                    }}
                  />
                </div>
                {/* Hover Tooltip */}
                <div className="absolute -bottom-8 left-1/2 -translate-x-1/2 px-2 py-1 bg-[var(--md-sys-color-on-surface)] text-[var(--md-sys-color-surface)] text-[10px] font-bold rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap z-50 pointer-events-none">
                  {dim.label}: {scores[dim.key]}%
                </div>
              </div>
            ))}
          </div>
          
          <div className="w-[1px] h-8 bg-[var(--md-sys-color-outline-variant)]" />
          
          <button 
            onClick={() => setShowCalibration(!showCalibration)}
            className={clsx(
              "p-2 rounded-xl transition-all",
              showCalibration ? "bg-[var(--md-sys-color-primary)] text-[var(--md-sys-color-on-primary)] shadow-md" : "text-[var(--md-sys-color-primary)] hover:bg-[var(--md-sys-color-primary)]/10"
            )}
          >
            <Settings2 size={20} />
          </button>
        </div>
      </div>

      {/* 校准面板 (手风琴效果) */}
      {showCalibration && (
        <div className="animate-in slide-in-from-top-4 duration-300 overflow-hidden">
          <div className="p-4 mt-2 bg-[var(--md-sys-color-surface-container-highest)] rounded-2xl border border-[var(--md-sys-color-primary)]/20 shadow-lg space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              {h3Dimensions.map(dim => (
                <div key={dim.key} className="space-y-2">
                  <div className="flex justify-between items-center">
                    <span className="text-xs font-bold flex items-center gap-2">
                      <span>{dim.icon}</span>
                      {dim.label}
                    </span>
                    <span className="text-xs font-mono font-bold" style={{ color: dim.color }}>{localScores[dim.key]}%</span>
                  </div>
                  <input 
                    type="range"
                    min="0"
                    max="100"
                    step="5"
                    value={localScores[dim.key]}
                    onChange={(e) => setLocalScores(prev => ({ ...prev, [dim.key]: parseInt(e.target.value) }))}
                    className="w-full h-1.5 bg-[var(--md-sys-color-surface-variant)] rounded-full appearance-none cursor-pointer accent-[var(--md-sys-color-primary)]"
                          />
                        </div>
                      ))}
                    </div>

                    <div className="space-y-2">
                      <textarea
                        placeholder="记录当下的身体感觉、心智杂念或灵感发现..."
                        value={moodNote}
                        onChange={(e) => setMoodNote(e.target.value)}
                        className="w-full h-20 bg-[var(--md-sys-color-surface)] border border-[var(--md-sys-color-outline-variant)] rounded-xl p-3 text-xs focus:ring-2 focus:ring-[var(--md-sys-color-primary)] focus:border-transparent transition-all outline-none resize-none placeholder:opacity-30"
                      />
                    </div>

                    <div className="flex justify-end pt-2">
              <Button
                variant="filled"
                className="h-10 px-6 text-xs"
                icon={<Activity size={16} />}
                onClick={handleCalibrate}
                loading={isCalibrating}
              >
                立即校准
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
