/**
 * API 服务层
 * 封装具体业务逻辑的 API 调用
 */
import api from '../lib/api';

export interface TaskStatus {
  id: string;
  type?: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress: number;
  message?: string;
  error?: string;
  result?: any;
  created_at?: string;
}

export const memoryApi = {
  // 获取图谱数据
  getGraph: (params?: any) => api.get('/memory/graph', { params }),
  
  // 训练文件
  trainFiles: (filenames: string[]) => api.post<{ task_id: string }>('/memory/train', { filenames }),
  
  // 获取任务状态
  getTaskStatus: (taskId: string) => api.get<TaskStatus>(`/memory/tasks/${taskId}`),
  
  // 清除记忆
  clearMemory: () => api.delete('/memory/clear'),
};

export const archivesApi = {
  getFiles: (params?: any) => api.get('/archives/files', { params }),
  uploadFile: (formData: FormData) => api.post('/archives/upload', formData),
  splitFile: (fileId: string) => api.post(`/archives/split/${fileId}`),
  deleteFile: (fileId: string) => api.delete(`/archives/files/${fileId}`),
};

export default {
  memory: memoryApi,
  archives: archivesApi,
};
