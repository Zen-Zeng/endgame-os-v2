import type { StrategicNode, StrategicLink } from './useStrategicData';

export const LAYER_HEIGHT = 160;
export const PIXELS_PER_DAY = 10;
export const NODE_WIDTH = 120;
export const NODE_HEIGHT = 40;

export interface LayoutNode extends StrategicNode {
  x: number;
  y: number;
}

export function calculateLayout(nodes: StrategicNode[], links: StrategicLink[]): LayoutNode[] {
  // 1. Initialize nodes with basic Time/Level coordinates
  const layoutNodes = nodes.map(node => {
    let level = node.level ?? 5;
    // Fix level based on type if missing
    if (node.type === 'Self') level = 0;
    else if (node.type === 'Vision') level = 1;
    else if (node.type === 'Goal') level = 2;
    else if (node.type === 'Project') level = 3;
    else if (node.type === 'Task') level = 4;
    
    // Initial X based on time
    // Shift by 500 to give some padding for negative offsets
    let x = (node.day_offset || 0) * PIXELS_PER_DAY + 500; 
    
    return {
      ...node,
      level,
      x,
      y: level * LAYER_HEIGHT
    };
  });

  // 2. Adjust X for nodes without time (Concept, Person)
  // They should be placed near their parents
  // Create a map of ID -> Node
  const nodeMap = new Map(layoutNodes.map(n => [n.id, n]));
  
  // Build parent map (Child -> Parent)
  // Note: Links are directed Parent -> Child for Hierarchy
  const parentMap = new Map<string, string>();
  links.forEach(l => {
    if (l.type === 'hierarchy' || l.type === 'OWNS' || l.type === 'DECOMPOSES_TO' || l.type === 'ACHIEVED_BY' || l.type === 'CONSISTS_OF') {
       // Check which one is the parent level. Usually Source is Parent.
       const source = nodeMap.get(l.source);
       const target = nodeMap.get(l.target);
       if (source && target && (source.level || 0) < (target.level || 0)) {
         parentMap.set(l.target, l.source);
       }
    }
  });

  // Iterate to adjust X for non-time nodes (level > 4 usually, or just check day_offset)
  layoutNodes.forEach(node => {
    if (node.day_offset === 0 && node.level > 0) {
       // Try to find parent
       const parentId = parentMap.get(node.id);
       if (parentId) {
         const parent = nodeMap.get(parentId);
         if (parent) {
           node.x = parent.x;
         }
       }
    }
  });

  // 3. Collision Resolution (Staggering)
  // Group by Level
  const levels: Record<number, LayoutNode[]> = {};
  layoutNodes.forEach(n => {
    if (!levels[n.level!]) levels[n.level!] = [];
    levels[n.level!].push(n);
  });

  // For each level, sort by X
  Object.keys(levels).forEach(lvlKey => {
    const lvl = Number(lvlKey);
    const nodesInLevel = levels[lvl];
    nodesInLevel.sort((a, b) => a.x - b.x);

    // Simple greedy row assignment
    // rows stores the end X of the last node in that row
    const rows: number[] = [];

    nodesInLevel.forEach(node => {
      let placed = false;
      for (let r = 0; r < rows.length; r++) {
        // If this row has space (last_end + gap < node.x)
        // But wait, if we strictly follow time X, we can't just push it right.
        // We must push it DOWN (change Y).
        
        // However, if X is identical (e.g. 0), we DO want to spread them out horizontally too?
        // No, strict time axis means X is fixed. Overlap must be solved by Y.
        
        // But for Concepts without time, X is flexible. 
        // Let's assume X is fixed for now, and we stagger Y.
        
        if (node.x > rows[r] + 10) { // 10px gap
           // Fits in this row
           rows[r] = node.x + NODE_WIDTH;
           node.y += r * 50; // Shift down
           placed = true;
           break;
        }
      }
      
      if (!placed) {
        // Start new row
        rows.push(node.x + NODE_WIDTH);
        node.y += (rows.length - 1) * 50;
      }
    });
  });

  return layoutNodes;
}
