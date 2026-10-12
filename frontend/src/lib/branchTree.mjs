export function branchTree(tree) {
  const nodesById = new Map(tree.nodes.map((node) => [node.id, node]));
  const children = new Map();
  for (const { source, target } of tree.edges) {
    if (!nodesById.has(source) || !nodesById.has(target)) continue;
    const ids = children.get(source) ?? new Set();
    ids.add(target);
    children.set(source, ids);
  }
  const root = nodesById.get(tree.rootNodeId);
  if (!root) throw new Error("Career tree root is missing.");
  const nodes = [{ ...root, originalId: root.id }];
  const edges = [];
  const expanded = new Set(tree.expandedNodeIds);
  const expandedNodeIds = expanded.has(root.id) ? [root.id] : [];
  const pending = [{ node: nodes[0], path: [root.id] }];
  for (let i = 0; i < pending.length; i++) {
    const { node, path } = pending[i];
    const childIds = [...(children.get(node.originalId) ?? [])].sort((a, b) =>
      nodesById.get(a).label.localeCompare(nodesById.get(b).label) || a.localeCompare(b));
    for (const originalId of childIds) {
      if (path.includes(originalId)) continue;
      const childPath = [...path, originalId];
      const id = `branch:${JSON.stringify(childPath)}`;
      const child = { ...nodesById.get(originalId), id, originalId };
      nodes.push(child);
      edges.push({ id: `${node.id}->${id}`, source: node.id, target: id });
      if (expanded.has(originalId)) expandedNodeIds.push(id);
      pending.push({ node: child, path: childPath });
    }
  }
  return { ...tree, nodes, edges, expandedNodeIds };
}
