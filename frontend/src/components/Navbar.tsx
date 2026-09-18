"use client";

import React, { useState } from "react";
import Link from "next/link";
import type { User } from "@supabase/supabase-js";

type Props = {
  user: User | null;
  onLogin: () => void;
  onSignup: () => void;
  onSignOut: () => void;
};

export default function Navbar({ user, onLogin, onSignup, onSignOut }: Props) {
  const [menuOpen, setMenuOpen] = useState(false);

  const firstName = user?.user_metadata?.first_name as string | undefined;
  const displayName = firstName ?? user?.email ?? "";

  return (
    <header className="sticky top-0 z-40 border-b border-primary-200 bg-background-light/90 backdrop-blur">
      <div className="flex items-center justify-between px-12 py-4">
        {/* Logo */}
        {user ? (
          <div className="flex items-center gap-2">
            <svg width="28" height="28" viewBox="0 0 28 28" fill="none" aria-hidden="true">
              <rect x="12" y="17" width="4" height="8" rx="1.5" fill="#15803d" />
              <ellipse cx="14" cy="12" rx="8" ry="8" fill="#4ade80" />
              <ellipse cx="9" cy="10" rx="5" ry="5" fill="#86efac" />
              <ellipse cx="19" cy="10" rx="5" ry="5" fill="#86efac" />
              <ellipse cx="14" cy="7" rx="4.5" ry="4.5" fill="#bbf7d0" />
            </svg>
            <span className="text-lg font-semibold tracking-tight text-primary-900">
              BranchingOut<span className="text-primary-600">AI</span>
            </span>
          </div>
        ) : (
          <Link href="/" className="flex items-center gap-2">
            <svg width="28" height="28" viewBox="0 0 28 28" fill="none" aria-hidden="true">
              <rect x="12" y="17" width="4" height="8" rx="1.5" fill="#15803d" />
              <ellipse cx="14" cy="12" rx="8" ry="8" fill="#4ade80" />
              <ellipse cx="9" cy="10" rx="5" ry="5" fill="#86efac" />
              <ellipse cx="19" cy="10" rx="5" ry="5" fill="#86efac" />
              <ellipse cx="14" cy="7" rx="4.5" ry="4.5" fill="#bbf7d0" />
            </svg>
            <span className="text-lg font-semibold tracking-tight text-primary-900">
              BranchingOut<span className="text-primary-600">AI</span>
            </span>
          </Link>
        )}

        {/* Desktop nav */}
        <nav className="hidden items-center gap-5 sm:flex">
          {user ? (
            <>
              <span className="text-sm text-neutral-700">
                Hi, <span className="font-medium text-primary-700">{displayName}</span>!
              </span>
              <Link
                href="/profile"
                className="rounded-lg px-3 py-2 text-sm font-medium text-primary-700 transition hover:bg-primary-100"
              >
                Account
              </Link>
              <button
                onClick={onSignOut}
                className="cursor-pointer rounded-lg bg-primary-100 px-4 py-2 text-sm font-medium text-primary-700 transition hover:bg-primary-200"
              >
                Sign out
              </button>
            </>
          ) : (
            <>
              <button
                onClick={onLogin}
                className="cursor-pointer rounded-lg px-4 py-2 text-sm font-medium text-primary-700 transition hover:bg-primary-100"
              >
                Log in
              </button>
              <button
                onClick={onSignup}
                className="cursor-pointer rounded-full bg-primary-600 px-5 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-primary-700"
              >
                Get started
              </button>
            </>
          )}
        </nav>

        {/* Mobile hamburger */}
        <button
          className="cursor-pointer sm:hidden text-primary-700"
          onClick={() => setMenuOpen((v) => !v)}
          aria-label="Toggle menu"
          aria-expanded={menuOpen}
          aria-controls="mobile-menu"
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
        <div id="mobile-menu" className="border-t border-primary-200 bg-primary-50 px-6 py-4 flex flex-col gap-3 sm:hidden">
          {user ? (
            <>
              <span className="text-sm text-neutral-700">Hi, <span className="font-medium text-primary-700">{displayName}</span>!</span>
              <Link
                href="/profile"
                onClick={() => setMenuOpen(false)}
                className="rounded-lg px-4 py-2 text-sm font-medium text-primary-700 hover:bg-primary-100"
              >
                Account
              </Link>
              <button onClick={() => { setMenuOpen(false); onSignOut(); }} className="cursor-pointer rounded-lg bg-primary-100 px-4 py-2 text-sm font-medium text-primary-700 transition hover:bg-primary-200">Sign out</button>
            </>
          ) : (
            <>
              <button onClick={() => { setMenuOpen(false); onLogin(); }} className="cursor-pointer text-left text-sm font-medium text-primary-700">Log in</button>
              <button onClick={() => { setMenuOpen(false); onSignup(); }} className="cursor-pointer rounded-full bg-primary-600 px-5 py-2 text-sm font-semibold text-white text-center">Get started</button>
            </>
          )}
        </div>
      )}
    </header>
  );
}
