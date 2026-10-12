export const CAREER_NODE_SIZE = { width: 200, height: 64 };

export function radialTreeLayout(tree, rootCenter, nodeSizes = new Map()) {
  const gap = 24;
  const sizeOf = (id) => nodeSizes.get(id) ?? CAREER_NODE_SIZE;
  const nodesById = new Map(tree.nodes.map((node) => [node.id, node]));
  const children = new Map(tree.nodes.map((node) => [node.id, []]));
  for (const { source, target } of tree.edges) {
    if (nodesById.has(source) && nodesById.has(target)) children.get(source).push(target);
  }
  for (const ids of children.values()) {
    ids.sort((a, b) => nodesById.get(a).label.localeCompare(nodesById.get(b).label) || a.localeCompare(b));
  }

  // Assign shared descendants once, using deterministic breadth-first ownership.
  const visited = new Set([tree.rootNodeId]);
  const queue = [tree.rootNodeId];
  const ownedChildren = new Map();
  for (let index = 0; index < queue.length; index++) {
    const ids = [...new Set(children.get(queue[index]) ?? [])].filter((id) => !visited.has(id));
    ids.forEach((id) => visited.add(id));
    ownedChildren.set(queue[index], ids);
    queue.push(...ids);
  }
  const roots = ownedChildren.get(tree.rootNodeId) ?? [];
  const positions = new Map();
  if (!roots.length) return positions;

  const weights = new Map();
  for (const id of [...queue].reverse()) {
    const descendants = ownedChildren.get(id) ?? [];
    weights.set(id, Math.max(1, descendants.reduce((sum, child) => sum + weights.get(child), 0)));
  }
  const totalWeight = roots.reduce((sum, id) => sum + Math.sqrt(weights.get(id)), 0);
  const spans = roots.map((id) => Math.PI * 2 * Math.sqrt(weights.get(id)) / totalWeight);
  let sectorStart = -Math.PI / 2 - spans[0] / 2;
  const branches = roots.map((id, index) => {
    const span = spans[index];
    const angle = sectorStart + span / 2;
    sectorStart += span;
    const cos = Math.cos(angle), sin = Math.sin(angle);
    const projectedSize = (nodeId) => {
      const { width, height } = sizeOf(nodeId);
      return {
        forwardExtent: Math.abs(cos) * width + Math.abs(sin) * height,
        acrossExtent: Math.abs(sin) * width + Math.abs(cos) * height,
      };
    };
    const packed = new Map();
    for (const nodeId of [...queue].reverse()) {
      const ids = ownedChildren.get(nodeId) ?? [];
      const merged = new Map();
      const points = [];
      const offsets = [];
      for (const child of ids) {
        const subtree = packed.get(child);
        let offset = 0;
        for (const [depth, contour] of subtree.contours) {
          const prior = merged.get(depth);
          if (prior) offset = Math.max(offset, prior.right + gap - contour.left);
        }
        offsets.push(offset);
        subtree.points.forEach((point) => points.push({ ...point, depth: point.depth + 1, across: point.across + offset }));
        for (const [depth, contour] of subtree.contours) {
          const prior = merged.get(depth);
          merged.set(depth, {
            left: Math.min(prior?.left ?? Infinity, contour.left + offset),
            right: Math.max(prior?.right ?? -Infinity, contour.right + offset),
          });
        }
      }
      const midpoint = offsets.length ? (offsets[0] + offsets.at(-1)) / 2 : 0;
      const halfWidth = projectedSize(nodeId).acrossExtent / 2;
      const contours = new Map([[0, { left: -halfWidth, right: halfWidth }]]);
      for (const [depth, contour] of merged) {
        contours.set(depth + 1, { left: contour.left - midpoint, right: contour.right - midpoint });
      }
      packed.set(nodeId, {
        points: [{ id: nodeId, depth: 0, across: 0 }, ...points.map((point) => ({ ...point, across: point.across - midpoint }))],
        contours,
      });
    }
    const points = packed.get(id).points;
    const levelSizes = [];
    points.forEach((point) => {
      levelSizes[point.depth] = Math.max(levelSizes[point.depth] ?? 0, projectedSize(point.id).forwardExtent);
    });
    const forwards = [0];
    for (let depth = 1; depth < levelSizes.length; depth++) {
      forwards[depth] = forwards[depth - 1] + (levelSizes[depth - 1] + levelSizes[depth]) / 2 + gap;
    }
    const boxes = points.map((point) => ({
      ...point,
      forward: forwards[point.depth],
      ...projectedSize(point.id),
    }));
    return { id, angle, span, cos, sin, boxes, rootProjection: projectedSize(tree.rootNodeId) };
  });

  let baseRadius = Math.max(120, ...branches.map((branch) =>
    (branch.rootProjection.forwardExtent + branch.boxes[0].forwardExtent) / 2 + gap));
  for (let i = 0; i < branches.length; i++) {
    for (let j = i + 1; j < branches.length; j++) {
      const a = branches[i], b = branches[j];
      const aSize = sizeOf(a.id), bSize = sizeOf(b.id);
      const dx = Math.abs(a.cos - b.cos), dy = Math.abs(a.sin - b.sin);
      baseRadius = Math.max(baseRadius, Math.min(
        dx > 1e-10 ? ((aSize.width + bSize.width) / 2 + gap) / dx : Infinity,
        dy > 1e-10 ? ((aSize.height + bSize.height) / 2 + gap) / dy : Infinity,
      ));
    }
  }
  baseRadius = Math.ceil(baseRadius) + 1;
  const rootSize = sizeOf(tree.rootNodeId);
  const placed = [{ x: rootCenter.x - rootSize.width / 2, y: rootCenter.y - rootSize.height / 2, ...rootSize }];
  const separated = (a, b) =>
    a.x + a.width + gap <= b.x || b.x + b.width + gap <= a.x
    || a.y + a.height + gap <= b.y || b.y + b.height + gap <= a.y;
  const boxAt = (branch, box, offset = 0) => {
    const size = sizeOf(box.id);
    return {
      id: box.id,
      x: rootCenter.x + branch.cos * (baseRadius + box.forward + offset) - branch.sin * box.across - size.width / 2,
      y: rootCenter.y + branch.sin * (baseRadius + box.forward + offset) + branch.cos * box.across - size.height / 2,
      ...size,
    };
  };
  for (const branch of branches) {
    const box = boxAt(branch, branch.boxes[0]);
    positions.set(box.id, { x: box.x, y: box.y });
    placed.push(box);
  }
  for (const branch of branches) {
    let offset = 0;
    const branchBoxes = () => branch.boxes.slice(1).map((box) => boxAt(branch, box, offset));
    let boxes = branchBoxes();
    while (boxes.some((box) => placed.some((prior) => !separated(box, prior)))) {
      offset += 8;
      boxes = branchBoxes();
    }
    boxes.forEach(({ id, x, y }) => positions.set(id, { x, y }));
    placed.push(...boxes);
  }
  return positions;
}
