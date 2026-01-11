import { useState, useEffect } from 'react';
import api from '../../lib/api';

// 定义节点类型
export interface StrategicNode {
  id: string;
  type: 'Vision' | 'Goal' | 'Project' | 'Task' | 'Self' | 'Person' | 'Concept';
  label: string;
  status: 'pending' | 'confirmed';
  content?: string;
  level?: number; // 层级 (0=Self, 1=Vision, 2=Goal...)
  day_offset?: number;
  color?: string;
  val?: number; // 节点大小
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

export function useStrategicData() {
  const [data, setData] = useState<GraphData>({ nodes: [], links: [] });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchData() {
      setLoading(true);
      try {
        // 使用 api.get 自动处理 Token 和 Base URL
        const json: any = await api.get('/graph/strategic');
        console.log('Strategic Graph Raw Data:', json);
        
        // 转换数据：将树状结构展平
        const nodes: StrategicNode[] = [];
        const links: StrategicLink[] = [];
        
        // 颜色映射 (M3 Palette)
        const typeColors: Record<string, string> = {
          Self: '#6750A4',     // Primary
          Vision: '#B3261E',   // Error/Red
          Goal: '#E27396',     // Pink
          Project: '#7D5260',  // Tertiary
          Task: '#605D62',     // Outline
          Person: '#3F5F90',   // Secondary
          Concept: '#1D6F42'   // Green
        };

        // 递归遍历树
        function traverse(node: any, level: number, parentId: string | null) {
          // 检查是否已存在（避免环）
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
            val: Math.max(10 - level * 2, 2) // 层级越深节点越小
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

        if (json.root) {
          traverse(json.root, 0, null);
        }

        console.log('Graph Nodes:', nodes);
        console.log('Graph Links:', links);

        setData({ nodes, links });
      } catch (err: any) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }

    fetchData();
  }, []);

  return { data, loading, error };
}
