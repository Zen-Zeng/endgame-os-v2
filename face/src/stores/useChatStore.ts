import { create } from 'zustand';

export interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp: number;
}

interface ChatState {
  messages: Message[];
  isStreaming: boolean;
  error: string | null;
  addMessage: (message: Message) => void;
  setStreaming: (status: boolean) => void;
  setError: (error: string | null) => void;
  clearMessages: () => void;
}

export const useChatStore = create<ChatState>((set) => ({
  messages: [],
  isStreaming: false,
  error: null,
  addMessage: (message) => 
    set((state) => ({ 
      messages: [...state.messages, message] 
    })),
  setStreaming: (status) => set({ isStreaming: status }),
  setError: (error) => set({ error }),
  clearMessages: () => set({ messages: [] }),
}));
