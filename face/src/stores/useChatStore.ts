import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp: number;
  metadata?: Record<string, any>;
}

interface ChatState {
  messages: Message[];
  isStreaming: boolean;
  error: string | null;
  addMessage: (message: Message) => void;
  setStreaming: (status: boolean) => void;
  setError: (error: string | null) => void;
  clearMessages: () => void;
  updateLastMessage: (content: string | null, metadata?: Record<string, any>) => void;
}

export const useChatStore = create<ChatState>()(
  persist(
    (set) => ({
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
      updateLastMessage: (content, metadata) =>
        set((state) => {
          const newMessages = [...state.messages];
          if (newMessages.length > 0) {
            const lastMessage = newMessages[newMessages.length - 1];
            if (lastMessage.role === 'assistant') {
              newMessages[newMessages.length - 1] = {
                ...lastMessage,
                content: content ? lastMessage.content + content : lastMessage.content,
                metadata: metadata ? { ...lastMessage.metadata, ...metadata } : lastMessage.metadata,
              };
            }
          }
          return { messages: newMessages };
        }),
    }),
    {
      name: 'chat-storage',
      partialize: (state) => ({ messages: state.messages }),
    }
  )
);
