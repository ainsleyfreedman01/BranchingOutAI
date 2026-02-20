"use client";

import React, { useState } from "react";

type Props = {
  onLogin: () => void;
  onSignup: () => void;
};

export default function Navbar({ onLogin, onSignup }: Props) {
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <header className="sticky top-0 z-40 border-b border-[#bbf7d0] bg-[#f7fdf9]/90 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
        {/* Logo */}
        <div className="flex items-center gap-2">
          <svg width="28" height="28" viewBox="0 0 28 28" fill="none" aria-hidden="true">
            {/* Simple stylised tree */}
            <rect x="12" y="16" width="4" height="9" rx="1.5" fill="#16a34a" />
            <ellipse cx="14" cy="12" rx="8" ry="8" fill="#4ade80" />
            <ellipse cx="9" cy="10" rx="5" ry="5" fill="#86efac" />
            <ellipse cx="19" cy="10" rx="5" ry="5" fill="#86efac" />
          </svg>
          <span className="text-lg font-semibold tracking-tight text-[#14532d]">
            BranchingOut<span className="text-[#16a34a]">AI</span>
          </span>
        </div>

        {/* Desktop nav */}
        <nav className="hidden items-center gap-2 sm:flex">
          <button
            onClick={onLogin}
            className="cursor-pointer rounded-lg px-4 py-2 text-sm font-medium text-[#15803d] transition hover:bg-[#dcfce7]"
          >
            Log in
          </button>
          <button
            onClick={onSignup}
            className="cursor-pointer rounded-full bg-[#16a34a] px-5 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-[#15803d]"
          >
            Get started
          </button>
        </nav>

        {/* Mobile hamburger */}
        <button
          className="cursor-pointer sm:hidden text-[#15803d]"
          onClick={() => setMenuOpen((v) => !v)}
          aria-label="Toggle menu"
        >
          {menuOpen ? (
            <svg width="22" height="22" fill="none" stroke="currentColor" strokeWidth="2"><line x1="4" y1="4" x2="18" y2="18"/><line x1="18" y1="4" x2="4" y2="18"/></svg>
          ) : (
            <svg width="22" height="22" fill="none" stroke="currentColor" strokeWidth="2"><line x1="3" y1="7" x2="19" y2="7"/><line x1="3" y1="13" x2="19" y2="13"/><line x1="3" y1="19" x2="19" y2="19"/></svg>
          )}
        </button>
      </div>

      {/* Mobile menu */}
      {menuOpen && (
        <div className="border-t border-[#bbf7d0] bg-[#f0fff4] px-6 py-4 flex flex-col gap-3 sm:hidden">
          <button onClick={() => { setMenuOpen(false); onLogin(); }} className="cursor-pointer text-left text-sm font-medium text-[#15803d]">Log in</button>
          <button onClick={() => { setMenuOpen(false); onSignup(); }} className="cursor-pointer rounded-full bg-[#16a34a] px-5 py-2 text-sm font-semibold text-white text-center">Get started</button>
        </div>
      )}
    </header>
  );
}
