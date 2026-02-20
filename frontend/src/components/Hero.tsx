"use client";

import React from "react";

type Props = {
  onPrimary: () => void;
};

export default function Hero({ onPrimary }: Props) {
  return (
    <section className="mx-auto max-w-6xl px-6 py-20 lg:py-28">
      <div className="flex flex-col items-center text-center">
          <span className="inline-block rounded-full bg-[#dcfce7] px-3 py-1 text-xs font-semibold uppercase tracking-widest text-[#15803d]">
            Your AI career guide
          </span>
          <h1 className="mt-4 text-4xl font-bold leading-tight tracking-tight text-[#14532d] sm:text-5xl">
            Grow your path,<br />
            <span className="text-[#16a34a]">branch by branch.</span>
          </h1>
          <p className="mt-5 max-w-xl text-lg leading-relaxed text-[#374151]">
            BranchingOutAI maps your career like a tree — exploring your interests,
            skills, and industry to suggest meaningful next steps.
          </p>
          <div className="mt-8 flex flex-wrap justify-center gap-3">
            <button
              onClick={onPrimary}
              className="cursor-pointer rounded-full bg-[#16a34a] px-6 py-3 text-sm font-semibold text-white shadow-md transition hover:bg-[#15803d]"
            >
              Start growing →
            </button>
            <a
              href="#features"
              className="inline-flex items-center rounded-full border border-[#86efac] px-6 py-3 text-sm font-medium text-[#15803d] transition hover:bg-[#f0fff4]"
            >
              See how it works
            </a>
          </div>
      </div>
    </section>
  );
}
