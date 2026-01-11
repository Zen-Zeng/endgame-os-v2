import { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
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
  Concept: { color: '#C4EED0', borderColor: '#0F5223' }  // Success
};

const StrategicPixiGraph = () => {
  const containerRef = useRef<HTMLDivElement>(null);
  const graphRef = useRef<any>(null);
  const { data, loading, error } = useStrategicData();
  
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

  useEffect(() => {
    if (graphRef.current) {
        // Access underlying d3 simulation
        const simulation = graphRef.current.d3Force('link').distance(50); // Default link distance
        
        // Define Custom Forces
        // 1. Center Self (Force 0)
        // 2. Vision Up (Force Y < 0)
        // 3. Goal Sides (Force X)
        // 4. Project/Task Down (Force Y > 0)
        
        graphRef.current.d3Force('y', (d3: any) => {
            return (node: any) => {
                // Return target Y based on type
                switch(node.type) {
                    case 'Self': return 0;
                    case 'Vision': return -200; // Pull Up
                    case 'Goal': return 0;      // Center Vertically
                    case 'Project': return 200; // Pull Down
                    case 'Task': return 400;    // Pull Further Down
                    default: return 0;
                }
            };
        });

        // Use imported d3 module instead of require
        // const d3 = (window as any).d3 || require('d3-force'); 

    }
  }, []);

  // Alternative: Pre-process data to set fx/fy for strict layout, OR use dagMode if hierarchy is strict.
  // But user wants Compass (Up/Down/Left/Right).
  
  // Let's try to set `fy` (Fixed Y) for specific nodes to enforce layers strictly!
  // This is supported by d3-force natively.
  useEffect(() => {
      if (data.nodes.length > 0) {
          data.nodes.forEach((node: any) => {
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
  }, [data]);


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
    const style = NODE_STYLES[node.type] || NODE_STYLES.Concept;
    const label = node.label;
    const fontSize = 12 / globalScale;
    const radius = 5; // Base radius

    // 1. Draw Shadow/Glow
    ctx.shadowColor = 'rgba(0,0,0,0.2)';
    ctx.shadowBlur = 4;
    ctx.shadowOffsetX = 1;
    ctx.shadowOffsetY = 1;

    // 2. Draw Circle
    ctx.beginPath();
    ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI, false);
    ctx.fillStyle = style.color;
    ctx.fill();

    // 3. Draw Border
    ctx.lineWidth = 1.5 / globalScale;
    ctx.strokeStyle = style.borderColor;
    ctx.stroke();

    // Reset shadow
    ctx.shadowColor = 'transparent';
    ctx.shadowBlur = 0;

    // 4. Draw Label
    // LOD: Only show label if scale is sufficient or it's a high-level node
    const isImportant = (node.level || 10) <= 2;
    const isHovered = hoverNode && hoverNode.id === node.id;
    
    if (isImportant || globalScale > 1.2 || isHovered) {
      ctx.font = `600 ${3 + fontSize}px Sans-Serif`; // Fixed base size + scale adjustment
      ctx.textAlign = 'center';
      ctx.textBaseline = 'top';
      
      // Text Background (for readability)
      // const textWidth = ctx.measureText(label).width;
      // ctx.fillStyle = 'rgba(0, 0, 0, 0.5)';
      // ctx.fillRect(node.x - textWidth / 2 - 2, node.y + radius + 2, textWidth + 4, fontSize + 4);

      ctx.fillStyle = themeColors.text;
      ctx.fillText(label, node.x, node.y + radius + 2);
    }
  }, [themeColors, hoverNode]);

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
        graphData={data}
        nodeLabel={() => ''} // Disable default browser tooltip, use custom overlay
        nodeCanvasObject={paintNode}
        nodeCanvasObjectMode={() => 'replace'} // We draw everything
        linkColor={() => themeColors.grid}
        linkWidth={1}
        linkDirectionalParticles={2}
        linkDirectionalParticleWidth={2}
        linkDirectionalParticleSpeed={0.005}
        backgroundColor={themeColors.background}
        onNodeHover={handleNodeHover}
        onNodeClick={(node) => {
            // Focus on node
            if (graphRef.current) {
                graphRef.current.centerAt(node.x, node.y, 1000);
                graphRef.current.zoom(4, 2000);
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
