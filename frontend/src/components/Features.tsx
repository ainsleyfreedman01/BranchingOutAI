"use client";

import React from "react";

// Simple SVG icons — one per feature
const icons: Record<string, React.ReactNode> = {
  grow: (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="#16a34a" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
      <path d="M10 17V7" />
      <path d="M6 11c0-2.5 4-6 4-6s4 3.5 4 6a4 4 0 0 1-8 0Z" />
    </svg>
  ),
  compass: (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="#16a34a" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="10" cy="10" r="8" />
      <path d="m13 7-1.5 4.5L7 13l1.5-4.5L13 7Z" />
    </svg>
  ),
  target: (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="#16a34a" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="10" cy="10" r="8" />
      <circle cx="10" cy="10" r="4" />
      <circle cx="10" cy="10" r="1" fill="#16a34a" />
    </svg>
  ),
  star: (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="#16a34a" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
      <path d="M10 2l2.4 5h5.1l-4.1 3 1.5 5L10 12l-4.9 3 1.5-5L2.5 7h5.1L10 2Z" />
    </svg>
  ),
  lock: (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="#16a34a" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
      <rect x="4" y="9" width="12" height="9" rx="2" />
      <path d="M7 9V6a3 3 0 0 1 6 0v3" />
    </svg>
  ),
  people: (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="#16a34a" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="7" cy="7" r="3" />
      <path d="M1 17c0-3 2.7-5 6-5" />
      <circle cx="14" cy="7" r="3" />
      <path d="M19 17c0-3-2.7-5-6-5" />
    </svg>
  ),
};

const features = [
  { iconKey: "grow",    title: "Grow from where you are",   desc: "Tell us your current role and skills. We map your starting point and show realistic next branches." },
  { iconKey: "compass", title: "Industry-aware paths",       desc: "Our AI reads live industry trends so your tree reflects what employers actually want right now." },
  { iconKey: "target",  title: "Skill-first suggestions",    desc: "Every branch comes with concrete skills to build, courses to take, and projects to try." },
  { iconKey: "star",    title: "Interests at the centre",    desc: "Not just titles — we factor in what you enjoy doing so your career stays energising." },
  { iconKey: "lock",    title: "Private by default",         desc: "Your data belongs to you. We never sell it, and you can export or delete it any time." },
  { iconKey: "people",  title: "Human + AI together",        desc: "AI surfaces options you might miss; you stay in control of every decision along the way." },
];

export default function Features() {
  return (
    <section id="features" className="bg-[#f0fff4] py-20">
      <div className="mx-auto max-w-6xl px-6">
        <div className="mb-12 text-center">
          <span className="inline-block rounded-full bg-[#dcfce7] px-3 py-1 text-xs font-semibold uppercase tracking-widest text-[#15803d]">
            How it works
          </span>
          <h2 className="mt-3 text-3xl font-bold text-[#14532d]">
            Everything you need to branch out
          </h2>
          <p className="mt-3 text-base text-[#4b5563]">
            Career growth shouldn&apos;t feel like a maze. We make it feel like a walk through the woods.
          </p>
        </div>

        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {features.map((f) => (
            <div
              key={f.title}
              className="rounded-2xl border border-[#bbf7d0] bg-white p-6 shadow-sm transition hover:shadow-md"
            >
              <div className="mb-3 flex h-8 w-8 items-center justify-center rounded-lg bg-[#dcfce7]">
                {icons[f.iconKey]}
              </div>
              <h3 className="font-semibold text-[#14532d]">{f.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-[#4b5563]">{f.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
