import { create } from 'zustand';

export interface H3Scores {
  mind: number;
  body: number;
  spirit: number;
  vocation: number;
}

interface H3State {
  scores: H3Scores;
  history: any[];
  setScore: (type: keyof H3Scores, val: number) => void;
  setScores: (scores: H3Scores) => void;
  fetchHistory: () => Promise<void>;
}

export const useH3Store = create<H3State>((set) => ({
  scores: { mind: 5, body: 5, spirit: 5, vocation: 5 },
  history: [],
  setScore: (type, val) => 
    set((state) => ({ 
      scores: { ...state.scores, [type]: val } 
    })),
  setScores: (scores) => set({ scores }),
  fetchHistory: async () => {
    try {
      const response = await fetch('http://127.0.0.1:8002/api/h3/history');
      if (response.ok) {
        const data = await response.json();
        set({ history: data.history });
      }
    } catch (err) {
      console.error('获取 H3 历史失败:', err);
    }
  },
}));
