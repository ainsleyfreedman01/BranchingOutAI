"use client";

import React, { useState } from "react";

type Props = {
  mode: "login" | "signup";
  open: boolean;
  onClose: () => void;
  onSwitch: () => void;
};

function EyeIcon({ open }: { open: boolean }) {
  return open ? (
    <svg width="18" height="18" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
      <path d="M1 10s3.5-6 9-6 9 6 9 6-3.5 6-9 6-9-6-9-6Z" />
      <circle cx="10" cy="10" r="2.5" />
    </svg>
  ) : (
    <svg width="18" height="18" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 3l14 14" />
      <path d="M10.5 5.1A8.5 8.5 0 0 1 19 10s-1.3 2.6-3.5 4.2" />
      <path d="M6.5 6.5C4.2 7.9 1 10 1 10s3.5 6 9 6c1.6 0 3-.4 4.2-1" />
      <path d="M8 10a2.5 2.5 0 0 0 4 2" />
    </svg>
  );
}

export default function AuthModal({ mode, open, onClose, onSwitch }: Props) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);

  if (!open) return null;

  const title = mode === "login" ? "Welcome back" : "Create your account";
  const action = mode === "login" ? "Log in" : "Sign up";
  const switchPrompt = mode === "login"
    ? "Don't have an account?"
    : "Already have an account?";

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="mx-4 w-full max-w-md rounded-2xl border border-[#bbf7d0] bg-white p-8 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="mb-6 flex items-start justify-between">
          <div>
            <h2 className="text-xl font-bold text-[#14532d]">{title}</h2>
            <p className="mt-1 text-sm text-[#6b7280]">
              {mode === "login"
                ? "Log in to continue your journey."
                : "Start growing your career tree today."}
            </p>
          </div>
          <button
            onClick={onClose}
            className="cursor-pointer ml-4 rounded-full p-1 text-[#6b7280] hover:bg-[#f0fff4] hover:text-[#15803d]"
            aria-label="Close"
          >
            <svg width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2"><line x1="3" y1="3" x2="15" y2="15"/><line x1="15" y1="3" x2="3" y2="15"/></svg>
          </button>
        </div>

        {/* Form */}
        <form className="space-y-4" onSubmit={(e) => e.preventDefault()}>
          <div>
            <label className="mb-1 block text-sm font-medium text-[#374151]">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              className="w-full rounded-lg border border-[#d1d5db] bg-[#f9fafb] px-4 py-2.5 text-sm outline-none focus:border-[#16a34a] focus:ring-2 focus:ring-[#dcfce7]"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-[#374151]">Password</label>
            <div className="relative">
              <input
                type={showPassword ? "text" : "password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full rounded-lg border border-[#d1d5db] bg-[#f9fafb] px-4 py-2.5 pr-10 text-sm outline-none focus:border-[#16a34a] focus:ring-2 focus:ring-[#dcfce7]"
              />
              <button
                type="button"
                onClick={() => setShowPassword((v) => !v)}
                className="cursor-pointer absolute right-3 top-1/2 -translate-y-1/2 text-[#9ca3af] hover:text-[#15803d]"
                aria-label={showPassword ? "Hide password" : "Show password"}
              >
                <EyeIcon open={showPassword} />
              </button>
            </div>
          </div>

          <button
            type="submit"
            className="cursor-pointer w-full rounded-full bg-[#16a34a] py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-[#15803d]"
          >
            {action}
          </button>
        </form>

        <p className="mt-5 text-center text-sm text-[#6b7280]">
          {switchPrompt}{" "}
          <button onClick={onSwitch} className="cursor-pointer font-medium text-[#16a34a] hover:underline">
            {mode === "login" ? "Sign up" : "Log in"}
          </button>
        </p>
      </div>
    </div>
  );
}
