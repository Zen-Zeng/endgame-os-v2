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

      updateScores: async (newScores, note, source = 'manual') => {
        const { scores } = get();
        const updatedScores = { ...scores, ...newScores };
        
        set({ isLoading: true });
        try {
          const response = await api.post<{ entry: H3Entry }>('/h3/update', {
            scores: updatedScores,
            note,
            source,
          });
          
          set({
            scores: response.entry.scores,
            history: [...get().history, response.entry],
            lastUpdated: response.entry.created_at,
            isLoading: false,
          });
        } catch (error) {
          console.error('更新 H3 状态失败:', error);
          set({ isLoading: false });
          // 即使后端失败，也更新本地状态
          set({
            scores: updatedScores,
            lastUpdated: new Date().toISOString(),
          });
        }
      },

      fetchHistory: async () => {
        set({ isLoading: true });
        try {
          const response = await api.get<{ history: H3Entry[] }>('/h3/history');
          set({
            history: response.history || [],
            isLoading: false,
          });
        } catch (err) {
          console.error('获取 H3 历史失败:', err);
          set({ isLoading: false });
        }
      },

      fetchCurrentState: async () => {
        set({ isLoading: true });
        try {
          const response = await api.get<{ scores: H3Scores; last_updated: string }>('/h3/current');
          set({
            scores: response.scores,
            lastUpdated: response.last_updated,
            isLoading: false,
          });
        } catch (err) {
          console.error('获取当前 H3 状态失败:', err);
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
