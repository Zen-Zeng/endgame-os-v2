import { useEffect, useState, useRef } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import api from '../lib/api';
import { ZoomIn, ZoomOut, RefreshCw, Maximize2, X, Activity, Share2 } from 'lucide-react';
import Button from './ui/Button';
import GlassCard from './layout/GlassCard';

interface Node {
  id: string;
  group: string;
  label: string;
  type?: string;
  name?: string;
  data?: any;
  x?: number;
  y?: number;
}

interface Link {
  source: any;
  target: any;
  type: string;
  data: any;
}

interface GraphData {
  nodes: Node[];
  links: Link[];
  total_nodes?: number;
  total_links?: number;
}

interface MemoryGraphProps {
  onClose?: () => void;
}

export default function MemoryGraph({ onClose }: MemoryGraphProps) {
  const [graphData, setGraphData] = useState<GraphData>({ nodes: [], links: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);
  const [dimensions, setDimensions] = useState({ width: 0, height: 0 });
  const graphRef = useRef<any>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // 监听容器大小变化
  useEffect(() => {
    if (containerRef.current) {
      const updateSize = () => {
        if (containerRef.current) {
          setDimensions({
            width: containerRef.current.clientWidth,
            height: containerRef.current.clientHeight
          });
        }
      };

      const resizeObserver = new ResizeObserver(updateSize);
      resizeObserver.observe(containerRef.current);
      updateSize();

      return () => resizeObserver.disconnect();
    }
  }, []);

  // 获取解析后的颜色 (用于 Canvas)
  const resolveColor = (colorStr: string): string => {
    if (colorStr.startsWith('var(')) {
      const varName = colorStr.match(/var\(([^)]+)\)/)?.[1];
      if (varName && typeof window !== 'undefined') {
        const value = getComputedStyle(document.documentElement).getPropertyValue(varName).trim();
        if (value) return value;
      }
    }
    
    // 回退颜色
    const fallbacks: { [key: string]: string } = {
      '--md-sys-color-primary': '#D0BCFF',
      '--md-sys-color-secondary': '#CCC2DC',
      '--md-sys-color-tertiary': '#EFB8C8',
      '--md-sys-color-error': '#F2B8B5',
      '--md-sys-color-primary-fixed': '#EADDFF',
      '--md-sys-color-secondary-fixed': '#E8DEF8',
      '--md-sys-color-outline': '#938F99'
    };
    
    const varName = colorStr.match(/var\(([^)]+)\)/)?.[1];
    return (varName && fallbacks[varName]) || '#938F99';
  };

  // 节点颜色映射 - 与 MemoryPage.tsx 中的 nodeTypes 同步
  const getNodeColor = (node: Node): string => {
    const colorMap: { [key: string]: string } = {
      'User': 'var(--md-sys-color-primary)',
      'Goal': 'var(--md-sys-color-secondary)',
      'Project': 'var(--md-sys-color-tertiary)',
      'Task': 'var(--md-sys-color-error)',
      'Log': 'var(--md-sys-color-primary-fixed)',
      'Concept': 'var(--md-sys-color-secondary-fixed)',
      '1': 'var(--md-sys-color-primary)', 
      '2': 'var(--md-sys-color-secondary)',
      '3': 'var(--md-sys-color-tertiary)',
      '4': 'var(--md-sys-color-error)',
      '5': 'var(--md-sys-color-primary-fixed)',
      'Unknown': 'var(--md-sys-color-outline)'
    };
    const groupKey = node.group?.toString() || node.type || 'Unknown';
    return colorMap[groupKey] || colorMap['Unknown'];
  };

  // 节点大小映射
  const getNodeSize = (node: Node): number => {
    const sizeMap: { [key: string]: number } = {
      'User': 12,
      'Goal': 10,
      'Project': 8,
      'Task': 7,
      'Log': 5,
      'Concept': 4,
      '1': 12,
      '2': 10,
      '3': 8,
      '4': 7,
      '5': 5
    };
    const groupKey = node.group?.toString() || node.type || 'Unknown';
    return sizeMap[groupKey] || 5;
  };

  const loadGraphData = async () => {
    try {
      setLoading(true);
      setError(null);
      const data: any = await api.get('/memory/graph');
      const result = data.data || data;
      const nodes = Array.isArray(result.nodes) ? result.nodes : [];
      const links = Array.isArray(result.links) ? result.links : [];
      
      const processedNodes = nodes.map((node: any, index: number) => ({
        ...node,
        id: node.id?.toString() || `node-${index}`,
        group: node.group?.toString() || 'Unknown',
        label: node.name || node.label || `Node ${index}`,
        type: node.type,
        data: node.data || { "描述": node.content || "无详细内容" }
      }));

      const processedLinks = links.map((link: any) => ({
        ...link,
        source: link.source?.toString(),
        target: link.target?.toString()
      }));
      
      setGraphData({
        nodes: processedNodes,
        links: processedLinks,
        total_nodes: processedNodes.length,
        total_links: processedLinks.length
      });
    } catch (err) {
      console.error('加载图数据失败:', err);
      setError(err instanceof Error ? err.message : '未知错误');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadGraphData();
  }, []);

  // 当数据加载完成后，强制图谱自适应视野
  useEffect(() => {
    if (graphData.nodes.length > 0 && graphRef.current) {
      setTimeout(() => {
        graphRef.current.zoomToFit(400);
      }, 500);
    }
  }, [graphData]);

  const handleNodeClick = (node: Node) => {
    setSelectedNode(node);
  };

  const handleBackgroundClick = () => {
    setSelectedNode(null);
  };

  const handleRefresh = () => {
    loadGraphData();
  };

  const handleZoomIn = () => graphRef.current?.zoom(1.2);
  const handleZoomOut = () => graphRef.current?.zoom(0.8);
  const handleResetZoom = () => graphRef.current?.zoomToFit(400);

  // 颜色处理工具
  const applyAlpha = (color: string, alpha: number): string => {
    if (color.startsWith('#')) {
      const r = parseInt(color.slice(1, 3), 16);
      const g = parseInt(color.slice(3, 5), 16);
      const b = parseInt(color.slice(5, 7), 16);
      return `rgba(${r}, ${g}, ${b}, ${alpha})`;
    }
    if (color.startsWith('var(')) {
      const resolved = resolveColor(color);
      return applyAlpha(resolved, alpha);
    }
    return color;
  };

  if (loading) {
    return (
      <div className="h-full w-full flex flex-col bg-[var(--md-sys-color-surface-container-low)]">
        <div className="flex items-center justify-between p-4 border-b border-[var(--md-sys-color-outline-variant)]">
          <h2 className="text-lg font-bold text-[var(--md-sys-color-on-surface)]">知识图谱可视化</h2>
          {onClose && <Button variant="text" onClick={onClose} icon={<X size={18} />} />}
        </div>
        <div className="flex-1 flex flex-col items-center justify-center">
          <div className="w-12 h-12 border-4 border-[var(--md-sys-color-primary-container)] border-t-[var(--md-sys-color-primary)] rounded-full animate-spin mb-4"></div>
          <p className="text-[var(--md-sys-color-on-surface-variant)]">加载图数据中...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="h-full w-full flex flex-col bg-[var(--md-sys-color-surface-container-low)]">
        <div className="flex items-center justify-between p-4 border-b border-[var(--md-sys-color-outline-variant)]">
          <h2 className="text-lg font-bold text-[var(--md-sys-color-on-surface)]">知识图谱可视化</h2>
          {onClose && <Button variant="text" onClick={onClose} icon={<X size={18} />} />}
        </div>
        <div className="flex-1 flex flex-col items-center justify-center p-8">
          <p className="text-[var(--md-sys-color-error)] mb-4 text-center">加载失败: {error}</p>
          <Button variant="filled" onClick={handleRefresh} icon={<RefreshCw size={18} />}>
            重试
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full w-full flex flex-col relative bg-white/40 backdrop-blur-sm overflow-hidden rounded-[var(--md-sys-shape-corner-extra-large)] border border-white/20 shadow-inner">
      {/* 图谱 Header */}
      <div className="absolute top-0 left-0 right-0 z-10 flex items-center justify-between p-6 bg-gradient-to-b from-white/60 to-transparent pointer-events-none">
        <div className="flex flex-col">
          <h2 className="text-xl font-bold text-[var(--md-sys-color-on-surface)] flex items-center gap-2 drop-shadow-sm">
            <Share2 size={24} className="text-[var(--md-sys-color-primary)]" />
            知识图谱可视化
          </h2>
          <div className="flex items-center gap-3 mt-2">
            <span className="text-[10px] font-bold text-[var(--md-sys-color-on-surface-variant)] bg-black/5 px-2 py-0.5 rounded-full flex items-center gap-1 uppercase tracking-wider border border-black/5">
              <Activity size={10} />
              节点: {graphData.nodes?.length || 0}
            </span>
            <span className="text-[10px] font-bold text-[var(--md-sys-color-on-surface-variant)] bg-black/5 px-2 py-0.5 rounded-full uppercase tracking-wider border border-black/5">
              连线: {graphData.links?.length || 0}
            </span>
          </div>
        </div>
        
        <div className="flex items-center gap-2 pointer-events-auto">
          <Button variant="tonal" onClick={handleRefresh} icon={<RefreshCw size={18} />} className="bg-black/5 hover:bg-black/10 border-none text-[var(--md-sys-color-on-surface)] h-10 w-10 p-0 rounded-full" />
          <Button variant="tonal" onClick={handleZoomIn} icon={<ZoomIn size={18} />} className="bg-black/5 hover:bg-black/10 border-none text-[var(--md-sys-color-on-surface)] h-10 w-10 p-0 rounded-full" />
          <Button variant="tonal" onClick={handleZoomOut} icon={<ZoomOut size={18} />} className="bg-black/5 hover:bg-black/10 border-none text-[var(--md-sys-color-on-surface)] h-10 w-10 p-0 rounded-full" />
          <Button variant="tonal" onClick={handleResetZoom} icon={<Maximize2 size={18} />} className="bg-black/5 hover:bg-black/10 border-none text-[var(--md-sys-color-on-surface)] h-10 w-10 p-0 rounded-full" />
          {onClose && <Button variant="tonal" onClick={onClose} icon={<X size={18} />} className="bg-black/5 hover:bg-black/10 border-none text-[var(--md-sys-color-on-surface)] h-10 w-10 p-0 ml-2 rounded-full" />}
        </div>
      </div>

      {/* 节点详情浮窗 */}
        {selectedNode && (
          <div className="absolute bottom-8 left-8 z-20 w-80 pointer-events-auto animate-in fade-in slide-in-from-bottom-4 duration-300">
            <GlassCard variant="elevated" padding="md" className="border border-white/20 shadow-2xl backdrop-blur-2xl bg-white/70">
              <div className="flex items-start justify-between mb-4">
                <div>
                  <span 
                    className="text-[10px] font-bold uppercase tracking-widest px-2 py-0.5 rounded-full mb-2 inline-block border border-current"
                    style={{ backgroundColor: `${getNodeColor(selectedNode)}20`, color: getNodeColor(selectedNode) }}
                  >
                    {selectedNode.group}
                  </span>
                  <h3 className="text-lg font-bold text-[var(--md-sys-color-on-surface)] leading-tight">{selectedNode.label}</h3>
                </div>
                <button onClick={() => setSelectedNode(null)} className="text-[var(--md-sys-color-on-surface-variant)]/40 hover:text-[var(--md-sys-color-on-surface)] transition-colors p-1">
                  <X size={18} />
                </button>
              </div>
              
              <div className="space-y-4 max-h-60 overflow-y-auto pr-2 scrollbar-hide">
                {selectedNode.data && Object.entries(selectedNode.data).map(([key, value]) => (
                  <div key={key} className="text-xs">
                    <span className="text-[var(--md-sys-color-on-surface-variant)]/60 font-medium block mb-1 uppercase tracking-tighter">{key}</span>
                    <span className="text-[var(--md-sys-color-on-surface)] block break-words bg-black/5 p-2 rounded border border-black/5 leading-relaxed">{String(value)}</span>
                  </div>
                ))}
              {(!selectedNode.data || Object.keys(selectedNode.data).length === 0) && (
                <div className="flex flex-col items-center justify-center py-6 text-white/20 italic">
                  <Activity size={24} className="mb-2 opacity-10" />
                  <p className="text-xs">暂无详细元数据</p>
                </div>
              )}
            </div>
          </GlassCard>
        </div>
      )}

      {/* 核心图谱 */}
      <div ref={containerRef} className="flex-1 cursor-grab active:cursor-grabbing overflow-hidden">
        {dimensions.width > 0 && dimensions.height > 0 && (
          <ForceGraph2D
            ref={graphRef}
            graphData={graphData}
            width={dimensions.width}
            height={dimensions.height}
            nodeLabel="label"
            nodeColor={(node: any) => resolveColor(getNodeColor(node))}
            nodeRelSize={1}
            nodeVal={getNodeSize}
            linkColor={() => 'rgba(0, 0, 0, 0.08)'}
            linkWidth={1}
            linkDirectionalParticles={1}
            linkDirectionalParticleSpeed={0.005}
            linkDirectionalParticleWidth={1.5}
            backgroundColor="transparent"
            onNodeClick={handleNodeClick}
            onBackgroundClick={handleBackgroundClick}
            nodeCanvasObject={(node: any, ctx, globalScale) => {
              if (node.x === undefined || node.y === undefined) return;
              
              const label = node.label;
              const fontSize = 12 / globalScale;
              const color = getNodeColor(node);
              const size = getNodeSize(node);

              // 绘制节点发光层
              ctx.beginPath();
              ctx.arc(node.x, node.y, size * 1.5, 0, 2 * Math.PI, false);
              const gradient = ctx.createRadialGradient(node.x, node.y, 0, node.x, node.y, size * 1.5);
              gradient.addColorStop(0, applyAlpha(color, 0.4));
              gradient.addColorStop(1, applyAlpha(color, 0));
              ctx.fillStyle = gradient;
              ctx.fill();

              // 绘制节点主体
              ctx.beginPath();
              ctx.arc(node.x, node.y, size, 0, 2 * Math.PI, false);
              ctx.fillStyle = color;
              ctx.fill();

              // 绘制选中高亮
              if (selectedNode?.id === node.id) {
                ctx.beginPath();
                ctx.arc(node.x, node.y, size * 1.8, 0, 2 * Math.PI, false);
                ctx.strokeStyle = 'rgba(255, 255, 255, 0.8)';
                ctx.lineWidth = 2 / globalScale;
                ctx.stroke();
              }

              // 绘制文字 (高缩放比例时显示)
              if (globalScale > 2) {
                ctx.font = `500 ${fontSize}px var(--md-ref-typeface-plain)`;
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                ctx.fillStyle = 'rgba(255, 255, 255, 0.9)';
                ctx.fillText(label, node.x, node.y + size + fontSize + 4);
              }
            }}
          />
        )}
      </div>
    </div>
  );
}
