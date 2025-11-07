import Image from "next/image";

export default function Home() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-zinc-50 font-sans dark:bg-black">
      <main className="flex min-h-screen w-full max-w-3xl flex-col items-center justify-between py-32 px-16 bg-white dark:bg-black sm:items-start">
        <Image
          className="dark:invert"
          src="/next.svg"
          alt="Next.js logo"
          width={100}
          height={20}
          priority
        />
        {/* Color test showcase: uses the custom Tailwind colors we added */}
        <section className="mt-8 w-full">
          <h2 className="mb-4 text-lg font-semibold text-black dark:text-zinc-50">
            Tailwind custom color test
          </h2>
          <div className="flex flex-wrap items-center gap-4">
            <div className="flex flex-col items-center gap-2">
              <div className="h-12 w-32 rounded-md bg-primary-500" style={{ backgroundColor: "#22c55e" }} />
              <span className="text-sm text-primary-700">primary-500</span>
            </div>

            <div className="flex flex-col items-center gap-2">
              <div className="h-12 w-32 rounded-md bg-accent-500" style={{ backgroundColor: "#facc15" }} />
              <span className="text-sm text-accent-700">accent-500</span>
            </div>

            <div className="flex flex-col items-center gap-2">
              <div className="h-12 w-32 rounded-md bg-neutral-700" style={{ backgroundColor: "#374151" }} />
              <span className="text-sm text-neutral-700">neutral-700</span>
            </div>

            <div className="flex flex-col items-center gap-2">
              <div className="h-12 w-32 rounded-md bg-background-light border border-neutral-200" style={{ backgroundColor: "#f7fdf9" }} />
              <span className="text-sm text-neutral-700">background-light</span>
            </div>

            <div className="flex flex-col items-center gap-2 dark:hidden">
              <div className="h-12 w-32 rounded-md bg-background-dark" style={{ backgroundColor: "#0f172a" }} />
              <span className="text-sm text-neutral-700">background-dark</span>
            </div>
          </div>

          <div className="mt-6 flex flex-col gap-2">
            <p className="text-base text-primary-600" style={{ color: "#16a34a" }}>This text uses text-primary-600</p>
            <p className="text-base text-accent-500" style={{ color: "#facc15" }}>This text uses text-accent-500</p>
            <p className="text-base text-neutral-500" style={{ color: "#6b7280" }}>This text uses text-neutral-500</p>
          </div>
        </section>
        <div className="flex flex-col items-center gap-6 text-center sm:items-start sm:text-left">
          <h1 className="max-w-xs text-3xl font-semibold leading-10 tracking-tight text-black dark:text-zinc-50">
            To get started, edit the page.tsx file.
          </h1>
          <p className="max-w-md text-lg leading-8 text-zinc-600 dark:text-zinc-400">
            Looking for a starting point or more instructions? Head over to{" "}
            <a
              href="https://vercel.com/templates?framework=next.js&utm_source=create-next-app&utm_medium=appdir-template-tw&utm_campaign=create-next-app"
              className="font-medium text-zinc-950 dark:text-zinc-50"
            >
              Templates
            </a>{" "}
            or the{" "}
            <a
              href="https://nextjs.org/learn?utm_source=create-next-app&utm_medium=appdir-template-tw&utm_campaign=create-next-app"
              className="font-medium text-zinc-950 dark:text-zinc-50"
            >
              Learning
            </a>{" "}
            center.
          </p>
        </div>
          <div className="flex flex-col gap-4 text-base font-medium sm:flex-row">
          <a
            className="flex h-12 w-full items-center justify-center gap-2 rounded-full bg-foreground px-5 text-background transition-colors hover:bg-[#383838] dark:hover:bg-[#ccc] md:w-[158px]"
            href="https://vercel.com/new?utm_source=create-next-app&utm_medium=appdir-template-tw&utm_campaign=create-next-app"
            target="_blank"
            rel="noopener noreferrer"
          >
            <Image
              className="dark:invert"
              src="/vercel.svg"
              alt="Vercel logomark"
              width={16}
              height={16}
            />
            Deploy Now
          </a>
          <a
            className="flex h-12 w-full items-center justify-center rounded-full border border-solid border-black/8 px-5 transition-colors hover:border-transparent hover:bg-black/4 dark:border-white/[.145] dark:hover:bg-[#1a1a1a] md:w-[158px]"
            href="https://nextjs.org/docs?utm_source=create-next-app&utm_medium=appdir-template-tw&utm_campaign=create-next-app"
            target="_blank"
            rel="noopener noreferrer"
          >
            Documentation
          </a>
        </div>
      </main>
    </div>
  );
}
