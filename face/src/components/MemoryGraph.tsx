/**
 * MemoryGraph 组件
 * 用于可视化调试图数据库中的知识图谱
 */
import { useEffect, useState, useRef } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import api from '../lib/api';

interface Node {
  id: string;
  group: string;
  label: string;
  data: any;
}

interface Link {
  source: string;
  target: string;
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
  const graphRef = useRef<any>(null);

  // 节点颜色映射
  const getNodeColor = (node: Node): string => {
    const colorMap: { [key: string]: string } = {
      'User': '#FF6B6B',
      'Goal': '#4ECDC4',
      'Project': '#45B7D1',
      'Task': '#96CEB4',
      'Log': '#FFEAA7',
      'Concept': '#DDA0DD',
      'Unknown': '#95A5A6'
    };
    return colorMap[node.group] || colorMap['Unknown'];
  };

  // 节点大小映射
  const getNodeSize = (node: Node): number => {
    const sizeMap: { [key: string]: number } = {
      'User': 20,
      'Goal': 15,
      'Project': 12,
      'Task': 10,
      'Log': 8,
      'Concept': 6
    };
    return sizeMap[node.group] || 8;
  };

  // 提取通用的数据加载和过滤逻辑
  const loadGraphData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const data: any = await api.get('/memory/graph');
      console.log('原始图数据:', data);
      
