/**
 * Endgame OS v2 - Neural Link Page
 * Interactive Topology Editor for Knowledge and Goals
 */
import { useEffect, useState, useRef, useCallback } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import { 
  Share2, 
  Search, 
  Plus, 
  Link as LinkIcon, 
  Zap, 
  Target,
  Layers,
  MousePointer2,
  Settings2,
  Info
} from 'lucide-react';
import GlassCard from '../components/layout/GlassCard';
import Button from '../components/ui/Button';
import { api } from '../lib/api';
import { clsx } from 'clsx';

interface Node {
  id: string;
  name: string;
  type: string;
  val: number;
}

interface Link {
  source: string;
  target: string;
  relation: string;
}

export default function NeuralLinkPage() {
  const fgRef = useRef<any>(null);
  const [graphData, setGraphData] = useState({ nodes: [], links: [] });
  const [selectedNode, setSelectedNode] = useState<any>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [recommendations, setRecommendations] = useState<any[]>([]);
  const [isConnecting, setIsConnecting] = useState(false);
  const [sourceNode, setSourceNode] = useState<any>(null);

  useEffect(() => {
    fetchGraphData();
  }, []);

  const fetchGraphData = async (nodeId?: string) => {
    try {
      const endpoint = nodeId ? `/memory/graph?node_id=${nodeId}` : '/memory/graph';
      const data = await api.get<any>(endpoint);
      if (data) {
        // 转换数据格式以适配 force-graph
        const nodes = data.nodes.map((n: any) => ({
          ...n,
          val: n.type === 'Goal' ? 10 : n.type === 'Project' ? 7 : 4
        }));
        setGraphData({ nodes, links: data.links });
      }
    } catch (e) {
      console.error('Fetch graph error', e);
    }
  };

  const handleNodeClick = useCallback((node: any) => {
    setSelectedNode(node);
    fetchRecommendations(node.id);
    
    if (isConnecting && sourceNode && sourceNode.id !== node.id) {
      createLink(sourceNode.id, node.id);
    }
  }, [isConnecting, sourceNode]);

  const fetchRecommendations = async (nodeId: string) => {
    try {
      const data = await api.get<any[]>(`/links/recommendations?node_id=${nodeId}`);
      setRecommendations(data || []);
    } catch (e) {
      console.error('Fetch recommendations error', e);
    }
  };

  const createLink = async (source: string, target: string) => {
    try {
      await api.post('/links/connect', { source, target, relation: 'relates_to' });
      setIsConnecting(false);
      setSourceNode(null);
      fetchGraphData(); // 刷新图谱
    } catch (e) {
      console.error('Create link error', e);
    }
  };

  const startConnecting = (node: any) => {
    setIsConnecting(true);
    setSourceNode(node);
  };

  return (
    <div className="page-container h-[calc(100vh-120px)] flex gap-[var(--md-sys-spacing-4)] overflow-hidden">
      {/* 左侧：可视化编辑器 */}
      <div className="flex-1 relative rounded-3xl overflow-hidden bg-white/40 backdrop-blur-sm border border-white/20 shadow-inner">
        <div className="absolute top-6 left-6 z-10 space-y-2">
          <GlassCard padding="sm" className="flex items-center gap-2">
            <Search size={18} className="opacity-50" />
            <input 
              type="text" 
              placeholder="搜索节点..." 
              className="bg-transparent border-none outline-none text-sm w-48"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </GlassCard>
          <div className="flex gap-2">
             <GlassCard padding="sm" className="flex items-center gap-2 cursor-pointer hover:bg-surface-variant/20">
               <MousePointer2 size={16} />
               <span className="text-xs font-bold">选择</span>
             </GlassCard>
             <GlassCard padding="sm" className={clsx(
               "flex items-center gap-2 cursor-pointer transition-colors",
               isConnecting ? "bg-[var(--md-sys-color-primary)] text-[var(--md-sys-color-on-primary)]" : "hover:bg-surface-variant/20"
             )} onClick={() => setIsConnecting(!isConnecting)}>
               <LinkIcon size={16} />
               <span className="text-xs font-bold">{isConnecting ? "连接中..." : "建立链接"}</span>
             </GlassCard>
          </div>
        </div>

        <ForceGraph2D
          ref={fgRef}
          graphData={graphData}
          nodeLabel="name"
          nodeColor={(n: any) => 
            n.type === 'Goal' ? 'var(--md-sys-color-primary)' : 
            n.type === 'Project' ? 'var(--md-sys-color-secondary)' : 
            'var(--md-sys-color-tertiary)'
          }
          linkColor={() => 'rgba(0, 0, 0, 0.1)'}
          linkDirectionalParticles={2}
          linkDirectionalParticleSpeed={0.005}
          onNodeClick={handleNodeClick}
          backgroundColor="transparent"
        />

        <div className="absolute bottom-6 right-6 z-10 flex flex-col gap-2">
          <Button variant="elevated" className="!p-3 !rounded-xl" icon={<Settings2 size={20} />} />
          <Button variant="elevated" className="!p-3 !rounded-xl" icon={<Plus size={20} />} />
        </div>
      </div>

      {/* 右侧：属性与推荐面板 */}
      <div className="w-80 flex flex-col gap-[var(--md-sys-spacing-4)] overflow-y-auto pr-2">
        {selectedNode ? (
          <>
            <GlassCard variant="elevated" padding="lg">
              <div className="flex justify-between items-start mb-4">
                <div className={clsx(
                  "p-3 rounded-2xl",
                  selectedNode.type === 'Goal' ? "bg-primary/10 text-primary" : "bg-secondary/10 text-secondary"
                )}>
                  <Target size={24} />
                </div>
                <Button variant="text" icon={<Share2 size={18} />} />
              </div>
              <h2 className="text-xl font-bold mb-1">{selectedNode.name}</h2>
              <div className="text-xs font-bold uppercase opacity-50 mb-4">{selectedNode.type}</div>
              
              <div className="space-y-4">
                <div className="p-3 bg-surface-variant/20 rounded-xl text-sm italic opacity-80">
                  "{selectedNode.content || "该节点暂无详细描述内容。"}"
                </div>
                
                <Button 
                  fullWidth 
                  variant={isConnecting && sourceNode?.id === selectedNode.id ? "tonal" : "outlined"}
                  icon={<LinkIcon size={18} />}
                  onClick={() => startConnecting(selectedNode)}
                >
                  {isConnecting && sourceNode?.id === selectedNode.id ? "请点击目标节点" : "以此节点为起点"}
                </Button>
              </div>
            </GlassCard>

            <div className="space-y-3">
              <h3 className="text-sm font-bold flex items-center gap-2 px-2">
                <Zap size={16} className="text-[var(--md-sys-color-tertiary)]" />
                神经链接推荐
              </h3>
              {recommendations.length > 0 ? (
                recommendations.map((rec: any) => (
                  <GlassCard key={rec.node_id} padding="sm" className="hover:ring-1 ring-primary transition-all cursor-pointer group">
                    <div className="flex justify-between items-center">
                      <div>
                        <div className="text-sm font-bold">{rec.name}</div>
                        <div className="text-[10px] opacity-50 uppercase">{rec.reason}</div>
                      </div>
                      <button 
                        className="p-2 rounded-lg hover:bg-primary/10 text-primary opacity-0 group-hover:opacity-100 transition-opacity"
                        onClick={() => createLink(selectedNode.id, rec.node_id)}
                      >
                        <Plus size={16} />
                      </button>
                    </div>
                  </GlassCard>
                ))
              ) : (
                <div className="p-8 text-center opacity-40">
                  <Info size={32} className="mx-auto mb-2" />
                  <p className="text-xs">暂无推荐，尝试关联更多知识</p>
                </div>
              )}
            </div>
          </>
        ) : (
          <div className="h-full flex flex-col items-center justify-center text-center opacity-40 p-8 border-2 border-dashed border-surface-variant rounded-3xl">
            <Layers size={48} className="mb-4" />
            <p className="text-sm font-bold">选择一个节点进行编辑</p>
            <p className="text-xs mt-2">点击图谱中的节点以查看详细属性和神经推荐</p>
          </div>
        )}
      </div>
    </div>
  );
}
