import Link from "next/link";

export default function TermsPage() {
  return (
    <main className="min-h-screen bg-background-light px-6 py-12 text-neutral-800">
      <article className="mx-auto max-w-3xl rounded-2xl border border-primary-100 bg-white p-8 shadow-sm sm:p-12">
        <Link href="/" className="inline-flex items-center gap-2 text-sm font-medium text-primary-700 transition hover:text-primary-900 hover:underline">
          <span aria-hidden="true">←</span> Back to BranchingOutAI
        </Link>
        <header className="mt-10 border-b border-primary-100 pb-8">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-primary-600">Using the service</p>
          <h1 className="mt-3 text-4xl font-bold tracking-tight text-primary-950">Terms of Service</h1>
          <p className="mt-3 text-sm text-neutral-500">Last updated: September 18, 2026</p>
        </header>

        <section className="mt-8">
          <p className="rounded-xl bg-primary-50 px-5 py-4 text-[15px] leading-7 text-primary-950">
            These terms keep the experience useful, respectful, and clear about what BranchingOutAI can and cannot promise.
          </p>
          <div className="mt-10 space-y-9 text-[15px] leading-7 text-neutral-600">
            <section><h2 className="text-xl font-semibold text-primary-950">Using BranchingOutAI</h2><p className="mt-2">You may use BranchingOutAI only for lawful purposes and only with information you have the right to provide. Keep your account credentials secure and notify us if you believe your account has been misused.</p></section>
            <section><h2 className="text-xl font-semibold text-primary-950">AI-generated information</h2><p className="mt-2">Career paths, recommendations, and other outputs are generated for general informational purposes. They are not professional, financial, legal, educational, or employment advice, and we do not guarantee that an opportunity, role, or recommendation is accurate, current, or suitable for you.</p></section>
            <section><h2 className="text-xl font-semibold text-primary-950">Prohibited conduct</h2><p className="mt-2">You must not probe, disrupt, overload, scrape, reverse engineer, abuse, or attempt unauthorized access to the service or another user&apos;s data. Automated requests must respect our rate limits and must not be used to bypass authentication or usage controls.</p></section>
            <section><h2 className="text-xl font-semibold text-primary-950">Your content</h2><p className="mt-2">You retain responsibility for the information you submit. You grant us permission to process it only as needed to operate, secure, and improve the service as described in the Privacy Policy.</p></section>
            <section><h2 className="text-xl font-semibold text-primary-950">Availability and changes</h2><p className="mt-2">The service is provided on an evolving basis and may change, become unavailable, or contain errors. We may suspend access when needed to protect users, providers, or the service.</p></section>
            <section><h2 className="text-xl font-semibold text-primary-950">Contact and governing terms</h2><p className="mt-2">Replace this placeholder with the legal entity, support contact, governing law, dispute process, and any required consumer notices before public launch. These terms should be reviewed by qualified legal counsel for the jurisdictions where you operate.</p></section>
          </div>
        </section>
      </article>
    </main>
  );
}