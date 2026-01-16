import { useState, useEffect, useCallback } from 'react';
import api from '../../lib/api';

// 定义节点类型
export interface StrategicNode {
  id: string;
  type: 'Vision' | 'Goal' | 'Project' | 'Task' | 'Self' | 'Person' | 'Concept' | 'Insight';
  label: string;
  status: 'pending' | 'confirmed';
  content?: string;
  level?: number; // 层级 (0=Self, 1=Vision, 2=Goal...)
  day_offset?: number;
  color?: string;
  val?: number; // 节点大小
  alignment_score?: number;
  energy_impact?: number;
  strategic_role?: string;
}

export interface StrategicLink {
  source: string;
  target: string;
  type: string;
}

interface GraphData {
  nodes: StrategicNode[];
  links: StrategicLink[];
}

export function useStrategicData(viewType: string = 'strategic') {
  const [data, setData] = useState<GraphData>({ nodes: [], links: [] });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  const refresh = useCallback(() => setRefreshKey(prev => prev + 1), []);

  useEffect(() => {
    async function fetchData() {
      setLoading(true);
      try {
        // 动态构建 URL
        let endpoint = `/memory/graph?view_type=${viewType}`;
        if (viewType === 'staging') {
          endpoint = '/memory/staging';
        }
        
        const json: any = await api.get(endpoint);
        console.log(`Graph Data (${viewType}):`, json);
        
        // 颜色映射 (M3 Palette)
        const typeColors: Record<string, string> = {
          Self: '#6750A4',     // Primary
          Vision: '#B3261E',   // Error/Red
          Goal: '#E27396',     // Pink
          Project: '#7D5260',  // Tertiary
          Task: '#605D62',     // Outline
          Person: '#3F5F90',   // Secondary
          Concept: '#1D6F42',  // Green
          Organization: '#006D36'
        };

        const nodes: StrategicNode[] = [];
        const links: StrategicLink[] = [];

        // 情况 A: 树状结构 (Root) - 主要是旧的 /graph/strategic 接口返回
        if (json.root) {
          function traverse(node: any, level: number, parentId: string | null) {
            if (nodes.find(n => n.id === node.id)) return;

            nodes.push({
              id: node.id,
              type: node.type,
              label: node.label,
              status: node.status,
              content: node.content,
              level: level,
              day_offset: node.day_offset || 0,
              color: typeColors[node.type] || '#999',
              val: Math.max(10 - level * 2, 2),
              alignment_score: node.alignment_score ?? 0,
              energy_impact: node.energy_impact,
              strategic_role: node.strategic_role
            });

            if (parentId) {
              links.push({
                source: parentId,
                target: node.id,
                type: 'hierarchy'
              });
            }

            if (node.children) {
              node.children.forEach((child: any) => traverse(child, level + 1, node.id));
            }
          }
          traverse(json.root, 0, null);
        } 
        // 情况 B: 扁平结构 (Nodes/Links) - /memory/graph 接口返回
        else if (json.nodes && Array.isArray(json.nodes)) {
           json.nodes.forEach((n: any) => {
             // 简单的层级推断
             let level = 3;
             if (n.type === 'Self') level = 0;
             else if (n.type === 'Vision') level = 1;
             else if (n.type === 'Goal') level = 2;
             
             nodes.push({
               id: n.id,
               type: n.type,
               label: n.label || n.name || 'Unknown',
               status: n.status || 'confirmed',
               content: n.content,
               level: level,
               color: typeColors[n.type] || '#999',
               val: Math.max(8 - level * 1.5, 3),
               alignment_score: n.alignment_score ?? 0,
               energy_impact: n.energy_impact,
               strategic_role: n.strategic_role
             });
           });
           
           if (json.links && Array.isArray(json.links)) {
             json.links.forEach((l: any) => {
               links.push({
                 source: l.source,
                 target: l.target,
                 type: l.type || 'link'
               });
             });
           }
        }

        setData({ nodes, links });
      } catch (err: any) {
        setError(err.message || 'Failed to load graph data');
      } finally {
        setLoading(false);
      }
    }

    fetchData();
  }, [viewType, refreshKey]);

  return { data, loading, error, refresh };
}
