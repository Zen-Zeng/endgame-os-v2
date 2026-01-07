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
        navigate('/dashboard');
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
    <div className="login-page">
      {/* 背景动效 */}
      <div className="login-background">
        <div className="login-gradient" />
        <div className="login-orb login-orb-1" />
        <div className="login-orb login-orb-2" />
        <div className="login-orb login-orb-3" />
        <div className="login-grid" />
      </div>

      {/* 左侧品牌区域 */}
      <div className="login-brand">
        <div className="login-brand-content">
          <div className="login-logo animate-fade-in-up">
            <div className="login-logo-icon">
              <Sparkles size={32} className="text-white" />
            </div>
            <div className="login-logo-glow" />
          </div>
          
          <h1 className="login-title animate-fade-in-up delay-100">
            Endgame OS
          </h1>
          
          <p className="login-tagline animate-fade-in-up delay-200">
            你的数字分身，帮助你保持对终局愿景的聚焦
          </p>
          
          <div className="login-features animate-fade-in-up delay-300">
            <div className="login-feature">
              <div className="login-feature-icon">
                <Shield size={20} />
              </div>
              <div className="login-feature-text">
                <span className="login-feature-title">H3 能量系统</span>
                <span className="login-feature-desc">四维能量监控</span>
              </div>
            </div>
            <div className="login-feature">
              <div className="login-feature-icon">
                <Sparkles size={20} />
              </div>
              <div className="login-feature-text">
                <span className="login-feature-title">AI 数字分身</span>
                <span className="login-feature-desc">个性化智能对话</span>
              </div>
            </div>
            <div className="login-feature">
              <div className="login-feature-icon">
                <ScanFace size={20} />
              </div>
              <div className="login-feature-text">
                <span className="login-feature-title">记忆图谱</span>
                <span className="login-feature-desc">长期知识沉淀</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 右侧表单区域 */}
      <div className="login-form-area">
        <div className="login-form-container animate-fade-in">
          {/* 移动端 Logo */}
          <div className="login-mobile-logo">
            <div className="login-logo-icon login-logo-icon-sm">
              <Sparkles size={24} className="text-white" />
            </div>
            <h1 className="login-mobile-title">Endgame OS</h1>
          </div>

          {/* 表单卡片 */}
          <div className="login-card">
            <div className="login-card-header">
              <h2 className="login-card-title">
                {isRegister ? '创建账号' : '欢迎回来'}
              </h2>
              <p className="login-card-subtitle">
                {isRegister ? '开启你的终局之旅' : '继续你的终局之旅'}
              </p>
            </div>

            {/* 生物识别登录 */}
            {biometricSupported && !isRegister && (
              <div className="login-biometric">
                <button
                  onClick={handleBiometricLogin}
                  disabled={biometricLoading}
                  className="login-biometric-btn"
                >
                  {biometricLoading ? (
                    <Loader2 size={24} className="animate-spin" />
                  ) : (
                    <Fingerprint size={24} />
                  )}
                  <span>使用生物识别登录</span>
                </button>
                <div className="login-divider">
                  <span>或使用密码登录</span>
                </div>
              </div>
            )}

            {/* 错误提示 */}
            {error && (
              <div className="login-error animate-fade-in">
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit} className="login-form">
              {/* 用户名（仅注册） */}
              {isRegister && (
                <div className="form-group animate-fade-in-up">
                  <label className="form-label">用户名</label>
                  <input
                    type="text"
                    className="form-input"
                    placeholder="你的名字"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    required={isRegister}
                  />
                </div>
              )}

              {/* 邮箱 */}
              <div className="form-group">
                <label className="form-label">邮箱</label>
                <div className="form-input-wrapper">
                  <Mail className="form-input-icon" size={20} />
                  <input
                    type="email"
                    className="form-input form-input-with-icon"
                    placeholder="your@email.com"
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    required
                  />
                </div>
              </div>

              {/* 密码 */}
              <div className="form-group">
                <label className="form-label">密码</label>
                <div className="form-input-wrapper">
                  <Lock className="form-input-icon" size={20} />
                  <input
                    type={showPassword ? 'text' : 'password'}
                    className="form-input form-input-with-icon"
                    placeholder="••••••••"
                    value={formData.password}
                    onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="form-input-action"
                  >
                    {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
                  </button>
                </div>
              </div>

              {/* 提交按钮 */}
              <button
                type="submit"
                disabled={isLoading}
                className="login-submit-btn"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="animate-spin" size={20} />
                    处理中...
                  </>
                ) : (
                  <>
                    {isRegister ? '创建账号' : '登录'}
                    <ArrowRight size={20} />
                  </>
                )}
              </button>
            </form>

            {/* 切换登录/注册 */}
            <div className="login-switch">
              <button
                type="button"
                onClick={() => {
                  setIsRegister(!isRegister);
                  clearError();
                }}
                className="login-switch-btn"
              >
                {isRegister ? '已有账号？立即登录' : '没有账号？立即注册'}
              </button>
            </div>
          </div>

          {/* 底部信息 */}
          <p className="login-footer">
            继续即表示你同意我们的服务条款和隐私政策
          </p>
        </div>
      </div>
    </div>
  );
}
