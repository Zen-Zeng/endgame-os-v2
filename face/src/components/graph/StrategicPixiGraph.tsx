import { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import * as d3 from 'd3-force';
import { useStrategicData } from './useStrategicData';
import type { StrategicNode } from './useStrategicData';

// M3 语义色配置 (High Contrast)
const NODE_STYLES: Record<string, { color: string, borderColor: string }> = {
  Self:    { color: '#D0BCFF', borderColor: '#6750A4' }, // Primary
  Vision:  { color: '#FFB4AB', borderColor: '#93000A' }, // Error
  Goal:    { color: '#FFD8E4', borderColor: '#8C1D18' }, // Tertiary Container
  Project: { color: '#E8DEF8', borderColor: '#65558F' }, // Secondary Container
  Task:    { color: '#E6E1E5', borderColor: '#484649' }, // Surface Variant
  Person:  { color: '#C2E7FF', borderColor: '#004A77' }, // Info
  Concept: { color: '#C4EED0', borderColor: '#0F5223' }, // Success
  Insight: { color: '#FFF4B4', borderColor: '#735C00' }  // Warning/Insight
};

interface StrategicPixiGraphProps {
  viewType?: 'global' | 'strategic' | 'people' | 'staging';
  refreshKey?: number;
  alignmentThreshold?: number; // Phase 4
  showImplicitLinks?: boolean; // Phase 4
  onMergeNodes?: (sourceId: string, targetId: string) => void;
  onNodeClick?: (node: StrategicNode) => void;
}

const StrategicPixiGraph = ({ 
  viewType = 'strategic',
  refreshKey = 0,
  alignmentThreshold = 0,
  showImplicitLinks = false,
  onMergeNodes,
  onNodeClick
}: StrategicPixiGraphProps) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const graphRef = useRef<any>(null);
  const { data, loading, error, refresh } = useStrategicData(viewType);

  // 监听外部触发的刷新
  useEffect(() => {
    refresh();
  }, [viewType, refreshKey, refresh]);
  
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });
  const [hoverNode, setHoverNode] = useState<StrategicNode | null>(null);
  const [tooltipPos, setTooltipPos] = useState({ x: 0, y: 0 });
  
  // Theme colors from CSS variables
  const [themeColors, setThemeColors] = useState({
    background: '#000000',
    text: '#ffffff',
    grid: '#333333'
  });

  // Custom Forces for Strategic Compass Layout

  // 过滤数据 (Phase 4)
  const filteredData = useMemo(() => {
    if (!data || !data.nodes) return { nodes: [], links: [] };
    
    // 如果阈值为 0，不进行对齐度过滤
    if (alignmentThreshold === 0) return data;
    
    // 过滤节点
    const validNodes = data.nodes.filter(n => {
        // Self 和 Vision 永远保留
        if (n.type === 'Self' || n.type === 'Vision') return true;
        // 如果节点没有 alignment_score，假设为 0 (或者保留？这里假设过滤掉不达标的)
        const score = (n as any).alignment_score || 0;
        return score >= alignmentThreshold;
    });
    
    const validNodeIds = new Set(validNodes.map(n => n.id));
    
    // 过滤连线
    const validLinks = data.links.filter(l => {
        const sourceId = typeof l.source === 'object' ? (l.source as any).id : l.source;
        const targetId = typeof l.target === 'object' ? (l.target as any).id : l.target;
        return validNodeIds.has(sourceId) && validNodeIds.has(targetId);
    });
    
    return { nodes: validNodes, links: validLinks };
  }, [data, alignmentThreshold]);

  useEffect(() => {
    if (graphRef.current) {
        // Access underlying d3 simulation
        graphRef.current.d3Force('link').distance(80); // 增加连线距离
        
        // Define Custom Forces
        // 使用 d3.forceY() 来强制分层
        graphRef.current.d3Force('y', d3.forceY().y((node: any) => {
            switch(node.type) {
                case 'Self': return 0;
                case 'Vision': return -300; // 愿景在最上方
                case 'Goal': return -150;   // 目标在愿景下方
                case 'Project': return 150; // 项目在下方
                case 'Task': return 300;    // 任务在最下方
                default: return 0;
            }
        }).strength(0.5));

        // 增加电荷力防止重叠
        graphRef.current.d3Force('charge').strength(-150);
    }
  }, []);

  // Alternative: Pre-process data to set fx/fy for strict layout, OR use dagMode if hierarchy is strict.
  // But user wants Compass (Up/Down/Left/Right).
  
  // Let's try to set `fy` (Fixed Y) for specific nodes to enforce layers strictly!
  // This is supported by d3-force natively.
  useEffect(() => {
      if (filteredData.nodes.length > 0) {
          filteredData.nodes.forEach((node: any) => {
              // Enforce "Strategic Compass" Layers
              // Self: Center
              if (node.type === 'Self') {
                  node.fx = 0;
                  node.fy = 0;
              } 
              // Vision: Top
              else if (node.type === 'Vision') {
                  // node.fy = -150; // Strict Y, free X
                  // Let's not fix it strictly, but guide it.
                  // Actually, fixing Y is good for layers.
              }
          });
      }
  }, [filteredData]);


  // Update dimensions on resize
  useEffect(() => {
    const updateDimensions = () => {
      if (containerRef.current) {
        setDimensions({
          width: containerRef.current.clientWidth,
          height: containerRef.current.clientHeight
        });
        
        // Read CSS variables
        const style = getComputedStyle(document.body);
        setThemeColors({
          background: style.getPropertyValue('--md-sys-color-surface-container') || '#1d1b20',
          text: style.getPropertyValue('--md-sys-color-on-surface') || '#e6e1e5',
          grid: style.getPropertyValue('--md-sys-color-outline-variant') || '#49454f'
        });
      }
    };

    window.addEventListener('resize', updateDimensions);
    updateDimensions();
    
    // Observer for container size changes
    const observer = new ResizeObserver(updateDimensions);
    if (containerRef.current) observer.observe(containerRef.current);

    return () => {
      window.removeEventListener('resize', updateDimensions);
      observer.disconnect();
    };
  }, []);

  // Custom Node Rendering
  const paintNode = useCallback((node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
    let style = { ... (NODE_STYLES[node.type] || NODE_STYLES.Concept) };
    const label = node.name || node.label;
    const isHovered = hoverNode?.id === node.id;
    
    // [Strategic Brain] 能量建模可视化 (社交觉醒)
    if (node.type === 'Person' && node.energy_impact !== undefined) {
        if (node.energy_impact > 0) {
            // 赋能型：更亮，带金色边框
            style.color = '#FFD700'; // Gold
            style.borderColor = '#B8860B';
        } else if (node.energy_impact < 0) {
            // 消耗型：灰色，带深红边框
            style.color = '#757575'; 
            style.borderColor = '#B71C1C';
        }
    }

    // 1. Level of Detail (LOD) - 极端缩小时只画简单的圆点
    if (globalScale < 0.4 && !isHovered) {
        ctx.beginPath();
        ctx.arc(node.x, node.y, 3, 0, 2 * Math.PI, false);
        ctx.fillStyle = style.color;
        ctx.fill();
        return;
    }

    const radius = isHovered ? 7 : 5;

    // 2. Draw Shadow/Glow (只在悬停或中等缩放以上绘制，且减少模糊半径)
    if (globalScale > 1.2 || isHovered) {
        ctx.shadowColor = 'rgba(0,0,0,0.2)';
        ctx.shadowBlur = 5 / globalScale;
        ctx.shadowOffsetX = 1 / globalScale;
        ctx.shadowOffsetY = 1 / globalScale;
    }

    // 3. Draw Circle
    ctx.beginPath();
    ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI, false);
    ctx.fillStyle = style.color;
    ctx.fill();

    // 4. Draw Border
    ctx.lineWidth = (isHovered ? 2.5 : 1.5) / globalScale;
    ctx.strokeStyle = style.borderColor;
    ctx.stroke();

    // Reset shadow
    ctx.shadowColor = 'transparent';
    ctx.shadowBlur = 0;

    // 5. Draw Label (LOD - 缩放较小时不绘制文字)
    if (globalScale > 0.7 || isHovered) {
        const fontSize = (isHovered ? 14 : 12) / globalScale;
        ctx.font = `${isHovered ? 'bold' : 'normal'} ${fontSize}px "Inter", system-ui, sans-serif`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'top';
        ctx.fillStyle = themeColors.text;
        
        // 绘制文字背景以便阅读
        if (isHovered) {
            const textWidth = ctx.measureText(label).width;
            ctx.fillStyle = 'rgba(0,0,0,0.6)';
            ctx.fillRect(node.x - textWidth/2 - 2, node.y + radius + 2, textWidth + 4, fontSize + 2);
            ctx.fillStyle = '#ffffff';
        }
        
        ctx.fillText(label, node.x, node.y + radius + 4);
    }
  }, [hoverNode, themeColors]);

  const handleNodeHover = (node: any, prevNode: any) => {
    setHoverNode(node || null);
    if (node && containerRef.current) {
        // Calculate screen position for tooltip (naive approach, can be improved with graph.graph2ScreenCoords)
        // Actually, let's use the pointer event if possible, but ForceGraph doesn't pass the event easily in this callback.
        // We will rely on onNodeHover just setting the node, and a separate mouse move or just center tooltip?
        // Wait, ForceGraph2D doesn't give mouse coords in onNodeHover.
        // We can use graphRef to project coordinates.
    }
  };

  // Track mouse for tooltip
  const handleMouseMove = (e: React.MouseEvent) => {
      if (hoverNode) {
        // Offset a bit
        setTooltipPos({ x: e.nativeEvent.offsetX, y: e.nativeEvent.offsetY });
      }
  };

  if (loading) return <div className="flex items-center justify-center h-full text-[var(--md-sys-color-primary)]">Loading Knowledge Graph...</div>;
  if (error) return <div className="flex items-center justify-center h-full text-[var(--md-sys-color-error)]">Error: {error}</div>;

  return (
    <div 
      ref={containerRef} 
      className="w-full h-full relative overflow-hidden"
      onMouseMove={handleMouseMove}
      style={{ background: themeColors.background }}
    >
      <ForceGraph2D
        ref={graphRef}
        width={dimensions.width}
        height={dimensions.height}
        graphData={filteredData}
        nodeLabel={() => ''} // Disable default browser tooltip, use custom overlay
        nodeCanvasObject={paintNode}
        nodeCanvasObjectMode={() => 'replace'} // We draw everything
        linkColor={() => themeColors.grid}
        linkWidth={(link: any) => {
            // LOD: 缩小时线变细
            return 1;
        }}
        linkDirectionalParticles={(link: any) => {
            // LOD: 缩小时不显示粒子
            return 2;
        }}
        linkDirectionalParticleWidth={(link: any) => {
            return 2;
        }}
        linkDirectionalParticleSpeed={0.005}
        backgroundColor={themeColors.background}
        onNodeHover={handleNodeHover}
        onNodeClick={(node) => {
            // 1. Focus on node
            if (graphRef.current) {
                graphRef.current.centerAt(node.x, node.y, 1000);
                graphRef.current.zoom(4, 2000);
            }
            // 2. Trigger external callback
            if (onNodeClick) {
                onNodeClick(node as StrategicNode);
            }
        }}
        onNodeDragEnd={async (node) => {
          if (viewType === 'staging' && onMergeNodes) {
            // Find if dropped onto another node
            const { nodes } = filteredData;
            const targetNode: any = nodes.find((n: any) => {
              if (n.id === node.id) return false;
              const dist = Math.sqrt(Math.pow(n.x - (node as any).x, 2) + Math.pow(n.y - (node as any).y, 2));
              return dist < 15; // Threshold for merging
            });

            if (targetNode && window.confirm(`是否将节点 "${node.label}" 合并到 "${targetNode.label}"?`)) {
              await onMergeNodes(node.id, targetNode.id);
              refresh(); // 合并后刷新数据
            }
          }
        }}
        // Physics settings
        cooldownTicks={100}
        d3AlphaDecay={0.02}
        d3VelocityDecay={0.3}
      />

      {/* Custom Tooltip Overlay */}
      {hoverNode && (
        <div 
            className="absolute p-4 bg-[var(--md-sys-color-surface-container-high)]/95 backdrop-blur-md border border-[var(--md-sys-color-outline-variant)] rounded-xl shadow-xl text-[var(--md-sys-color-on-surface)] pointer-events-none z-50 animate-in fade-in duration-200"
            style={{ 
                left: tooltipPos.x + 20, 
                top: tooltipPos.y + 20,
                maxWidth: '300px'
            }}
        >
            <div className="flex items-center gap-2 mb-2">
                <span className="w-2 h-2 rounded-full" style={{ backgroundColor: NODE_STYLES[hoverNode.type]?.borderColor || '#000' }} />
                <span className="text-xs font-mono opacity-50 uppercase tracking-wider">{hoverNode.type}</span>
            </div>
            <div className="font-bold text-lg mb-2 leading-tight">{hoverNode.label}</div>
            {hoverNode.content && (
                <div className="text-sm opacity-80 line-clamp-3 bg-white/5 p-2 rounded mb-2">{hoverNode.content}</div>
            )}
            <div className="flex items-center gap-4 text-xs opacity-50 mt-2">
                <span>Lvl {hoverNode.level}</span>
                <span className="capitalize">{hoverNode.status}</span>
            </div>
        </div>
      )}
      
      <div className="absolute bottom-4 right-4 text-[10px] text-white/20 pointer-events-none">
        Powered by ForceGraph2D
      </div>
    </div>
  );
};

export default StrategicPixiGraph;
