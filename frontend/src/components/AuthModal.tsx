"use client";

import React, { useEffect, useId, useState } from "react";
import { supabase } from "@/lib/supabase";

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

function clearForm(
  setFirstName: (v: string) => void,
  setLastName: (v: string) => void,
  setEmail: (v: string) => void,
  setPassword: (v: string) => void,
  setError: (v: string | null) => void,
  setShowPassword: (v: boolean) => void,
) {
  setFirstName("");
  setLastName("");
  setEmail("");
  setPassword("");
  setError(null);
  setShowPassword(false);
}

export default function AuthModal({ mode, open, onClose, onSwitch }: Props) {
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [awaitingConfirmation, setAwaitingConfirmation] = useState(false);
  const [resetSent, setResetSent] = useState(false);
  const [acceptedTerms, setAcceptedTerms] = useState(false);
  const titleId = useId();
  const errorId = useId();

  useEffect(() => {
    if (!open) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [open, onClose]);

  if (!open) return null;

  const title = mode === "login" ? "Welcome back" : "Create your account";
  const action = mode === "login" ? "Log in" : "Sign up";
  const switchPrompt = mode === "login"
    ? "Don't have an account?"
    : "Already have an account?";

  function handleSwitch() {
    clearForm(setFirstName, setLastName, setEmail, setPassword, setError, setShowPassword);
    setAwaitingConfirmation(false);
    setResetSent(false);
    setAcceptedTerms(false);
    onSwitch();
  }

  function handleClose() {
    clearForm(setFirstName, setLastName, setEmail, setPassword, setError, setShowPassword);
    setAwaitingConfirmation(false);
    setResetSent(false);
    setAcceptedTerms(false);
    onClose();
  }

  async function handleForgotPassword() {
    if (!email) { setError("Enter your email above first."); return; }
    setError(null);
    setLoading(true);
    try {
      const { error: resetError } = await supabase.auth.resetPasswordForEmail(email, {
        redirectTo: `${window.location.origin}/reset-password`,
      });
      if (resetError) { setError(resetError.message); return; }
      setResetSent(true);
    } finally {
      setLoading(false);
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (mode === "signup" && !acceptedTerms) {
      setError("Please accept the Terms of Service and Privacy Policy to continue.");
      return;
    }
    setLoading(true);
    try {
      if (mode === "signup") {
        const { data, error: signUpError } = await supabase.auth.signUp({
          email,
          password,
          options: {
            data: {
              first_name: firstName.trim(),
              last_name: lastName.trim(),
              full_name: `${firstName.trim()} ${lastName.trim()}`.trim(),
            },
          },
        });
        if (signUpError) { setError(signUpError.message); return; }
        // If email confirmation is required, session will be null
        if (!data.session) {
          setAwaitingConfirmation(true);
          return;
        }
      } else {
        const { error: signInError } = await supabase.auth.signInWithPassword({ email, password });
        if (signInError) { setError(signInError.message); return; }
      }
      handleClose();
    } finally {
      setLoading(false);
    }
  }

  const closeBtn = (
    <button
      onClick={handleClose}
      className="cursor-pointer ml-4 rounded-full p-1 text-neutral-500 hover:bg-primary-50 hover:text-primary-700"
      aria-label="Close"
    >
      <svg width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2"><line x1="3" y1="3" x2="15" y2="15"/><line x1="15" y1="3" x2="3" y2="15"/></svg>
    </button>
  );

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm"
      onClick={handleClose}
      role="presentation"
    >
      <div
        className="mx-4 w-full max-w-md rounded-2xl border border-primary-200 bg-white p-8 shadow-xl"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
      >
        {/* ── Awaiting email confirmation ── */}
        {awaitingConfirmation ? (
          <div className="text-center">
            <div className="mb-4 flex justify-end">{closeBtn}</div>
            <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-primary-100">
              <svg width="24" height="24" fill="none" stroke="#16a34a" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/>
                <polyline points="22,6 12,13 2,6"/>
              </svg>
            </div>
            <h2 id={titleId} className="text-xl font-bold text-primary-900">Check your inbox</h2>
            <p className="mt-2 text-sm text-neutral-500">
              We sent a confirmation link to <span className="font-medium text-neutral-700">{email}</span>.
              Click it to activate your account.
            </p>
            <button
              onClick={handleClose}
              className="cursor-pointer mt-6 rounded-full bg-primary-600 px-8 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-primary-700"
            >
              Got it
            </button>
          </div>
        ) : (
          <>
            {/* Header */}
            <div className="mb-6 flex items-start justify-between">
              <div>
                <h2 id={titleId} className="text-xl font-bold text-primary-900">{title}</h2>
                <p className="mt-1 text-sm text-neutral-500">
                  {mode === "login"
                    ? "Log in to continue your journey."
                    : "Start growing your career tree today."}
                </p>
              </div>
              {closeBtn}
            </div>

            {/* Form */}
            <form className="space-y-4" onSubmit={handleSubmit}>
              {/* First + Last name — signup only */}
              {mode === "signup" && (
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label htmlFor="first-name" className="mb-1 block text-sm font-medium text-neutral-700">First name</label>
                    <input
                      id="first-name"
                      type="text"
                      value={firstName}
                      onChange={(e) => setFirstName(e.target.value)}
                      placeholder="Jane"
                      required
                      className="w-full rounded-lg border border-neutral-300 bg-neutral-50 px-4 py-2.5 text-sm outline-none focus:border-primary-600 focus:ring-2 focus:ring-primary-100"
                    />
                  </div>
                  <div>
                    <label htmlFor="last-name" className="mb-1 block text-sm font-medium text-neutral-700">Last name</label>
                    <input
                      id="last-name"
                      type="text"
                      value={lastName}
                      onChange={(e) => setLastName(e.target.value)}
                      placeholder="Smith"
                      required
                      className="w-full rounded-lg border border-neutral-300 bg-neutral-50 px-4 py-2.5 text-sm outline-none focus:border-primary-600 focus:ring-2 focus:ring-primary-100"
                    />
                  </div>
                </div>
              )}

              <div>
                <label htmlFor="email" className="mb-1 block text-sm font-medium text-neutral-700">Email</label>
                <input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@example.com"
                  required
                  className="w-full rounded-lg border border-neutral-300 bg-neutral-50 px-4 py-2.5 text-sm outline-none focus:border-primary-600 focus:ring-2 focus:ring-primary-100"
                />
              </div>
              <div>
                <div className="mb-1 flex items-center justify-between">
                  <label htmlFor="password" className="text-sm font-medium text-neutral-700">Password</label>
                  {mode === "login" && (
                    <button
                      type="button"
                      onClick={handleForgotPassword}
                      disabled={loading}
                      className="cursor-pointer text-xs text-primary-600 hover:underline disabled:opacity-50"
                    >
                      {resetSent ? "Email sent ✓" : "Forgot password?"}
                    </button>
                  )}
                </div>
                <div className="relative">
                  <input
                    id="password"
                    type={showPassword ? "text" : "password"}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    required
                    className="w-full rounded-lg border border-neutral-300 bg-neutral-50 px-4 py-2.5 pr-10 text-sm outline-none focus:border-primary-600 focus:ring-2 focus:ring-primary-100"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword((v) => !v)}
                    className="cursor-pointer absolute right-3 top-1/2 -translate-y-1/2 text-[#9ca3af] hover:text-primary-700"
                    aria-label={showPassword ? "Hide password" : "Show password"}
                  >
                    <EyeIcon open={showPassword} />
                  </button>
                </div>
              </div>

              {mode === "signup" && (
                <label className="flex items-start gap-2 text-xs leading-5 text-neutral-600">
                  <input
                    type="checkbox"
                    checked={acceptedTerms}
                    onChange={(e) => setAcceptedTerms(e.target.checked)}
                    className="mt-1 h-4 w-4 rounded border-neutral-300 text-primary-600 focus:ring-primary-500"
                  />
                  <span>
                    I agree to the <a href="/terms" target="_blank" rel="noreferrer" className="text-primary-700 underline">Terms of Service</a>{" "}
                    and acknowledge the <a href="/privacy" target="_blank" rel="noreferrer" className="text-primary-700 underline">Privacy Policy</a>.
                  </span>
                </label>
              )}

              {error && (
                <p id={errorId} role="alert" className="rounded-lg bg-red-50 px-4 py-2.5 text-sm text-red-600">{error}</p>
              )}

              <button
                type="submit"
                disabled={loading}
                className="cursor-pointer w-full rounded-full bg-primary-600 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-primary-700 disabled:opacity-60"
              >
                {loading ? (mode === "login" ? "Logging in…" : "Creating account…") : action}
              </button>
            </form>

            <p className="mt-5 text-center text-sm text-neutral-500">
              {switchPrompt}{" "}
              <button onClick={handleSwitch} className="cursor-pointer font-medium text-primary-600 hover:underline">
                {mode === "login" ? "Sign up" : "Log in"}
              </button>
            </p>
          </>
        )}
      </div>
    </div>
  );
}
