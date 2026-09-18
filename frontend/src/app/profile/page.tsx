"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { AuthProvider, useAuth } from "@/context/AuthContext";
import { supabase } from "@/lib/supabase";
import Navbar from "@/components/Navbar";

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function ProfileContent() {
  const { user, session, signOut, loading } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    if (!loading && !user) router.replace("/");
    if (user) setEmail(user.email ?? "");
  }, [loading, user, router]);

  function clearMessages() {
    setStatusMessage(null);
    setErrorMessage(null);
  }

  async function updateEmail() {
    clearMessages();
    if (!email.trim() || email.trim() === user?.email) {
      setErrorMessage("Enter a new email address first.");
      return;
    }
    setSaving(true);
    const { error } = await supabase.auth.updateUser({ email: email.trim() });
    setSaving(false);
    if (error) setErrorMessage(error.message);
    else setStatusMessage("Check your email to confirm the new address.");
  }

  async function updatePassword() {
    clearMessages();
    if (password.length < 8) {
      setErrorMessage("Your new password must be at least 8 characters.");
      return;
    }
    setSaving(true);
    const { error } = await supabase.auth.updateUser({ password });
    setSaving(false);
    if (error) setErrorMessage(error.message);
    else {
      setPassword("");
      setStatusMessage("Your password has been updated.");
    }
  }

  async function deleteAccount() {
    clearMessages();
    if (!window.confirm("Delete your account and all saved career graph data? This cannot be undone.")) return;
    if (!session?.access_token) {
      setErrorMessage("Your session has expired. Please sign in again.");
      return;
    }
    setDeleting(true);
    try {
      const response = await fetch(`${apiUrl}/account`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${session.access_token}` },
      });
      if (!response.ok) {
        const body = await response.json().catch(() => null);
        throw new Error(body?.detail ?? "Unable to delete account.");
      }
      await signOut();
      router.replace("/");
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Unable to delete account.");
      setDeleting(false);
    }
  }

  if (loading || !user) return null;

  return (
    <div className="min-h-screen bg-background-light">
      <Navbar user={user} onLogin={() => {}} onSignup={() => {}} onSignOut={async () => { await signOut(); router.replace("/"); }} />
      <main className="mx-auto max-w-3xl px-6 py-12">
        <header className="mb-8 flex flex-col gap-5 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-primary-600">Your account</p>
            <h1 className="mt-2 text-3xl font-bold tracking-tight text-primary-950">Account settings</h1>
            <p className="mt-2 text-sm text-neutral-500">Manage your login details and account data.</p>
          </div>
          <Link
            href="/graph"
            className="inline-flex items-center gap-2 self-start rounded-lg border border-primary-200 bg-white px-4 py-2.5 text-sm font-semibold text-primary-700 shadow-sm transition hover:bg-primary-50 sm:self-auto"
          >
            <span aria-hidden="true">←</span>
            Back to graph
          </Link>
        </header>

        {(statusMessage || errorMessage) && (
          <div role="status" className={`mb-6 rounded-xl px-4 py-3 text-sm ${errorMessage ? "bg-red-50 text-red-700" : "bg-primary-50 text-primary-800"}`}>
            {errorMessage ?? statusMessage}
          </div>
        )}

        <div className="space-y-6">
          <section className="rounded-2xl border border-primary-100 bg-white p-6 shadow-sm">
            <h2 className="text-lg font-semibold text-primary-950">Email address</h2>
            <p className="mt-1 text-sm text-neutral-500">Changing your email requires confirmation at the new address.</p>
            <div className="mt-5 flex flex-col gap-3 sm:flex-row">
              <input aria-label="Email address" type="email" value={email} onChange={(e) => setEmail(e.target.value)} className="min-w-0 flex-1 rounded-lg border border-neutral-300 bg-neutral-50 px-4 py-2.5 text-sm outline-none focus:border-primary-600 focus:ring-2 focus:ring-primary-100" />
              <button onClick={updateEmail} disabled={saving} className="rounded-lg bg-primary-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-primary-700 disabled:opacity-60">Update email</button>
            </div>
          </section>

          <section className="rounded-2xl border border-primary-100 bg-white p-6 shadow-sm">
            <h2 className="text-lg font-semibold text-primary-950">Password</h2>
            <p className="mt-1 text-sm text-neutral-500">Use at least 8 characters and avoid reusing an old password.</p>
            <div className="mt-5 flex flex-col gap-3 sm:flex-row">
              <input aria-label="New password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="New password" className="min-w-0 flex-1 rounded-lg border border-neutral-300 bg-neutral-50 px-4 py-2.5 text-sm outline-none focus:border-primary-600 focus:ring-2 focus:ring-primary-100" />
              <button onClick={updatePassword} disabled={saving} className="rounded-lg bg-primary-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-primary-700 disabled:opacity-60">Update password</button>
            </div>
          </section>

          <section className="rounded-2xl border border-red-200 bg-red-50/60 p-6">
            <h2 className="text-lg font-semibold text-red-900">Delete account</h2>
            <p className="mt-1 text-sm leading-6 text-red-800">This permanently removes your account and saved career graph data.</p>
            <button onClick={deleteAccount} disabled={deleting} className="mt-5 rounded-lg border border-red-300 px-4 py-2.5 text-sm font-semibold text-red-700 transition hover:bg-red-100 disabled:opacity-60">{deleting ? "Deleting account..." : "Delete my account"}</button>
          </section>
        </div>
      </main>
    </div>
  );
}

export default function ProfilePage() {
  return (
    <AuthProvider>
      <ProfileContent />
    </AuthProvider>
  );
}