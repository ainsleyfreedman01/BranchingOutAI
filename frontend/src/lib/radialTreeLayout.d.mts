export const CAREER_NODE_SIZE: { width: number; height: number };

export function radialTreeLayout(
  tree: {
    rootNodeId: string;
    nodes: { id: string; label: string }[];
    edges: { source: string; target: string }[];
  },
  rootCenter: { x: number; y: number },
  nodeSizes?: Map<string, { width: number; height: number }>,
): Map<string, { x: number; y: number }>;
