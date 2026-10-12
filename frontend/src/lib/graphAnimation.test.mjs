import assert from "node:assert/strict";
import test from "node:test";
import { animateGraphFrames } from "./graphAnimation.mjs";

function clock() {
  let nextId = 0;
  const frames = new Map();
  return {
    requestFrame: (callback) => { frames.set(++nextId, callback); return nextId; },
    cancelFrame: (id) => frames.delete(id),
    tick: (time) => {
      const pending = [...frames.values()];
      frames.clear();
      pending.forEach((callback) => callback(time));
    },
    pending: () => frames.size,
  };
}

test("branch animation moves smoothly from start to end and completes once", () => {
  const timer = clock();
  const values = [];
  let completed = 0;
  animateGraphFrames((progress) => values.push(progress), () => completed++, timer);
  timer.tick(100);
  timer.tick(260);
  timer.tick(420);
  assert.deepEqual(values, [0, 0.875, 1]);
  assert.equal(completed, 1);
  assert.equal(timer.pending(), 0);
});

test("interrupted animation cannot run stale completion or frames", () => {
  const timer = clock();
  let frames = 0;
  let completed = false;
  const stop = animateGraphFrames(() => frames++, () => { completed = true; }, timer);
  timer.tick(0);
  stop();
  timer.tick(500);
  assert.equal(frames, 1);
  assert.equal(completed, false);
  assert.equal(timer.pending(), 0);
});
