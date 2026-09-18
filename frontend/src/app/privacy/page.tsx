import Link from "next/link";

export default function PrivacyPage() {
  return (
    <main className="min-h-screen bg-background-light px-6 py-12 text-neutral-800">
      <article className="mx-auto max-w-3xl rounded-2xl border border-primary-100 bg-white p-8 shadow-sm sm:p-12">
        <Link href="/" className="inline-flex items-center gap-2 text-sm font-medium text-primary-700 transition hover:text-primary-900 hover:underline">
          <span aria-hidden="true">←</span> Back to BranchingOutAI
        </Link>
        <header className="mt-10 border-b border-primary-100 pb-8">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-primary-600">Your information</p>
          <h1 className="mt-3 text-4xl font-bold tracking-tight text-primary-950">Privacy Policy</h1>
          <p className="mt-3 text-sm text-neutral-500">Last updated: September 18, 2026</p>
        </header>

        <section className="mt-8">
          <p className="rounded-xl bg-primary-50 px-5 py-4 text-[15px] leading-7 text-primary-950">
            We built BranchingOutAI to help you explore possibilities without losing sight of the person behind the data. This policy explains what we collect, why we use it, and the choices available to you.
          </p>
          <div className="mt-10 space-y-9 text-[15px] leading-7 text-neutral-600">
            <section><h2 className="text-xl font-semibold text-primary-950">Information we collect</h2><p className="mt-2">When you create an account, we collect your email address, password credential handled by Supabase, and the name you provide. When you use BranchingOutAI, we collect your career interests, skills, industry and job inputs, generated career-path state, and basic technical information needed to keep the service secure.</p></section>
            <section><h2 className="text-xl font-semibold text-primary-950">How we use information</h2><p className="mt-2">We use this information to authenticate you, save and display your career graph, generate suggestions, maintain the service, prevent abuse, and communicate about account or security matters. We do not sell your personal information.</p></section>
            <section><h2 className="text-xl font-semibold text-primary-950">Service providers</h2><p className="mt-2">We use infrastructure providers, including Supabase for authentication and storage and OpenAI for AI-generated suggestions. Information sent to those providers is used to provide the requested functionality and is subject to their terms and privacy practices.</p></section>
            <section><h2 className="text-xl font-semibold text-primary-950">Retention and deletion</h2><p className="mt-2">We retain account and career-graph information while your account is active or as needed to provide the service, meet legal obligations, resolve disputes, and enforce agreements. Contact us through the account support channel to request access, correction, or deletion. Replace this placeholder with the production support address before launch.</p></section>
            <section><h2 className="text-xl font-semibold text-primary-950">Your choices</h2><p className="mt-2">You may stop using the service, request deletion of your account data, or contact us with privacy questions. Some information may be retained where required by law or for legitimate security purposes.</p></section>
            <section><h2 className="text-xl font-semibold text-primary-950">Changes</h2><p className="mt-2">We may update this policy as the service changes. We will post the revised version here and update the date above.</p></section>
          </div>
        </section>
      </article>
    </main>
  );
}