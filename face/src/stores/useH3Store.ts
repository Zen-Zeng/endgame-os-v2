/**
 * H3 能量状态管理
 * 管理用户的四维能量状态
 */
import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { api } from '../lib/api';

export interface H3Scores {
  mind: number;
  body: number;
  spirit: number;
  vocation: number;
}

export interface H3Entry {
  id: string;
  scores: H3Scores;
  note?: string;
  source: 'calibration' | 'chat' | 'manual';
  created_at: string;
}

interface H3State {
  scores: H3Scores;
  history: H3Entry[];
  isLoading: boolean;
  lastUpdated: string | null;
  
  // Actions
  setScore: (type: keyof H3Scores, val: number) => void;
  setScores: (scores: H3Scores) => void;
  updateScores: (scores: Partial<H3Scores>, note?: string, source?: H3Entry['source']) => Promise<void>;
  fetchHistory: () => Promise<void>;
  fetchCurrentState: () => Promise<void>;
  initializeFromOnboarding: (scores: H3Scores) => Promise<void>;
}

export const useH3Store = create<H3State>()(
  persist(
    (set, get) => ({
      scores: { mind: 0, body: 0, spirit: 0, vocation: 0 },
      history: [],
      isLoading: false,
      lastUpdated: null,

      setScore: (type, val) =>
        set((state) => ({
          scores: { ...state.scores, [type]: val },
        })),

      setScores: (scores) => set({ scores }),

      updateScores: async (newScores, note) => {
        const { scores } = get();
        const updatedScores = { ...scores, ...newScores };
        
        set({ isLoading: true });
        try {
          // 对接 /h3/calibrate 接口
          const response = await api.post<any>('/h3/calibrate', {
            mind: updatedScores.mind,
            body: updatedScores.body,
            spirit: updatedScores.spirit,
            vocation: updatedScores.vocation,
            mood_note: note,
            blockers: [],
            wins: []
          });
          
          // 转换后端响应为前端 H3Entry 格式
          const newEntry: H3Entry = {
            id: response.id,
            scores: {
              mind: response.energy.mind,
              body: response.energy.body,
              spirit: response.energy.spirit,
              vocation: response.energy.vocation
            },
            note: response.mood_note,
            source: response.calibration_type || 'manual',
            created_at: response.created_at
          };
          
          set({
            scores: newEntry.scores,
            history: [...get().history, newEntry],
            lastUpdated: newEntry.created_at,
            isLoading: false,
          });
        } catch (error) {
          console.error('更新 H3 状态失败:', error);
          set({ isLoading: false });
          // 即使后端失败，也更新本地状态 (乐观更新)
          set({
            scores: updatedScores,
            lastUpdated: new Date().toISOString(),
          });
        }
      },

      fetchCurrentState: async () => {
        set({ isLoading: true });
        try {
          const response = await api.get<any>('/h3/current');
          // 后端直接返回 H3Energy 对象，而不是包裹在 energy 字段中
          if (response && (response.mind !== undefined || response.energy)) {
            const energy = response.energy || response;
            set({
              scores: {
                mind: energy.mind || 0,
                body: energy.body || 0,
                spirit: energy.spirit || 0,
                vocation: energy.vocation || 0
              },
              lastUpdated: energy.created_at,
              isLoading: false
            });
          }
        } catch (error) {
          console.error('获取当前 H3 状态失败:', error);
          set({ isLoading: false });
        }
      },

      fetchHistory: async () => {
        set({ isLoading: true });
        try {
          const response = await api.get<any[]>('/h3/history?days=7');
          const historyEntries: H3Entry[] = response.map(item => ({
            id: item.id,
            scores: {
              mind: item.mind,
              body: item.body,
              spirit: item.spirit,
              vocation: item.vocation
            },
            note: item.mood_note,
            source: 'manual',
            created_at: item.created_at
          }));
          set({ history: historyEntries, isLoading: false });
        } catch (error) {
          console.error('获取 H3 历史失败:', error);
          set({ isLoading: false });
        }
      },

      initializeFromOnboarding: async (scores) => {
        set({ isLoading: true });
        try {
          const response = await api.post<{ entry: H3Entry }>('/h3/initialize', {
            scores,
            source: 'calibration',
            note: '初始校准',
          });
          
          set({
            scores: response.entry.scores,
            history: [response.entry],
            lastUpdated: response.entry.created_at,
            isLoading: false,
          });
        } catch (error) {
          console.error('初始化 H3 状态失败:', error);
          // 即使后端失败，也更新本地状态
          set({
            scores,
            lastUpdated: new Date().toISOString(),
            isLoading: false,
          });
        }
      },
    }),
    {
      name: 'endgame-h3',
      partialize: (state) => ({
        scores: state.scores,
        lastUpdated: state.lastUpdated,
      }),
    }
  )
);
