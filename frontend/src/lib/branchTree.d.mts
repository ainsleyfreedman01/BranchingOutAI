export function branchTree<T extends {
  rootNodeId: string;
  nodes: { id: string; label: string }[];
  edges: { id: string; source: string; target: string }[];
  expandedNodeIds: string[];
}>(tree: T): Omit<T, "nodes"> & {
  nodes: (T["nodes"][number] & { originalId: string })[];
};
