/**
 * 登录页面 - 增强版
 * 支持传统登录 + 生物识别认证 (WebAuthn)
 */
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Eye, 
  EyeOff, 
  Mail, 
  Lock, 
  Loader2, 
  Fingerprint,
  ScanFace,
  Sparkles,
  ArrowRight,
  Shield,
} from 'lucide-react';
import { useAuthStore } from '../stores/useAuthStore';
import { useOnboardingStore } from '../stores/useOnboardingStore';
import GlassCard from '../components/layout/GlassCard';
import Button from '../components/ui/Button';
import clsx from 'clsx';

// 检查浏览器是否支持 WebAuthn
const isWebAuthnSupported = () => {
  return !!(navigator.credentials && window.PublicKeyCredential);
};

export default function LoginPage() {
  const navigate = useNavigate();
  const { login, register, isLoading, error, clearError } = useAuthStore();
  const { isOnboardingComplete, nextStep } = useOnboardingStore();
  
  const [isRegister, setIsRegister] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [biometricSupported, setBiometricSupported] = useState(false);
  const [biometricLoading, setBiometricLoading] = useState(false);
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    name: '',
  });

  useEffect(() => {
    // 检查生物识别支持
    const checkBiometric = async () => {
      if (isWebAuthnSupported()) {
        try {
          const available = await PublicKeyCredential.isUserVerifyingPlatformAuthenticatorAvailable();
          setBiometricSupported(available);
        } catch {
          setBiometricSupported(false);
        }
      }
    };
    checkBiometric();
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    clearError();
    
    try {
      if (isRegister) {
        await register(formData.email, formData.password, formData.name);
      } else {
        await login(formData.email, formData.password);
      }
      
      // 登录成功后，检查是否需要引导流程
      if (isOnboardingComplete) {
        navigate('/');
      } else {
        nextStep(); // 进入下一步：persona 设置
        navigate('/onboarding/persona');
      }
    } catch {
      // Error is handled in store
    }
  };

  const handleBiometricLogin = async () => {
    if (!biometricSupported) return;
    
    setBiometricLoading(true);
    try {
      // WebAuthn 认证流程
      const credential = await navigator.credentials.get({
        publicKey: {
          challenge: new Uint8Array(32),
          timeout: 60000,
          userVerification: 'required',
          rpId: window.location.hostname,
        },
      });

      if (credential) {
        // TODO: 发送凭据到后端验证
        // 目前模拟成功
        await login('biometric@endgame.os', 'biometric');
        
        if (isOnboardingComplete) {
          navigate('/dashboard');
        } else {
          nextStep();
          navigate('/onboarding/persona');
        }
      }
    } catch (err) {
      console.error('Biometric auth failed:', err);
    } finally {
      setBiometricLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex bg-[var(--md-sys-color-background)] overflow-hidden relative">
      {/* 动态背景装饰 */}
      <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-[var(--md-sys-color-primary)] opacity-10 blur-[120px] rounded-full animate-pulse" />
      <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-[var(--md-sys-color-secondary)] opacity-10 blur-[120px] rounded-full" />

      {/* 左侧展示区域 - 仅在桌面端显示 */}
      <div className="hidden lg:flex lg:w-1/2 flex-col justify-center px-20 relative z-10 border-r border-[var(--md-sys-color-outline-variant)]">
        <div className="max-w-lg">
          <div className="mb-12 relative inline-block">
            <div className="w-20 h-20 rounded-3xl bg-[var(--md-sys-color-primary)] flex items-center justify-center shadow-2xl shadow-[var(--md-sys-color-primary)]/20">
              <Sparkles size={40} className="text-white" />
            </div>
            <div className="absolute -inset-4 bg-[var(--md-sys-color-primary)] opacity-20 blur-2xl rounded-full -z-10" />
          </div>
          
          <h1 className="text-7xl font-black tracking-tighter text-[var(--md-sys-color-on-background)] mb-6 leading-tight">
            Endgame <span className="text-[var(--md-sys-color-primary)]">OS</span>
          </h1>
          
          <p className="text-xl text-[var(--md-sys-color-on-surface-variant)] opacity-70 mb-12 max-w-md leading-relaxed">
            你的数字分身，帮助你保持对终局愿景的聚焦。
          </p>
          
          <div className="space-y-6">
            <div className="flex items-center gap-6 p-4 rounded-2xl border border-[var(--md-sys-color-outline-variant)] bg-[var(--md-sys-color-surface-container-low)]/50">
              <div className="w-12 h-12 rounded-xl bg-[var(--md-sys-color-primary-container)] flex items-center justify-center text-[var(--md-sys-color-on-primary-container)]">
                <Shield size={24} />
              </div>
              <div>
                <h3 className="font-bold text-[var(--md-sys-color-on-surface)]">H3 能量系统</h3>
                <p className="text-sm opacity-60">四维能量平衡与监控</p>
              </div>
            </div>
            <div className="flex items-center gap-6 p-4 rounded-2xl border border-[var(--md-sys-color-outline-variant)] bg-[var(--md-sys-color-surface-container-low)]/50">
              <div className="w-12 h-12 rounded-xl bg-[var(--md-sys-color-secondary-container)] flex items-center justify-center text-[var(--md-sys-color-on-secondary-container)]">
                <Sparkles size={24} />
              </div>
              <div>
                <h3 className="font-bold text-[var(--md-sys-color-on-surface)]">AI 数字分身</h3>
                <p className="text-sm opacity-60">个性化心智成长模型</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 右侧表单区域 */}
      <div className="flex-1 flex items-center justify-center p-6 relative z-10">
        <div className="w-full max-w-[440px]">
          {/* 移动端 Logo */}
          <div className="lg:hidden flex items-center gap-4 justify-center mb-12">
            <div className="w-12 h-12 rounded-2xl bg-[var(--md-sys-color-primary)] flex items-center justify-center">
              <Sparkles size={24} className="text-white" />
            </div>
            <h1 className="text-3xl font-black tracking-tighter">Endgame OS</h1>
          </div>

          <GlassCard className="p-10 border-[var(--md-sys-color-outline-variant)]">
            <div className="text-center mb-10">
              <h2 className="text-3xl font-black tracking-tighter mb-2 text-[var(--md-sys-color-on-surface)]">
                {isRegister ? '创建账号' : '欢迎回来'}
              </h2>
              <p className="text-[var(--md-sys-color-on-surface-variant)] opacity-60 uppercase text-xs tracking-widest font-bold">
                {isRegister ? '开启你的终局之旅' : '继续你的终局之旅'}
              </p>
            </div>

            {/* 生物识别登录 */}
            {biometricSupported && !isRegister && (
              <div className="mb-8">
                <button
                  onClick={handleBiometricLogin}
                  disabled={biometricLoading}
                  className="w-full flex items-center justify-center gap-3 py-4 rounded-2xl border border-[var(--md-sys-color-outline-variant)] bg-[var(--md-sys-color-surface-container-high)] text-[var(--md-sys-color-on-surface)] font-bold transition-all hover:bg-[var(--md-sys-color-surface-container-highest)]"
                >
                  {biometricLoading ? (
                    <Loader2 size={24} className="animate-spin" />
                  ) : (
                    <Fingerprint size={24} className="text-[var(--md-sys-color-primary)]" />
                  )}
                  <span>使用生物识别登录</span>
                </button>
                <div className="flex items-center gap-4 my-6">
                  <div className="h-[1px] flex-1 bg-[var(--md-sys-color-outline-variant)]" />
                  <span className="text-xs font-bold opacity-30 uppercase tracking-tighter">OR</span>
                  <div className="h-[1px] flex-1 bg-[var(--md-sys-color-outline-variant)]" />
                </div>
              </div>
            )}

            {/* 错误提示 */}
            {error && (
              <div className="mb-6 p-4 rounded-xl bg-[var(--md-sys-color-error-container)] text-[var(--md-sys-color-on-error-container)] text-sm font-medium animate-shake">
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-6">
              {isRegister && (
                <div className="space-y-2">
                  <label className="text-xs font-bold opacity-50 uppercase tracking-widest ml-1">用户名</label>
                  <input
                    type="text"
                    className="w-full px-5 py-4 rounded-2xl bg-[var(--md-sys-color-surface-container-highest)] border border-transparent focus:border-[var(--md-sys-color-primary)] outline-none transition-all text-[var(--md-sys-color-on-surface)]"
                    placeholder="你的名字"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    required={isRegister}
                  />
                </div>
              )}

              <div className="space-y-2">
                <label className="text-xs font-bold opacity-50 uppercase tracking-widest ml-1">邮箱</label>
                <div className="relative">
                  <Mail className="absolute left-5 top-1/2 -translate-y-1/2 opacity-30" size={20} />
                  <input
                    type="email"
                    className="w-full pl-14 pr-5 py-4 rounded-2xl bg-[var(--md-sys-color-surface-container-highest)] border border-transparent focus:border-[var(--md-sys-color-primary)] outline-none transition-all text-[var(--md-sys-color-on-surface)]"
                    placeholder="your@email.com"
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    required
                  />
                </div>
              </div>

              <div className="space-y-2">
                <label className="text-xs font-bold opacity-50 uppercase tracking-widest ml-1">密码</label>
                <div className="relative">
                  <Lock className="absolute left-5 top-1/2 -translate-y-1/2 opacity-30" size={20} />
                  <input
                    type={showPassword ? 'text' : 'password'}
                    className="w-full pl-14 pr-14 py-4 rounded-2xl bg-[var(--md-sys-color-surface-container-highest)] border border-transparent focus:border-[var(--md-sys-color-primary)] outline-none transition-all text-[var(--md-sys-color-on-surface)]"
                    placeholder="••••••••"
                    value={formData.password}
                    onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-5 top-1/2 -translate-y-1/2 opacity-30 hover:opacity-100 transition-opacity"
                  >
                    {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
                  </button>
                </div>
              </div>

              <Button
                type="submit"
                loading={isLoading}
                className="w-full py-8 text-lg font-black tracking-tighter rounded-2xl shadow-xl shadow-[var(--md-sys-color-primary)]/20"
              >
                {isRegister ? '创建账号' : '登录系统'}
                {!isLoading && <ArrowRight size={20} className="ml-2" />}
              </Button>
            </form>

            <div className="mt-8 text-center">
              <button
                type="button"
                onClick={() => {
                  setIsRegister(!isRegister);
                  clearError();
                }}
                className="text-sm font-bold opacity-50 hover:opacity-100 hover:text-[var(--md-sys-color-primary)] transition-all uppercase tracking-widest"
              >
                {isRegister ? '已有账号？立即登录' : '没有账号？立即注册'}
              </button>
            </div>
          </GlassCard>

          <p className="mt-8 text-center text-xs opacity-30 font-medium">
            ENDGAME OS V2.0 &copy; 2026<br/>
            继续即表示你同意我们的服务条款和隐私政策
          </p>
        </div>
      </div>
    </div>
  );
}
