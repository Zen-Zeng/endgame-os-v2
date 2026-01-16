/**
 * 认证状态管理
 */
import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { api } from '../lib/api';

export interface UserVision {
  title: string;
  description: string;
  core_values: string[];
  key_milestones: string[];
}

export interface PersonaConfig {
  name: string;
  tone: string;
  proactive_level: number;
  challenge_mode: boolean;
  reflection_frequency: string;
  system_prompt_template?: string;
  traits: string[];
}

export interface User {
  id: string;
  email: string;
  name: string;
  avatar_url?: string;
  onboarding_completed: boolean;
  morning_protocol_enabled: boolean;
  vision?: UserVision;
  persona?: PersonaConfig;
}

interface AuthState {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  error: string | null;
  
  // Actions
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, name: string) => Promise<void>;
  logout: () => void;
  checkAuth: () => Promise<void>;
  clearError: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      token: null,
      isLoading: false,
      error: null,

      login: async (email: string, password: string) => {
        set({ isLoading: true, error: null });
        try {
          const response = await api.post<{ access_token: string; user: User }>(
            '/auth/login',
            { email, password }
          );
          
          api.setToken(response.access_token);
          set({
            user: response.user,
            token: response.access_token,
            isLoading: false,
          });
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : '登录失败',
            isLoading: false,
          });
          throw error;
        }
      },

      register: async (email: string, password: string, name: string) => {
        set({ isLoading: true, error: null });
        try {
          const response = await api.post<{ access_token: string; user: User }>(
            '/auth/register',
            { email, password, name }
          );
          
          api.setToken(response.access_token);
          set({
            user: response.user,
            token: response.access_token,
            isLoading: false,
          });
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : '注册失败',
            isLoading: false,
          });
          throw error;
        }
      },

      logout: () => {
        api.setToken(null);
        set({ user: null, token: null });
      },

      checkAuth: async () => {
        const { token } = get();
        if (!token) return;

        set({ isLoading: true });
        try {
          api.setToken(token);
          const response = await api.post<{ valid: boolean; user: User | null }>(
            '/auth/verify'
          );
          
          if (response.valid && response.user) {
            set({ user: response.user, isLoading: false });
          } else {
            set({ user: null, token: null, isLoading: false });
          }
        } catch {
          set({ user: null, token: null, isLoading: false });
        }
      },

      clearError: () => set({ error: null }),
    }),
    {
      name: 'endgame-auth',
      partialize: (state) => ({ token: state.token }),
    }
  )
);

