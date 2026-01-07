/**
 * API 客户端
 * 处理与 Brain 后端的通信
 */

const API_BASE = '/api/v1';

interface RequestOptions extends RequestInit {
  token?: string;
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
        this.token = parsed.state?.token || null;
      }
    } catch (e) {
      console.error('Failed to load token from storage:', e);
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

    const token = options?.token || this.token;
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    return headers;
  }

  async request<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    
    // 权限校验拦截 (排除登录和注册接口)
    const isPublic = endpoint.includes('/auth/login') || endpoint.includes('/auth/register');
    const token = options.token || this.token;
    
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
    return this.request<T>(endpoint, {
      ...options,
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  async patch<T>(endpoint: string, data?: unknown, options?: RequestOptions): Promise<T> {
    return this.request<T>(endpoint, {
      ...options,
      method: 'PATCH',
      body: data ? JSON.stringify(data) : undefined,
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

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const text = decoder.decode(value);
      const lines = text.split('\n');

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6));
            onChunk(data);
          } catch {
            // Ignore parse errors
          }
        }
      }
    }
  }
}

export const api = new ApiClient();
export default api;

