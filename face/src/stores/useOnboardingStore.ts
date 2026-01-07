/**
 * 引导流程状态管理
 * 追踪用户的引导进度
 */
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export type OnboardingStep = 'login' | 'persona' | 'h3' | 'completed';

export interface PersonaConfig {
  nickname: string;           // 用户希望 AI 如何称呼自己
  aiName: string;             // AI 的名字
  personality: string;        // AI 人格描述
  instructions: string;       // 自定义指令
  knowledgeBase: string[];    // 知识库文件 IDs
  memoryFiles: string[];      // 记忆文件 IDs
  vision: string;             // 用户的终局愿景
  goals: string[];            // 核心目标
}

export interface H3InitialState {
  mind: number;
  body: number;
  spirit: number;
  vocation: number;
  answers: Record<string, number>;  // 问题ID -> 答案分数
  completedAt?: string;
}

interface OnboardingState {
  // 当前步骤
  currentStep: OnboardingStep;
  
  // 人格配置
  personaConfig: PersonaConfig | null;
  
  // H3 初始状态
  h3InitialState: H3InitialState | null;
  
  // 引导是否完成
  isOnboardingComplete: boolean;
  
  // Actions
  setStep: (step: OnboardingStep) => void;
  nextStep: () => void;
  previousStep: () => void;
  setPersonaConfig: (config: PersonaConfig) => void;
  setH3InitialState: (state: H3InitialState) => void;
  completeOnboarding: () => void;
  resetOnboarding: () => void;
}

const STEP_ORDER: OnboardingStep[] = ['login', 'persona', 'h3', 'completed'];

export const useOnboardingStore = create<OnboardingState>()(
  persist(
    (set, get) => ({
      currentStep: 'login',
      personaConfig: null,
      h3InitialState: null,
      isOnboardingComplete: false,

      setStep: (step) => set({ currentStep: step }),

      nextStep: () => {
        const { currentStep } = get();
        const currentIndex = STEP_ORDER.indexOf(currentStep);
        if (currentIndex < STEP_ORDER.length - 1) {
          const nextStep = STEP_ORDER[currentIndex + 1];
          set({ currentStep: nextStep });
          if (nextStep === 'completed') {
            set({ isOnboardingComplete: true });
          }
        }
      },

      previousStep: () => {
        const { currentStep } = get();
        const currentIndex = STEP_ORDER.indexOf(currentStep);
        if (currentIndex > 0) {
          set({ currentStep: STEP_ORDER[currentIndex - 1] });
        }
      },

      setPersonaConfig: (config) => set({ personaConfig: config }),

      setH3InitialState: (state) => set({ h3InitialState: state }),

      completeOnboarding: () => set({
        currentStep: 'completed',
        isOnboardingComplete: true,
      }),

      resetOnboarding: () => set({
        currentStep: 'login',
        personaConfig: null,
        h3InitialState: null,
        isOnboardingComplete: false,
      }),
    }),
    {
      name: 'endgame-onboarding',
    }
  )
);

