import assert from "node:assert/strict";
import test from "node:test";
import { CAREER_NODE_SIZE, radialTreeLayout } from "./radialTreeLayout.mjs";

test("compact nodes preserve space for the 48-by-64 branch toggle target", () => {
  assert.deepEqual(CAREER_NODE_SIZE, { width: 200, height: 64 });
  assert.ok(CAREER_NODE_SIZE.width >= 48);
  assert.ok(CAREER_NODE_SIZE.height >= 64);
});

function makeTree(count) {
  return {
    rootNodeId: "root",
    nodes: [{ id: "root", label: "You" }, ...Array.from({ length: count }, (_, i) => ({ id: `n${i}`, label: `Interest ${String(i).padStart(2, "0")}` }))],
    edges: Array.from({ length: count }, (_, i) => ({ source: "root", target: `n${i}` })),
  };
}

function center(position) {
  return { x: position.x + CAREER_NODE_SIZE.width / 2, y: position.y + CAREER_NODE_SIZE.height / 2 };
}

test("twelve interests surround the root in all four directions without overlapping", () => {
  const origin = { x: 600, y: 400 };
  const positions = [...radialTreeLayout(makeTree(12), origin).values()];
  const centers = positions.map(center);
  for (const axis of ["x", "y"]) {
    assert.ok(centers.some((point) => point[axis] < origin[axis] - 100));
    assert.ok(centers.some((point) => point[axis] > origin[axis] + 100));
  }
  for (let i = 0; i < positions.length; i++) {
    for (let j = i + 1; j < positions.length; j++) {
      assert.ok(Math.abs(positions[i].x - positions[j].x) >= CAREER_NODE_SIZE.width + 16
        || Math.abs(positions[i].y - positions[j].y) >= CAREER_NODE_SIZE.height + 16);
    }
  }
});

test("descendants fan outward in their parent branch and remain separated", () => {
  const tree = makeTree(4);
  for (let i = 0; i < 10; i++) {
    tree.nodes.push({ id: `child${i}`, label: `Child ${i}` });
    tree.edges.push({ source: "n0", target: `child${i}` });
  }
  const positions = radialTreeLayout(tree, { x: 0, y: 0 });
  const parent = center(positions.get("n0"));
  for (let i = 0; i < 10; i++) {
    const child = center(positions.get(`child${i}`));
    assert.ok(child.y < 0);
    assert.ok(Math.hypot(child.x, child.y) > Math.hypot(parent.x, parent.y));
    for (let j = i + 1; j < 10; j++) {
      const sibling = center(positions.get(`child${j}`));
      assert.ok(Math.abs(child.x - sibling.x) >= CAREER_NODE_SIZE.width + 16
        || Math.abs(child.y - sibling.y) >= CAREER_NODE_SIZE.height + 16);
    }
  }
});

test("connections use a compact radius rather than a fixed 300px minimum", () => {
  const positions = radialTreeLayout(makeTree(4), { x: 0, y: 0 });
  const radii = [...positions.values()].map(center).map(({ x, y }) => Math.hypot(x, y));
  assert.ok(radii.every((radius) => radius < 270));
  const single = center(radialTreeLayout(makeTree(1), { x: 0, y: 0 }).get("n0"));
  assert.ok(Math.hypot(single.x, single.y) < 140);
});

test("deep branches stay close to their immediate parent instead of a narrow root-centered ring", () => {
  const tree = makeTree(12);
  for (let i = 0; i < 3; i++) {
    tree.nodes.push({ id: `industry${i}`, label: `Industry ${i}` });
    tree.edges.push({ source: "n4", target: `industry${i}` });
    tree.nodes.push({ id: `role${i}`, label: `Role ${i}` });
    tree.edges.push({ source: "industry1", target: `role${i}` });
  }
  const sizes = new Map(tree.nodes.map(({ id }) => [id, {
    width: id.startsWith("role") ? 360 : id.startsWith("industry") ? 340 : 240,
    height: 96,
  }]));
  const positions = radialTreeLayout(tree, { x: 0, y: 0 }, sizes);
  const nodeCenter = (id) => ({
    x: positions.get(id).x + sizes.get(id).width / 2,
    y: positions.get(id).y + sizes.get(id).height / 2,
  });
  for (const parentId of ["n4", "industry1"]) {
    const parent = nodeCenter(parentId);
    for (const { target } of tree.edges.filter(({ source }) => source === parentId)) {
      const child = nodeCenter(target);
      assert.ok(Math.hypot(child.x - parent.x, child.y - parent.y) < 550);
    }
  }
  const boxes = [...positions].map(([id, position]) => ({ ...position, ...sizes.get(id) }));
  for (let i = 0; i < boxes.length; i++) {
    for (let j = i + 1; j < boxes.length; j++) {
      const a = boxes[i], b = boxes[j];
      assert.ok(a.x + a.width + 16 <= b.x || b.x + b.width + 16 <= a.x
        || a.y + a.height + 16 <= b.y || b.y + b.height + 16 <= a.y);
    }
  }
});

