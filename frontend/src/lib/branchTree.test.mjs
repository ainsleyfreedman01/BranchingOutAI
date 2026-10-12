import assert from "node:assert/strict";
import test from "node:test";
import { branchTree } from "./branchTree.mjs";
import { radialTreeLayout } from "./radialTreeLayout.mjs";

test("shared concepts get local linked copies without altering stored nodes", () => {
  const tree = {
    rootNodeId: "you",
    nodes: ["you", "data", "studies", "education", "role"].map((id) => ({ id, label: id })),
    edges: [["you", "data"], ["you", "studies"], ["data", "education"], ["studies", "education"], ["education", "role"]]
      .map(([source, target]) => ({ id: `${source}->${target}`, source, target })),
    expandedNodeIds: ["you", "data", "studies", "education"],
  };
  const before = structuredClone(tree);
  const projected = branchTree(tree);
  assert.deepEqual(tree, before);
  const copies = projected.nodes.filter(({ originalId }) => originalId === "education");
  assert.equal(copies.length, 2);
  assert.notEqual(copies[0].id, copies[1].id);
  assert.ok(copies.every(({ id }) => projected.expandedNodeIds.includes(id)));
  assert.equal(projected.nodes.filter(({ originalId }) => originalId === "role").length, 2);
  const positions = radialTreeLayout(projected, { x: 0, y: 0 });
  for (const edge of projected.edges.filter(({ source }) => source !== "you")) {
    const a = positions.get(edge.source), b = positions.get(edge.target);
    assert.ok(Math.hypot(a.x - b.x, a.y - b.y) < 550);
  }
  assert.deepEqual(branchTree({ ...tree, nodes: [...tree.nodes].reverse(), edges: [...tree.edges].reverse() }), projected);
});

test("projection avoids cycles and duplicate edges", () => {
  const projected = branchTree({
    rootNodeId: "you", nodes: ["you", "a"].map((id) => ({ id, label: id })),
    edges: [
      { id: "one", source: "you", target: "a" },
      { id: "two", source: "you", target: "a" },
      { id: "back", source: "a", target: "you" },
    ],
    expandedNodeIds: ["you"],
  });
  assert.equal(projected.nodes.length, 2);
  assert.equal(projected.edges.length, 1);
});
