"use client";

import React from "react";

type Props = {
  onPrimary: () => void;
};

export default function Hero({ onPrimary }: Props) {
  return (
    <section className="mx-auto max-w-6xl px-6 py-20 lg:py-28">
      <div className="flex flex-col items-center text-center">
          <span className="inline-block rounded-full bg-primary-100 px-3 py-1 text-xs font-semibold uppercase tracking-widest text-primary-700">
            Your AI career guide
          </span>
          <h1 className="mt-4 text-4xl font-bold leading-tight tracking-tight text-primary-900 sm:text-5xl">
            Grow your path,<br />
            <span className="text-primary-600">branch by branch.</span>
          </h1>
          <p className="mt-5 max-w-xl text-lg leading-relaxed text-neutral-700">
            BranchingOutAI maps your career like a tree — exploring your interests,
            skills, and industry to suggest meaningful next steps.
          </p>
          <div className="mt-8 flex flex-wrap justify-center gap-3">
            <button
              onClick={onPrimary}
              className="cursor-pointer rounded-full bg-primary-600 px-6 py-3 text-sm font-semibold text-white shadow-md transition hover:bg-primary-700"
            >
              Start growing →
            </button>
            <a
              href="#features"
              className="inline-flex items-center rounded-full border border-primary-300 px-6 py-3 text-sm font-medium text-primary-700 transition hover:bg-primary-50"
            >
              See how it works
            </a>
          </div>
      </div>
    </section>
  );
}
