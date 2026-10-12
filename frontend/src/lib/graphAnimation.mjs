export function animateGraphFrames(onFrame, onComplete, {
  duration = 320,
  requestFrame = globalThis.requestAnimationFrame,
  cancelFrame = globalThis.cancelAnimationFrame,
} = {}) {
  let start;
  let frameId;
  const step = (time) => {
    start ??= time;
    const progress = Math.min(1, (time - start) / duration);
    onFrame(1 - (1 - progress) ** 3);
    if (progress === 1) onComplete();
    else frameId = requestFrame(step);
  };
  frameId = requestFrame(step);
  return () => cancelFrame(frameId);
}
