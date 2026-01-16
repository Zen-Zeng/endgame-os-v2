import { useState, useEffect, useRef, useMemo } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import { useStrategicData } from './useStrategicData';
import type { StrategicNode } from './useStrategicData';

const NODE_STYLES: Record<string, { color: string, borderColor: string }> = {
  Self:    { color: '#D0BCFF', borderColor: '#6750A4' }, 
  Vision:  { color: '#FFB4AB', borderColor: '#93000A' }, 
  Goal:    { color: '#FFD8E4', borderColor: '#8C1D18' }, 
  Project: { color: '#E8DEF8', borderColor: '#65558F' }, 
  Task:    { color: '#E6E1E5', borderColor: '#484649' }, 
  Person:  { color: '#C2E7FF', borderColor: '#004A77' }, 
  Concept: { color: '#C4EED0', borderColor: '#0F5223' },
  Insight: { color: '#FFD700', borderColor: '#B8860B' }  
};

interface StrategicTreeViewProps {
  alignmentThreshold?: number;
  refreshKey?: number;
}

const StrategicTreeView = ({ 
  alignmentThreshold = 0,
  refreshKey = 0
}: StrategicTreeViewProps) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const graphRef = useRef<any>(null);
  const { data, loading, error, refresh } = useStrategicData('strategic');
  
  useEffect(() => {
    refresh();
  }, [refreshKey, refresh]);
  
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });
  const [hoverNode, setHoverNode] = useState<StrategicNode | null>(null);
  const [tooltipPos, setTooltipPos] = useState({ x: 0, y: 0 });

  const filteredData = useMemo(() => {
    if (!data || !data.nodes) return { nodes: [], links: [] };
    if (alignmentThreshold === 0) return data;
    
    const validNodes = data.nodes.filter(n => {
        if (n.type === 'Self' || n.type === 'Vision') return true;
        const score = (n as any).alignment_score || 0;
        return score >= alignmentThreshold;
    });
    
    const validNodeIds = new Set(validNodes.map(n => n.id));
    const validLinks = data.links.filter(l => {
        const sourceId = typeof l.source === 'object' ? (l.source as any).id : l.source;
        const targetId = typeof l.target === 'object' ? (l.target as any).id : l.target;
        return validNodeIds.has(sourceId) && validNodeIds.has(targetId);
    });
    
    return { nodes: validNodes, links: validLinks };
  }, [data, alignmentThreshold]);

  useEffect(() => {
    const updateDimensions = () => {
      if (containerRef.current) {
        setDimensions({
          width: containerRef.current.clientWidth,
          height: containerRef.current.clientHeight
        });
      }
    };
    window.addEventListener('resize', updateDimensions);
    updateDimensions();
    return () => window.removeEventListener('resize', updateDimensions);
  }, []);

  const paintNode = (node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
    const style = NODE_STYLES[node.type] || NODE_STYLES.Concept;
    const label = node.label;
    const fontSize = 12 / globalScale;
    const padding = 6 / globalScale;
    
    // 基础半径
    let radius = 6;
    if (node.type === 'Self') radius = 10;
    if (node.type === 'Vision') radius = 8;

    // 绘制阴影 (仅在缩放较大时)
    if (globalScale > 1.5) {
        ctx.shadowColor = 'rgba(0, 0, 0, 0.3)';
        ctx.shadowBlur = 10 / globalScale;
        ctx.shadowOffsetX = 2 / globalScale;
        ctx.shadowOffsetY = 2 / globalScale;
    }

    // 绘制节点主体
    ctx.beginPath();
    ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI, false);
    ctx.fillStyle = style.color;
    ctx.fill();
    
    // 绘制外圈
    ctx.lineWidth = 2 / globalScale;
    ctx.strokeStyle = style.borderColor;
    ctx.stroke();
    
    // 重置阴影
    ctx.shadowColor = 'transparent';

    // 绘制文本
    if (globalScale > 0.6) {
      const text = label.length > 15 ? label.substring(0, 15) + '...' : label;
      ctx.font = `${node.type === 'Self' || node.type === 'Vision' ? '700' : '500'} ${fontSize}px "Inter", "Segoe UI", sans-serif`;
      
      // 测量文本宽度以绘制背景胶囊 (Mind map style)
      const textWidth = ctx.measureText(text).width;
      const bgWidth = textWidth + padding * 3;
      const bgHeight = fontSize + padding * 2;
      
      // 文本背景 (Glass effect)
      ctx.fillStyle = 'rgba(29, 27, 32, 0.8)';
      ctx.beginPath();
      const rectX = node.x - bgWidth / 2;
      const rectY = node.y + radius + padding;
      const r = 4 / globalScale;
      
      // Rounded rect
      ctx.moveTo(rectX + r, rectY);
      ctx.lineTo(rectX + bgWidth - r, rectY);
      ctx.arcTo(rectX + bgWidth, rectY, rectX + bgWidth, rectY + r, r);
      ctx.lineTo(rectX + bgWidth, rectY + bgHeight - r);
      ctx.arcTo(rectX + bgWidth, rectY + bgHeight, rectX + bgWidth - r, rectY + bgHeight, r);
      ctx.lineTo(rectX + r, rectY + bgHeight);
      ctx.arcTo(rectX, rectY + bgHeight, rectX, rectY + bgHeight - r, r);
      ctx.lineTo(rectX, rectY + r);
      ctx.arcTo(rectX, rectY, rectX + r, rectY, r);
      ctx.fill();
      
      // 文本描边 (如果是高优先级节点)
      if (node.type === 'Vision' || node.type === 'Goal') {
          ctx.strokeStyle = style.borderColor;
          ctx.lineWidth = 0.5 / globalScale;
          ctx.stroke();
      }

      // 绘制文字
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillStyle = '#ffffff';
      ctx.fillText(text, node.x, rectY + bgHeight / 2);
      
      // 如果有能量影响，绘制一个小标识
      if (node.data && node.data["能量影响"]) {
          const impact = parseInt(node.data["能量影响"]);
          if (impact > 5) {
              ctx.fillStyle = '#FFD700';
              ctx.font = `${fontSize * 0.8}px Sans-Serif`;
              ctx.fillText('★', node.x + bgWidth/2 + 4/globalScale, rectY + bgHeight/2);
          }
      }
    }
  };

  if (loading) return <div className="flex items-center justify-center h-full">Loading Tree View...</div>;

  return (
    <div ref={containerRef} className="w-full h-full relative bg-[#1d1b20]">
      <ForceGraph2D
        ref={graphRef}
        width={dimensions.width}
        height={dimensions.height}
        graphData={filteredData}
        dagMode="td" // Top-down tree layout
        dagLevelDistance={140}
        nodeCanvasObject={paintNode}
        nodeCanvasObjectMode={() => 'replace'}
        linkColor={() => 'rgba(255, 255, 255, 0.15)'}
        linkWidth={2}
        linkCurvature={0.3}
        linkDirectionalArrowLength={5}
        linkDirectionalArrowRelPos={1}
        linkDirectionalParticles={2}
        linkDirectionalParticleSpeed={0.005}
        onNodeHover={(node) => setHoverNode(node as any)}
        onNodeClick={(node) => {
            if (graphRef.current) {
                graphRef.current.centerAt(node.x, node.y, 800);
                graphRef.current.zoom(2.5, 800);
            }
        }}
        // 性能优化与交互增强
        enableNodeDrag={true}
        enableZoomInteraction={true}
        enablePanInteraction={true}
        cooldownTicks={150}
        d3AlphaDecay={0.02}
        d3VelocityDecay={0.3}
      />
      
      {/* Tooltip */}
      {hoverNode && (
        <div 
          className="absolute p-3 bg-[#2b2930] border border-[#49454f] rounded-lg shadow-xl text-white pointer-events-none z-50"
          style={{ left: tooltipPos.x + 20, top: tooltipPos.y + 20 }}
        >
          <div className="text-[10px] opacity-50 uppercase mb-1">{hoverNode.type}</div>
          <div className="font-bold">{hoverNode.label}</div>
          {hoverNode.content && <div className="text-xs opacity-70 mt-1 max-w-[200px]">{hoverNode.content}</div>}
        </div>
      )}

      <div className="absolute top-4 left-4 bg-[#2b2930]/80 backdrop-blur-md px-3 py-1.5 rounded-full border border-[#49454f] text-[10px] font-bold text-white/50 uppercase tracking-widest">
        Strategic Tree Mode (DAG TD)
      </div>
    </div>
  );
};

export default StrategicTreeView;