test("layout is deterministic regardless of node and edge input order", () => {
  const tree = makeTree(12);
  const expected = radialTreeLayout(tree, { x: 0, y: 0 });
  assert.deepEqual(radialTreeLayout({ ...tree, nodes: [...tree.nodes].reverse(), edges: [...tree.edges].reverse() }, { x: 0, y: 0 }), expected);
});

test("variable-width titles remain centered on their ring and do not overlap", () => {
  const tree = makeTree(12);
  const sizes = new Map(tree.nodes.map(({ id }, index) => [id, { width: 240 + index * 70, height: 96 }]));
  const positions = radialTreeLayout(tree, { x: 0, y: 0 }, sizes);
  const boxes = [...positions].map(([id, position]) => ({ ...position, ...sizes.get(id) }));
  const radii = boxes.map(({ x, y, width, height }) => Math.hypot(x + width / 2, y + height / 2));
  assert.ok(radii.every((radius) => Math.abs(radius - radii[0]) < 0.001));
  for (let i = 0; i < boxes.length; i++) {
    for (let j = i + 1; j < boxes.length; j++) {
      const a = boxes[i], b = boxes[j];
      assert.ok(a.x + a.width + 16 <= b.x || b.x + b.width + 16 <= a.x
        || a.y + a.height + 16 <= b.y || b.y + b.height + 16 <= a.y);
    }
  }
});

test("empty, single-branch, cyclic and shared-descendant graphs stay finite", () => {
  assert.equal(radialTreeLayout(makeTree(0), { x: 0, y: 0 }).size, 0);
  const tree = makeTree(2);
  tree.nodes.push({ id: "shared", label: "Shared" });
  tree.edges.push({ source: "n0", target: "shared" }, { source: "n1", target: "shared" }, { source: "shared", target: "root" });
  const positions = radialTreeLayout(tree, { x: 0, y: 0 });
  assert.equal(positions.size, 3);
  for (const position of positions.values()) {
    assert.ok(Number.isFinite(position.x) && Number.isFinite(position.y));
  }
  assert.equal(radialTreeLayout(makeTree(1), { x: 0, y: 0 }).size, 1);
});

test("removing a branch redistributes the remaining siblings evenly", () => {
  const tree = makeTree(6);
  const original = radialTreeLayout(tree, { x: 0, y: 0 });
  tree.nodes = tree.nodes.filter(({ id }) => id !== "n2");
  tree.edges = tree.edges.filter(({ target }) => target !== "n2");
  const remaining = radialTreeLayout(tree, { x: 0, y: 0 });
  assert.equal(remaining.size, 5);
  assert.notDeepEqual(remaining.get("n3"), original.get("n3"));
  const angles = [...remaining.values()].map(center).map(({ x, y }) => Math.atan2(y, x)).sort((a, b) => a - b);
  angles.forEach((angle, index) => {
    const next = index === angles.length - 1 ? angles[0] + Math.PI * 2 : angles[index + 1];
    assert.ok(Math.abs(next - angle - Math.PI * 2 / 5) < 0.001);
  });
});

test("growing and collapsing a visible branch reflows neighboring interests", () => {
  const collapsed = makeTree(6);
  const expanded = {
    ...collapsed,
    nodes: [...collapsed.nodes],
    edges: [...collapsed.edges],
  };
  for (let i = 0; i < 4; i++) {
    expanded.nodes.push({ id: `child${i}`, label: `Child ${i}` });
    expanded.edges.push({ source: "n2", target: `child${i}` });
  }
  const before = radialTreeLayout(collapsed, { x: 0, y: 0 });
  const after = radialTreeLayout(expanded, { x: 0, y: 0 });
  assert.notDeepEqual(after.get("n1"), before.get("n1"));
  assert.notDeepEqual(after.get("n3"), before.get("n3"));
  assert.deepEqual(radialTreeLayout(collapsed, { x: 0, y: 0 }), before);
  assert.deepEqual(radialTreeLayout({
    ...expanded, nodes: [...expanded.nodes].reverse(), edges: [...expanded.edges].reverse(),
  }, { x: 0, y: 0 }), after);
});

