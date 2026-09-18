"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { AuthProvider, useAuth } from "@/context/AuthContext";
import { supabase } from "@/lib/supabase";

function ResetPasswordContent() {
  const { session, loading } = useAuth();
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);

  // Supabase exchanges the recovery link's token for a session on page load;
  // give it a moment before deciding the link is invalid/expired.
  const [checkingLink, setCheckingLink] = useState(true);
  useEffect(() => {
    const timer = setTimeout(() => setCheckingLink(false), 1500);
    return () => clearTimeout(timer);
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (password.length < 8) {
      setError("Your new password must be at least 8 characters.");
      return;
    }
    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }
    setSubmitting(true);
    const { error: updateError } = await supabase.auth.updateUser({ password });
    setSubmitting(false);
    if (updateError) {
      setError(updateError.message);
      return;
    }
    setSuccess(true);
  }

  const linkInvalid = !loading && !checkingLink && !session;

  return (
    <div className="flex min-h-screen items-center justify-center bg-background-light px-4">
      <div className="w-full max-w-md rounded-2xl border border-primary-200 bg-white p-8 shadow-xl">
        <h1 className="text-xl font-bold text-primary-900">Reset your password</h1>

        {success ? (
          <>
            <p className="mt-3 text-sm text-neutral-500">
              Your password has been updated. You can now log in with your new password.
            </p>
            <Link
              href="/"
              className="mt-6 inline-flex w-full items-center justify-center rounded-full bg-primary-600 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-primary-700"
            >
              Return to sign in
            </Link>
          </>
        ) : loading || checkingLink ? (
          <p className="mt-3 text-sm text-neutral-500">Verifying your reset link…</p>
        ) : linkInvalid ? (
          <>
            <p className="mt-3 text-sm text-neutral-500">
              This password reset link is invalid or has expired. Please request a new one.
            </p>
            <Link
              href="/"
              className="mt-6 inline-flex w-full items-center justify-center rounded-full bg-primary-600 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-primary-700"
            >
              Back to home
            </Link>
          </>
        ) : (
          <>
            <p className="mt-1 text-sm text-neutral-500">Choose a new password for your account.</p>
            <form className="mt-6 space-y-4" onSubmit={handleSubmit}>
              <div>
                <label htmlFor="new-password" className="mb-1 block text-sm font-medium text-neutral-700">
                  New password
                </label>
                <input
                  id="new-password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  required
                  className="w-full rounded-lg border border-neutral-300 bg-neutral-50 px-4 py-2.5 text-sm outline-none focus:border-primary-600 focus:ring-2 focus:ring-primary-100"
                />
              </div>
              <div>
                <label htmlFor="confirm-password" className="mb-1 block text-sm font-medium text-neutral-700">
                  Confirm new password
                </label>
                <input
                  id="confirm-password"
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="••••••••"
                  required
                  className="w-full rounded-lg border border-neutral-300 bg-neutral-50 px-4 py-2.5 text-sm outline-none focus:border-primary-600 focus:ring-2 focus:ring-primary-100"
                />
              </div>

              {error && (
                <p role="alert" className="rounded-lg bg-red-50 px-4 py-2.5 text-sm text-red-600">
                  {error}
                </p>
              )}

              <button
                type="submit"
                disabled={submitting}
                className="w-full rounded-full bg-primary-600 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-primary-700 disabled:opacity-60"
              >
                {submitting ? "Updating…" : "Update password"}
              </button>
            </form>
          </>
        )}
      </div>
    </div>
  );
}

export default function ResetPasswordPage() {
  return (
    <AuthProvider>
      <ResetPasswordContent />
    </AuthProvider>
  );
}
