"use client";

import React from "react";
import { useRouter } from "next/navigation";
import type { User } from "@supabase/supabase-js";

type Props = {
  user: User | null;
  onCTAClick: () => void;
};

export default function CTA({ user, onCTAClick }: Props) {
  const router = useRouter();

  return (
    <section className="py-20">
      <div className="mx-auto max-w-3xl px-6 text-center">
        <div className="rounded-3xl border border-primary-200 bg-gradient-to-br from-primary-50 to-primary-100 p-12 shadow-sm">
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
          <h2 className="text-3xl font-bold text-primary-900">
            Ready to grow?
          </h2>
          <p className="mt-3 text-base text-neutral-700">
            {user
              ? "Pick up where you left off and keep building your career tree."
              : "Join BranchingOutAI and start building a career map that\u2019s as unique as you are."}
          </p>
          <div className="mt-8 flex flex-wrap justify-center gap-3">
            {user ? (
              <button
                onClick={() => router.push("/graph")}
                className="cursor-pointer rounded-full bg-primary-600 px-8 py-3 text-sm font-semibold text-white shadow-md transition hover:bg-primary-700"
              >
                Go to my graph →
              </button>
            ) : (
              <button
                onClick={onCTAClick}
                className="cursor-pointer rounded-full bg-primary-600 px-8 py-3 text-sm font-semibold text-white shadow-md transition hover:bg-primary-700"
              >
                Create your free account
              </button>
            )}
          </div>
          {!user && (
            <p className="mt-4 text-xs text-neutral-500">No credit card required. Free to start.</p>
          )}
        </div>
      </div>
    </section>
  );
}