      if (data && data.nodes && data.links) {
        const nodeIds = new Set(data.nodes.map((n: any) => n.id));
        const validLinks = data.links.filter((l: any) => {
          const sourceId = typeof l.source === 'object' ? l.source.id : l.source;
          const targetId = typeof l.target === 'object' ? l.target.id : l.target;
          
          const sourceExists = nodeIds.has(sourceId);
          const targetExists = nodeIds.has(targetId);
          
          if (!sourceExists || !targetExists) {
            console.warn(`过滤无效连线: ${sourceId} -> ${targetId} (节点不存在)`);
          }
          
          return sourceExists && targetExists;
        });
        
        setGraphData({
          nodes: data.nodes,
          links: validLinks,
          total_nodes: data.nodes.length,
          total_links: validLinks.length
        });
      } else if (data) {
        setGraphData({
          nodes: data.nodes || [],
          links: data.links || [],
          total_nodes: data.nodes?.length || 0,
          total_links: data.links?.length || 0
        });
      }
    } catch (err) {
      console.error('加载图数据失败:', err);
      setError(err instanceof Error ? err.message : '未知错误');
    } finally {
      setLoading(false);
    }
  };

  // 加载图数据
  useEffect(() => {
    loadGraphData();
  }, []);

  // 处理节点点击
  const handleNodeClick = (node: Node) => {
    setSelectedNode(node);
    console.log('选中节点:', node);
  };

  // 处理背景点击（取消选择）
  const handleBackgroundClick = () => {
    setSelectedNode(null);
  };

  // 刷新数据
  const handleRefresh = () => {
    loadGraphData();
  };

  // 缩放视图
  const handleZoomIn = () => {
    if (graphRef.current) {
      graphRef.current.zoom(1.2);
    }
  };

  const handleZoomOut = () => {
    if (graphRef.current) {
      graphRef.current.zoom(0.8);
    }
  };

  const handleResetZoom = () => {
    if (graphRef.current) {
      graphRef.current.zoomToFit(400);
    }
  };

  if (loading) {
    return (
      <div className="memory-graph-container">
        <div className="memory-graph-header">
          <h2>知识图谱可视化</h2>
          {onClose && (
            <button className="close-button" onClick={onClose}>
              关闭
            </button>
          )}
        </div>
        <div className="memory-graph-loading">
          <div className="spinner"></div>
          <p>加载图数据中...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="memory-graph-container">
        <div className="memory-graph-header">
          <h2>知识图谱可视化</h2>
          {onClose && (
            <button className="close-button" onClick={onClose}>
              关闭
            </button>
          )}
        </div>
        <div className="memory-graph-error">
          <p>加载失败: {error}</p>
          <button className="refresh-button" onClick={handleRefresh}>
            重试
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="memory-graph-container">
      <div className="memory-graph-header">
        <h2>知识图谱可视化</h2>
        <div className="memory-graph-stats">
          <span>节点: {graphData.nodes?.length || 0}</span>
          <span>连线: {graphData.links?.length || 0}</span>
        </div>
        <div className="memory-graph-controls">
          <button className="control-button" onClick={handleRefresh} title="刷新">
            🔄
          </button>
          <button className="control-button" onClick={handleZoomIn} title="放大">
            🔍+
          </button>
          <button className="control-button" onClick={handleZoomOut} title="缩小">
            🔍-
          </button>
          <button className="control-button" onClick={handleResetZoom} title="重置视图">
            🎯
          </button>
          {onClose && (
            <button className="close-button" onClick={onClose}>
              关闭
            </button>
          )}
        </div>
      </div>

      <div className="memory-graph-content">
        <div className="graph-legend">
          <h3>图例</h3>
          <div className="legend-items">
            <div className="legend-item">
              <span className="legend-color" style={{ backgroundColor: '#FF6B6B' }}></span>
              <span>User</span>
            </div>
            <div className="legend-item">
              <span className="legend-color" style={{ backgroundColor: '#4ECDC4' }}></span>
              <span>Goal</span>
            </div>
            <div className="legend-item">
              <span className="legend-color" style={{ backgroundColor: '#45B7D1' }}></span>
              <span>Project</span>
            </div>
            <div className="legend-item">
              <span className="legend-color" style={{ backgroundColor: '#96CEB4' }}></span>
              <span>Task</span>
            </div>
            <div className="legend-item">
              <span className="legend-color" style={{ backgroundColor: '#FFEAA7' }}></span>
              <span>Log</span>
            </div>
            <div className="legend-item">
              <span className="legend-color" style={{ backgroundColor: '#DDA0DD' }}></span>
              <span>Concept</span>
            </div>
          </div>
        </div>

        <div className="graph-wrapper">
          {(!graphData.nodes || graphData.nodes.length === 0) ? (
            <div className="empty-graph">
              <p>暂无图数据</p>
              <p className="hint">请先添加一些记忆数据</p>
            </div>
          ) : (
            <ForceGraph2D
              ref={graphRef}
              graphData={graphData}
              nodeLabel={(node: Node) => node.label}
              nodeColor={(node: Node) => getNodeColor(node)}
              nodeVal={(node: Node) => getNodeSize(node)}
              linkLabel={(link: Link) => link.type}
              linkDirectionalArrowLength={3}
              linkDirectionalArrowRelPos={1}
              onNodeClick={handleNodeClick}
              onBackgroundClick={handleBackgroundClick}
              width={800}
              height={600}
              cooldownTicks={100}
              onEngineStop={() => {
                if (graphRef.current) {
                  graphRef.current.zoomToFit(400);
                }
              }}
            />
          )}
        </div>

        {selectedNode && (
          <div className="node-details-panel">
            <div className="panel-header">
              <h3>节点详情</h3>
              <button className="close-panel-button" onClick={() => setSelectedNode(null)}>
                ✕
              </button>
            </div>
            <div className="panel-content">
              <div className="detail-item">
                <span className="detail-label">ID:</span>
                <span className="detail-value">{selectedNode.id}</span>
              </div>
              <div className="detail-item">
                <span className="detail-label">类型:</span>
                <span className="detail-value">{selectedNode.group}</span>
              </div>
              <div className="detail-item">
                <span className="detail-label">标签:</span>
                <span className="detail-value">{selectedNode.label}</span>
              </div>
              {selectedNode.data && (
                <div className="detail-item">
                  <span className="detail-label">数据:</span>
                  <pre className="detail-data">
                    {JSON.stringify(selectedNode.data, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      <style>{`
        .memory-graph-container {
          width: 100%;
          height: 100vh;
          display: flex;
          flex-direction: column;
          background: #1a1a2e;
          color: #eee;
        }

        .memory-graph-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 1rem 2rem;
          background: #16213e;
          border-bottom: 2px solid #0f3460;
        }

        .memory-graph-header h2 {
          margin: 0;
          font-size: 1.5rem;
          color: #e94560;
        }

        .memory-graph-stats {
          display: flex;
          gap: 2rem;
          font-size: 0.9rem;
        }

        .memory-graph-controls {
          display: flex;
          gap: 0.5rem;
        }

        .control-button,
        .close-button,
        .refresh-button {
          padding: 0.5rem 1rem;
          background: #0f3460;
          color: #eee;
          border: 1px solid #e94560;
          border-radius: 4px;
          cursor: pointer;
          font-size: 1rem;
          transition: all 0.3s;
        }

        .control-button:hover,
        .close-button:hover,
        .refresh-button:hover {
          background: #e94560;
          transform: scale(1.05);
        }

        .memory-graph-content {
          flex: 1;
          display: flex;
          overflow: hidden;
        }

        .graph-legend {
          width: 150px;
          padding: 1rem;
          background: #16213e;
          border-right: 2px solid #0f3460;
          overflow-y: auto;
        }

        .graph-legend h3 {
          margin-top: 0;
          font-size: 1rem;
          color: #e94560;
        }

        .legend-items {
          display: flex;
          flex-direction: column;
          gap: 0.5rem;
        }

        .legend-item {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          font-size: 0.85rem;
        }

        .legend-color {
          width: 16px;
          height: 16px;
          border-radius: 50%;
          border: 2px solid #eee;
        }

        .graph-wrapper {
          flex: 1;
          position: relative;
          background: #0f0f23;
        }

        .memory-graph-loading,
        .memory-graph-error {
          flex: 1;
          display: flex;
          flex-direction: column;
          justify-content: center;
          align-items: center;
          gap: 1rem;
        }

        .spinner {
          width: 50px;
          height: 50px;
          border: 4px solid #0f3460;
          border-top: 4px solid #e94560;
          border-radius: 50%;
          animation: spin 1s linear infinite;
        }

        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }

        .empty-graph {
          display: flex;
          flex-direction: column;
          justify-content: center;
          align-items: center;
          height: 100%;
          color: #666;
        }

        .empty-graph .hint {
          font-size: 0.85rem;
          margin-top: 0.5rem;
        }

        .node-details-panel {
          position: absolute;
          top: 1rem;
          right: 1rem;
          width: 300px;
          max-height: 400px;
          background: #16213e;
          border: 2px solid #e94560;
          border-radius: 8px;
          overflow-y: auto;
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.5);
          z-index: 1000;
        }

        .panel-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 0.75rem 1rem;
          background: #0f3460;
          border-bottom: 2px solid #e94560;
        }

        .panel-header h3 {
          margin: 0;
          font-size: 1rem;
          color: #e94560;
        }

        .close-panel-button {
          background: none;
          border: none;
          color: #eee;
          font-size: 1.2rem;
          cursor: pointer;
          padding: 0;
          width: 24px;
          height: 24px;
          display: flex;
          align-items: center;
          justify-content: center;
        }

        .close-panel-button:hover {
          color: #e94560;
        }

        .panel-content {
          padding: 1rem;
        }

        .detail-item {
          margin-bottom: 1rem;
        }

        .detail-label {
          display: block;
          font-weight: bold;
          color: #e94560;
          margin-bottom: 0.25rem;
          font-size: 0.85rem;
        }

        .detail-value {
          color: #eee;
          word-break: break-word;
        }

        .detail-data {
          background: #0f0f23;
          padding: 0.5rem;
          border-radius: 4px;
          font-size: 0.75rem;
          overflow-x: auto;
          margin: 0;
          max-height: 200px;
          overflow-y: auto;
        }
      `}</style>
    </div>
  );
}
