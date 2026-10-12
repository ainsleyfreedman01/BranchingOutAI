export function animateGraphFrames(
  onFrame: (progress: number) => void,
  onComplete: () => void,
  options?: {
    duration?: number;
    requestFrame?: typeof requestAnimationFrame;
    cancelFrame?: typeof cancelAnimationFrame;
  },
): () => void;
