/**
 * API 客户端
 * 处理与 Brain 后端的通信
 */

// 自动检测基础 URL
// 如果在 5173 (Vite) 下运行，利用 vite.config.ts 的代理
// 如果在 8888 (FastAPI) 下运行，直接使用相对路径
const API_BASE = '/api/v1';

interface RequestOptions extends RequestInit {
  token?: string;
  params?: Record<string, string | number | boolean | undefined>;
}

class ApiClient {
  private baseUrl: string;
  private token: string | null = null;

  constructor(baseUrl: string = API_BASE) {
    this.baseUrl = baseUrl;
    // 从 Zustand 的持久化存储中读取 token
    try {
      const authData = localStorage.getItem('endgame-auth');
      if (authData) {
        const parsed = JSON.parse(authData);
        // Zustand persist 存储结构是 { state: { ..., token: "..." }, version: 0 }
        this.token = parsed.state?.token || null;
      }
    } catch (e) {
      console.error('Failed to load token from storage:', e);
    }
  }

  // 辅助方法：手动更新 token（用于 store 中登录成功后立即更新）
  updateToken() {
    try {
      const authData = localStorage.getItem('endgame-auth');
      if (authData) {
        const parsed = JSON.parse(authData);
        this.token = parsed.state?.token || null;
      }
    } catch (e) {
      console.error('Failed to update token:', e);
    }
  }

  setToken(token: string | null) {
    this.token = token;
    // 注意：Zustand 的 persist 会处理自己的 localStorage，
    // 这里我们同步一份简单的 'token' 键供其他可能的需求使用
    if (token) {
      localStorage.setItem('token', token);
    } else {
      localStorage.removeItem('token');
    }
  }

  private getHeaders(options?: RequestOptions): HeadersInit {
    const headers: Record<string, string> = {};

    // 优先使用选项中的 token，否则从 localStorage 实时获取最新的 token
    let token = options?.token;
    
    if (!token) {
      try {
        const authData = localStorage.getItem('endgame-auth');
        if (authData) {
          const parsed = JSON.parse(authData);
          token = parsed.state?.token || null;
        }
      } catch (e) {
        console.error('Failed to load token for request:', e);
      }
    }

    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    return headers;
  }

  async request<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
    let url = `${this.baseUrl}${endpoint}`;
    
    // 处理查询参数
    if (options.params) {
      const searchParams = new URLSearchParams();
      Object.entries(options.params).forEach(([key, value]) => {
        if (value !== undefined) {
          searchParams.append(key, String(value));
        }
      });
      const queryString = searchParams.toString();
      if (queryString) {
        url += (url.includes('?') ? '&' : '?') + queryString;
      }
    }
    
    // 权限校验拦截 (排除登录和注册接口)
    const isPublic = endpoint.includes('/auth/login') || endpoint.includes('/auth/register');
    
    // 获取最新 token
    let token = options.token;
    if (!token) {
      try {
        const authData = localStorage.getItem('endgame-auth');
        if (authData) {
          const parsed = JSON.parse(authData);
          token = parsed.state?.token || null;
        }
      } catch (e) {
        console.error('Failed to load token for request check:', e);
      }
    }
    
    if (!isPublic && !token) {
      throw new Error('未登录或登录已过期');
    }

    const headers = this.getHeaders(options);

    const response = await fetch(url, {
      ...options,
      headers: {
        ...headers,
        ...(options.headers || {}),
      },
    });

    if (!response.ok) {
      const errorText = await response.text();
      let errorMessage = `HTTP ${response.status}`;
      try {
        const errorJson = JSON.parse(errorText);
        errorMessage = errorJson.detail || JSON.stringify(errorJson);
      } catch {
        errorMessage = errorText || errorMessage;
      }
      throw new Error(errorMessage);
    }

    return response.json();
  }

  async get<T>(endpoint: string, options?: RequestOptions): Promise<T> {
    return this.request<T>(endpoint, { ...options, method: 'GET' });
  }

  async post<T>(endpoint: string, data?: unknown, options?: RequestOptions): Promise<T> {
    const isFormData = data instanceof FormData;
    const headers: Record<string, string> = {};
    
    // 如果是 FormData，不要手动设置 Content-Type，让浏览器自动设置以包含 boundary
    if (!isFormData) {
      headers['Content-Type'] = 'application/json';
    }

    return this.request<T>(endpoint, {
      ...options,
      method: 'POST',
      headers: {
        ...headers,
        ...(options?.headers as Record<string, string> || {}),
      },
      body: isFormData ? (data as FormData) : (data ? JSON.stringify(data) : undefined),
    });
  }

  async put<T>(endpoint: string, data?: unknown, options?: RequestOptions): Promise<T> {
    const isFormData = data instanceof FormData;
    const headers: Record<string, string> = {};
    if (!isFormData) {
      headers['Content-Type'] = 'application/json';
    }

    return this.request<T>(endpoint, {
      ...options,
      method: 'PUT',
      headers: {
        ...headers,
        ...(options?.headers as Record<string, string> || {}),
      },
      body: isFormData ? (data as FormData) : (data ? JSON.stringify(data) : undefined),
    });
  }

  async patch<T>(endpoint: string, data?: unknown, options?: RequestOptions): Promise<T> {
    const isFormData = data instanceof FormData;
    const headers: Record<string, string> = {};
    if (!isFormData) {
      headers['Content-Type'] = 'application/json';
    }

    return this.request<T>(endpoint, {
      ...options,
      method: 'PATCH',
      headers: {
        ...headers,
        ...(options?.headers as Record<string, string> || {}),
      },
      body: isFormData ? (data as FormData) : (data ? JSON.stringify(data) : undefined),
    });
  }

  async delete<T>(endpoint: string, options?: RequestOptions): Promise<T> {
    return this.request<T>(endpoint, { ...options, method: 'DELETE' });
  }

  // SSE 流式请求
  async stream(
    endpoint: string,
    data: unknown,
    onChunk: (chunk: { type: string; content?: string; message?: unknown }) => void,
    options?: RequestOptions
  ): Promise<void> {
    const url = `${this.baseUrl}${endpoint}`;
    const headers = this.getHeaders(options);

    const response = await fetch(url, {
      method: 'POST',
      headers: {
        ...headers,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      const errorText = await response.text();
      let errorMessage = `HTTP ${response.status}`;
      try {
        const errorJson = JSON.parse(errorText);
        errorMessage = errorJson.detail || JSON.stringify(errorJson);
      } catch {
        errorMessage = errorText || errorMessage;
      }
      throw new Error(errorMessage);
    }

    const reader = response.body?.getReader();
    if (!reader) {
      throw new Error('No response body');
    }

    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      
      // 保留最后一行（可能不完整）
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.trim() === '') continue;
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6));
            onChunk(data);
          } catch (e) {
            console.warn('SSE Parse Error:', e, line);
          }
        }
      }
    }
  }
}

export const api = new ApiClient();
export default api;

