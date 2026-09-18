"use client";

import React from "react";

export default function Footer() {
  return (
    <footer className="border-t border-primary-200 bg-background-light py-8">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 text-sm text-neutral-500">
        <div className="flex items-center gap-2">
          <svg width="20" height="20" viewBox="0 0 28 28" fill="none" aria-hidden="true">
            <rect x="12" y="16" width="4" height="9" rx="1.5" fill="#16a34a" />
            <ellipse cx="14" cy="12" rx="8" ry="8" fill="#4ade80" />
            <ellipse cx="9" cy="10" rx="5" ry="5" fill="#86efac" />
            <ellipse cx="19" cy="10" rx="5" ry="5" fill="#86efac" />
          </svg>
          <span className="font-medium text-primary-900">BranchingOutAI</span>
        </div>
        <div className="flex items-center gap-4">
          <a href="/privacy" className="hover:text-primary-700 hover:underline">Privacy</a>
          <a href="/terms" className="hover:text-primary-700 hover:underline">Terms</a>
          <p>© {new Date().getFullYear()} BranchingOutAI. All rights reserved.</p>
        </div>
      </div>
    </footer>
  );
}
