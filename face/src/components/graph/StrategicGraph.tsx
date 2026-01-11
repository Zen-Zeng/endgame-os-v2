import { useRef, useCallback } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import { useStrategicData, type StrategicNode } from './useStrategicData';

const StrategicGraph = () => {
  const fgRef = useRef<any>(null);
  const { data, loading, error } = useStrategicData();

  // 自定义节点渲染 (M3 Card Style)
  const nodeCanvasObject = useCallback((node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
    const label = node.label;
    const fontSize = 12 / globalScale;
    ctx.font = `${fontSize}px Sans-Serif`;
    const textWidth = ctx.measureText(label).width;
    const bckgDimensions = [textWidth + fontSize * 2, fontSize * 2]; // 宽, 高

    // M3 Colors
    const bgColor = node.color || '#fff';
    const textColor = '#fff';

    // 绘制圆角矩形背景
    const x = node.x - bckgDimensions[0] / 2;
    const y = node.y - bckgDimensions[1] / 2;
    const w = bckgDimensions[0];
    const h = bckgDimensions[1];
    const r = 4 / globalScale; // 圆角半径

    ctx.fillStyle = bgColor;
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.lineTo(x + w - r, y);
    ctx.quadraticCurveTo(x + w, y, x + w, y + r);
    ctx.lineTo(x + w, y + h - r);
    ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
    ctx.lineTo(x + r, y + h);
    ctx.quadraticCurveTo(x, y + h, x, y + h - r);
    ctx.lineTo(x, y + r);
    ctx.quadraticCurveTo(x, y, x + r, y);
    ctx.closePath();
    ctx.fill();

    // 绘制文字
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillStyle = textColor;
    ctx.fillText(label, node.x, node.y);

    // 节点交互区域
    node.__bckgDimensions = bckgDimensions; 
  }, []);

  // 数据加载后自动居中
  const handleEngineStop = useCallback(() => {
    if (fgRef.current) {
      fgRef.current.zoomToFit(400, 50);
    }
  }, []);

  if (loading) return <div className="flex items-center justify-center h-full text-sm text-gray-500">Loading Strategic Graph...</div>;
  if (error) return <div className="flex items-center justify-center h-full text-sm text-red-500">Error: {error}</div>;

  return (
    <div className="w-full h-full bg-[var(--md-sys-color-surface-container-lowest)] rounded-2xl overflow-hidden border border-[var(--md-sys-color-outline-variant)]">
      <ForceGraph2D
        ref={fgRef}
        graphData={data}
        nodeLabel="label"
        nodeCanvasObject={nodeCanvasObject}
        nodeCanvasObjectMode={() => 'replace'}
        dagMode="td" // Top-Down DAG layout
        dagLevelDistance={80}
        backgroundColor="rgba(0,0,0,0)" // 透明背景
        linkColor={() => '#a0a0a0'} // 更亮的连线颜色
        linkWidth={2}
        linkDirectionalArrowLength={3.5}
        linkDirectionalArrowRelPos={1}
        d3VelocityDecay={0.3}
        onEngineStop={handleEngineStop}
        cooldownTicks={100} // 减少计算时间，更快稳定
        onNodeClick={(node) => {
          // Center view on click
          fgRef.current?.centerAt(node.x, node.y, 1000);
          fgRef.current?.zoom(2, 2000);
        }}
      />
    </div>
  );
};

export default StrategicGraph;
