"use client";

import { useState } from "react";
import Navbar from "@/components/Navbar";
import Hero from "@/components/Hero";
import Features from "@/components/Features";
import CTA from "@/components/CTA";
import Footer from "@/components/Footer";
import AuthModal from "@/components/AuthModal";

export default function Home() {
  const [authOpen, setAuthOpen] = useState(false);
  const [authMode, setAuthMode] = useState<"login" | "signup">("signup");

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
      <Navbar onLogin={openLogin} onSignup={openSignup} />
      <main>
        <Hero onPrimary={openSignup} />
        <Features />
        <CTA onCTAClick={openSignup} />
      </main>
      <Footer />
      <AuthModal mode={authMode} open={authOpen} onClose={() => setAuthOpen(false)} onSwitch={() => setAuthMode((m) => m === "login" ? "signup" : "login")} />
    </>
  );
}
