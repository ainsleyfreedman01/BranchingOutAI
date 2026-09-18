"use client";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Navbar from "@/components/Navbar";
import Hero from "@/components/Hero";
import Features from "@/components/Features";
import CTA from "@/components/CTA";
import Footer from "@/components/Footer";
import AuthModal from "@/components/AuthModal";
import { AuthProvider, useAuth } from "@/context/AuthContext";

function PageContent() {
  const { user, signOut } = useAuth();
  const router = useRouter();
  const [authOpen, setAuthOpen] = useState(false);
  const [authMode, setAuthMode] = useState<"login" | "signup">("signup");

  useEffect(() => {
    if (user) {
      router.replace("/graph");
    }
  }, [user, router]);

  function openLogin() {
    setAuthMode("login");
    setAuthOpen(true);
  }

  function openSignup() {
    setAuthMode("signup");
    setAuthOpen(true);
  }

  return (
    <>
      <Navbar
        user={user}
        onLogin={openLogin}
        onSignup={openSignup}
        onSignOut={signOut}
      />
      <main>
        {user ? (
          <div className="min-h-[60vh] flex items-center justify-center">
            <div className="max-w-3xl mx-auto px-6 py-12 text-center">
              <h1 className="text-3xl font-bold text-primary-900">{`Hi${(user.user_metadata?.first_name as string | undefined) ? `, ${(user.user_metadata?.first_name as string)}!` : "!"}`}</h1>
              <p className="mt-3 text-sm text-neutral-500">Pick up where you left off — view your Career Graph or update your profile.</p>
              <div className="mt-6 flex items-center justify-center gap-3">
                <button
                  onClick={() => router.push("/graph")}
                  className="inline-flex items-center gap-2 rounded-md bg-primary-600 px-4 py-2 text-white transition hover:bg-primary-700"
                >
                  Go to my graph →
                </button>
                <button
                  onClick={() => router.push("/profile")}
                  className="inline-flex items-center gap-2 rounded-md border border-primary-100 bg-white px-4 py-2 text-sm text-primary-900 hover:bg-primary-50"
                >
                  Profile
                </button>
              </div>
              {/* Wide-screen filler content for signed-in users */}
              <div className="mt-10">
                <div className="max-w-6xl mx-auto px-4">
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    <div className="rounded-lg border border-primary-100 bg-white p-5 shadow-sm">
                      <h3 className="text-lg font-semibold text-primary-900">Recent nodes</h3>
                      <p className="mt-2 text-sm text-neutral-500">No recent activity yet — your created nodes will appear here.</p>
                      <div className="mt-4">
                        <button onClick={() => router.push('/graph')} className="text-sm text-primary-900 underline">Open graph</button>
                      </div>
                    </div>

                    <div className="rounded-lg border border-primary-100 bg-white p-5 shadow-sm">
                      <h3 className="text-lg font-semibold text-primary-900">Saved paths</h3>
                      <p className="mt-2 text-sm text-neutral-500">Save interesting career paths here for later reference.</p>
                      <div className="mt-4">
                        <button onClick={() => router.push('/graph')} className="text-sm text-primary-900 underline">View paths</button>
                      </div>
                    </div>

                    <div className="rounded-lg border border-primary-100 bg-white p-5 shadow-sm">
                      <h3 className="text-lg font-semibold text-primary-900">Suggestions</h3>
                      <p className="mt-2 text-sm text-neutral-500">AI suggestions and next steps will appear here as you interact with the graph.</p>
                      <div className="mt-4">
                        <button onClick={() => router.push('/graph')} className="text-sm text-primary-900 underline">Explore suggestions</button>
                      </div>
                    </div>
                  </div>
                </div>
                <div className="mt-8">
                  <div className="max-w-6xl mx-auto px-4">
                    <div className="rounded-lg border border-primary-100 bg-primary-50 p-6 text-center">
                      <p className="text-sm text-primary-900">Tip: drag the canvas or use the zoom controls in the bottom-right to explore.</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        ) : (
          <>
            <Hero onPrimary={openSignup} />
            <Features />
            <CTA user={user} onCTAClick={openSignup} />
          </>
        )}
      </main>
      <Footer />
      <AuthModal
        mode={authMode}
        open={authOpen}
        onClose={() => setAuthOpen(false)}
        onSwitch={() => setAuthMode((m) => (m === "login" ? "signup" : "login"))}
      />
    </>
  );
}

export default function Home() {
  return (
    <AuthProvider>
      <PageContent />
    </AuthProvider>
  );
}