test("large neighboring subtrees stay separated and grow in outward lanes", () => {
  const tree = makeTree(6);
  for (let i = 0; i < 6; i++) {
    for (let j = 0; j < 3; j++) {
      const child = `child-${i}-${j}`;
      tree.nodes.push({ id: child, label: child });
      tree.edges.push({ source: `n${i}`, target: child });
      for (let k = 0; k < 3; k++) {
        const leaf = `${child}-${k}`;
        tree.nodes.push({ id: leaf, label: leaf });
        tree.edges.push({ source: child, target: leaf });
      }
    }
  }
  const sizes = new Map(tree.nodes.map(({ id }, index) => [id, { width: 240 + index % 4 * 45, height: 96 }]));
  const positions = radialTreeLayout(tree, { x: 0, y: 0 }, sizes);
  const boxes = [...positions].map(([id, position]) => ({ id, ...position, ...sizes.get(id) }));
  boxes.push({ id: "root", x: -120, y: -48, ...sizes.get("root") });
  for (let i = 0; i < boxes.length; i++) {
    for (let j = i + 1; j < boxes.length; j++) {
      const a = boxes[i], b = boxes[j];
      assert.ok(a.x + a.width <= b.x || b.x + b.width <= a.x
        || a.y + a.height <= b.y || b.y + b.height <= a.y, `${a.id} overlaps ${b.id}`);
    }
  }
  for (let i = 0; i < 6; i++) {
    const angle = -Math.PI / 2 + i * Math.PI / 3;
    const forward = (id) => {
      const box = boxes.find((box) => box.id === id);
      return (box.x + box.width / 2) * Math.cos(angle) + (box.y + box.height / 2) * Math.sin(angle);
    };
    const edges = tree.edges.filter(({ target }) => target.startsWith(`child-${i}-`));
    for (const { source, target } of edges) {
      assert.ok(forward(target) > forward(source), `${target} does not grow outward`);
    }
  }
});

test("expanded interests stay on one compact circular ring with wider titles", () => {
  const tree = makeTree(12);
  for (let i = 0; i < 3; i++) {
    tree.nodes.push({ id: `industry${i}`, label: `Industry ${i}` });
    tree.edges.push({ source: "n4", target: `industry${i}` });
    tree.nodes.push({ id: `role${i}`, label: `Role ${i}` });
    tree.edges.push({ source: "industry1", target: `role${i}` });
  }
  const sizes = new Map(tree.nodes.map(({ id }, index) => [id, {
    width: 240 + index % 4 * 16, height: 96,
  }]));
  const positions = radialTreeLayout(tree, { x: 0, y: 0 }, sizes);
  const radii = tree.nodes.filter(({ id }) => id.startsWith("n")).map(({ id }) => ({
    x: positions.get(id).x + sizes.get(id).width / 2,
    y: positions.get(id).y + sizes.get(id).height / 2,
  }))
    .map(({ x, y }) => Math.hypot(x, y));
  assert.ok(radii.every((radius) => radius < 700));
  assert.ok(radii.every((radius) => Math.abs(radius - radii[0]) < 0.001),
    "expanded interests must remain on the same circular ring");
});

for (const count of [0, 1, 2, 3, 5, 8, 12, 20, 32, 64, 100]) {
  test(`${count} interests use an account-independent circular layout before and after expansion`, () => {
    const tree = makeTree(count);
    const rootId = `account-${count}-name`;
    tree.rootNodeId = rootId;
    tree.nodes[0].id = rootId;
    tree.edges.forEach((edge) => { edge.source = rootId; });
    const origin = { x: 137 + count, y: -219 - count };
    for (const expanded of [false, true]) {
      if (expanded) {
        for (let i = 0; i < count; i += 3) {
          for (let j = 0; j < 3; j++) {
            const id = `child-${i}-${j}`;
            tree.nodes.push({ id, label: `Branch ${i} child ${j}` });
            tree.edges.push({ source: `n${i}`, target: id });
          }
        }
      }
      const sizes = new Map(tree.nodes.map(({ id }, index) => [id, {
        width: 240 + index % 5 * 36,
        height: 96 + index % 3 * 8,
      }]));
      const positions = radialTreeLayout(tree, origin, sizes);
      assert.equal(positions.size, tree.nodes.length - 1);
      const boxes = [{ ...sizes.get(rootId), x: origin.x - sizes.get(rootId).width / 2,
        y: origin.y - sizes.get(rootId).height / 2 },
      ...[...positions].map(([id, position]) => ({ ...position, ...sizes.get(id) }))];
      for (let i = 0; i < boxes.length; i++) {
        const a = boxes[i];
        assert.ok(Number.isFinite(a.x) && Number.isFinite(a.y));
        for (let j = i + 1; j < boxes.length; j++) {
          const b = boxes[j];
          assert.ok(a.x + a.width + 16 <= b.x || b.x + b.width + 16 <= a.x
            || a.y + a.height + 16 <= b.y || b.y + b.height + 16 <= a.y,
          `nodes ${i} and ${j} overlap for ${count} interests`);
        }
      }
      const radii = Array.from({ length: count }, (_, i) => {
        const id = `n${i}`, position = positions.get(id), size = sizes.get(id);
        return Math.hypot(position.x + size.width / 2 - origin.x,
          position.y + size.height / 2 - origin.y);
      });
      assert.ok(radii.every((radius) => Math.abs(radius - radii[0]) < 0.001));
      assert.deepEqual(radialTreeLayout({
        ...tree, nodes: [...tree.nodes].reverse(), edges: [...tree.edges].reverse(),
      }, origin, sizes), positions);
    }
  });
}
