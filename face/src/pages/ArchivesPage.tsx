/**
 * 档案库页面
 * 按照原型图 Layout 9 设计
 */
import { useState, useEffect } from 'react';
import {
  Search,
  Upload,
  FolderOpen,
  File,
  FileText,
  Image,
  MoreVertical,
  Grid,
  List,
  Plus,
  Loader2,
} from 'lucide-react';
import GlassCard from '../components/layout/GlassCard';
import api from '../lib/api';
import clsx from 'clsx';

// 模拟文件数据
const mockFiles = [
  { id: '1', name: '项目计划.md', type: 'markdown', size: '12 KB', date: '今天' },
  { id: '2', name: '会议记录.txt', type: 'text', size: '8 KB', date: '昨天' },
  { id: '3', name: '设计稿.png', type: 'image', size: '2.4 MB', date: '3天前' },
  { id: '4', name: '数据分析.csv', type: 'csv', size: '156 KB', date: '上周' },
  { id: '5', name: '思考笔记.md', type: 'markdown', size: '4 KB', date: '上周' },
];

const fileTypeIcons: Record<string, typeof File> = {
  markdown: FileText,
  text: FileText,
  image: Image,
  csv: File,
  default: File,
};

export default function ArchivesPage() {
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [searchQuery, setSearchQuery] = useState('');
  const [files, setFiles] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isUploading, setIsUploading] = useState(false);

  // 加载文件列表
  const fetchFiles = async () => {
    try {
      setIsLoading(true);
      const data: any = await api.get('/archives/files');
      setFiles(data);
    } catch (error) {
      console.error('获取文件失败:', error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchFiles();
  }, []);

  // 处理文件上传
  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    try {
      setIsUploading(true);
      const formData = new FormData();
      formData.append('file', file);
      
      await api.post('/archives/upload', formData);
      fetchFiles(); // 刷新列表
    } catch (error) {
      console.error('上传失败:', error);
      alert('上传失败');
    } finally {
      setIsUploading(false);
    }
  };

  // 格式化文件大小
  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  // 格式化日期
  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    
    if (diff < 24 * 3600 * 1000) return '今天';
    if (diff < 48 * 3600 * 1000) return '昨天';
    return date.toLocaleDateString();
  };

  const filteredFiles = files.filter((file) =>
    file.original_name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="min-h-screen p-8">
      {/* 页面标题和操作 */}
      <header className="mb-8 animate-fade-in-down">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="font-display text-3xl font-bold text-[var(--color-text-primary)] mb-2">
              档案库
            </h1>
            <p className="text-[var(--color-text-secondary)]">
              管理你的文件和知识资料
            </p>
          </div>
          <label className={clsx("btn btn-primary cursor-pointer", isUploading && "opacity-50 pointer-events-none")}>
            {isUploading ? <Loader2 className="animate-spin" size={18} /> : <Upload size={18} />}
            {isUploading ? '上传中...' : '上传文件'}
            <input type="file" className="hidden" onChange={handleFileUpload} disabled={isUploading} />
          </label>
        </div>

        {/* 搜索和视图切换 */}
        <div className="flex items-center gap-4">
          <div className="flex-1 relative">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-[var(--color-text-muted)]" />
            <input
              type="text"
              placeholder="搜索文件..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="input w-full pl-12"
            />
          </div>
          <div className="flex bg-[var(--color-bg-card)] rounded-lg p-1">
            <button
              onClick={() => setViewMode('grid')}
              className={clsx(
                'p-2 rounded-md transition-colors',
                viewMode === 'grid'
                  ? 'bg-[var(--color-primary)] text-white'
                  : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]'
              )}
            >
              <Grid size={18} />
            </button>
            <button
              onClick={() => setViewMode('list')}
              className={clsx(
                'p-2 rounded-md transition-colors',
                viewMode === 'list'
                  ? 'bg-[var(--color-primary)] text-white'
                  : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]'
              )}
            >
              <List size={18} />
            </button>
          </div>
        </div>
      </header>

      {/* 文件列表 */}
      {isLoading ? (
        <div className="flex flex-col items-center justify-center py-20">
          <Loader2 className="w-12 h-12 text-[var(--color-primary)] animate-spin mb-4" />
          <p className="text-[var(--color-text-secondary)]">加载中...</p>
        </div>
      ) : filteredFiles.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 bg-[var(--color-bg-card)] rounded-2xl border border-dashed border-[var(--color-border)]">
          <FolderOpen size={48} className="text-[var(--color-text-muted)] mb-4" />
          <p className="text-[var(--color-text-secondary)]">
            {searchQuery ? '未找到匹配文件' : '档案库空空如也'}
          </p>
        </div>
      ) : viewMode === 'grid' ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-6">
          {filteredFiles.map((file) => {
            const Icon = fileTypeIcons[file.file_type] || fileTypeIcons.default;
            return (
              <GlassCard
                key={file.id}
                className="group relative p-4 hover:border-[var(--color-primary)] transition-all cursor-pointer"
              >
                <div className="flex flex-col items-center text-center">
                  <div className="w-16 h-16 rounded-xl bg-[var(--color-bg-page)] flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                    <Icon size={32} className="text-[var(--color-primary)]" />
                  </div>
                  <h3 className="font-medium text-[var(--color-text-primary)] truncate w-full mb-1">
                    {file.original_name}
                  </h3>
                  <div className="flex items-center gap-2 text-xs text-[var(--color-text-muted)]">
                    <span>{formatFileSize(file.file_size)}</span>
                    <span>•</span>
                    <span>{formatDate(file.created_at)}</span>
                  </div>
                </div>
                <button className="absolute top-2 right-2 p-1 opacity-0 group-hover:opacity-100 transition-opacity text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]">
                  <MoreVertical size={16} />
                </button>
              </GlassCard>
            );
          })}
        </div>
      ) : (
        <div className="bg-[var(--color-bg-card)] rounded-2xl border border-[var(--color-border)] overflow-hidden">
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-[var(--color-border)] bg-[var(--color-bg-page)]/50">
                <th className="px-6 py-4 font-medium text-[var(--color-text-secondary)]">文件名</th>
                <th className="px-6 py-4 font-medium text-[var(--color-text-secondary)]">大小</th>
                <th className="px-6 py-4 font-medium text-[var(--color-text-secondary)]">日期</th>
                <th className="px-6 py-4"></th>
              </tr>
            </thead>
            <tbody>
              {filteredFiles.map((file) => {
                const Icon = fileTypeIcons[file.file_type] || fileTypeIcons.default;
                return (
                  <tr
                    key={file.id}
                    className="border-b border-[var(--color-border)] last:border-0 hover:bg-[var(--color-primary)]/5 transition-colors cursor-pointer group"
                  >
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <Icon size={20} className="text-[var(--color-primary)]" />
                        <span className="font-medium text-[var(--color-text-primary)]">
                          {file.original_name}
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-[var(--color-text-secondary)]">
                      {formatFileSize(file.file_size)}
                    </td>
                    <td className="px-6 py-4 text-[var(--color-text-secondary)]">
                      {formatDate(file.created_at)}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <button className="p-1 opacity-0 group-hover:opacity-100 transition-opacity text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]">
                        <MoreVertical size={18} />
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

