"use client";

import React from "react";

type Props = {
  onCTAClick: () => void;
};

export default function CTA({ onCTAClick }: Props) {
  return (
    <section className="py-20">
      <div className="mx-auto max-w-3xl px-6 text-center">
        <div className="rounded-3xl border border-[#bbf7d0] bg-gradient-to-br from-[#f0fff4] to-[#dcfce7] p-12 shadow-sm">
          {/* Decorative tree */}
          <div className="mb-6 flex justify-center">
            <svg width="56" height="56" viewBox="0 0 56 56" fill="none" aria-hidden="true">
              <rect x="24" y="34" width="8" height="16" rx="3" fill="#15803d" />
              <ellipse cx="28" cy="24" rx="16" ry="16" fill="#4ade80" />
              <ellipse cx="18" cy="20" rx="10" ry="10" fill="#86efac" />
              <ellipse cx="38" cy="20" rx="10" ry="10" fill="#86efac" />
              <ellipse cx="28" cy="14" rx="9" ry="9" fill="#bbf7d0" />
            </svg>
          </div>
          <h2 className="text-3xl font-bold text-[#14532d]">
            Ready to grow?
          </h2>
          <p className="mt-3 text-base text-[#374151]">
            Join BranchingOutAI and start building a career map that's as unique as you are.
          </p>
          <div className="mt-8 flex flex-wrap justify-center gap-3">
            <button
              onClick={onCTAClick}
              className="cursor-pointer rounded-full bg-[#16a34a] px-8 py-3 text-sm font-semibold text-white shadow-md transition hover:bg-[#15803d]"
            >
              Create your free account
            </button>
          </div>
          <p className="mt-4 text-xs text-[#6b7280]">No credit card required. Free to start.</p>
        </div>
      </div>
    </section>
  );
}
