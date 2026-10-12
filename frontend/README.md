# BranchingOutAI frontend

The frontend is a Next.js app using React and TypeScript. It provides the landing page, Supabase sign-in and account settings, and the interactive career graph. The graph page calls the FastAPI backend for saved graph data, branch suggestions, career guidance, explanations, and live job searches.

## Run locally

From this directory:

```bash
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). For the graph and account features, also run the backend as described in the repository-root `README.md`.

Set these frontend environment variables in a local `.env.local` file:

- `NEXT_PUBLIC_SUPABASE_URL` — Supabase project URL.
- `NEXT_PUBLIC_SUPABASE_ANON_KEY` — public Supabase anon key used by Supabase Auth.
- `NEXT_PUBLIC_API_URL` — backend base URL, such as `http://localhost:8000`.

Only public client configuration belongs in `NEXT_PUBLIC_*` variables. Never put Supabase service-role credentials or external provider API keys in the frontend.

## Useful locations

- `src/app/` — Next.js routes: home, graph, profile, password reset, privacy, and terms.
- `src/components/` — shared interface components.
- `src/context/AuthContext.tsx` — current Supabase user and session state.
- `src/lib/graphApi.mjs` — authenticated calls to the backend career-tree API.
- `src/lib/branchTree.mjs`, `radialTreeLayout.mjs`, and `graphAnimation.mjs` — graph display and layout helpers.
- `src/lib/*.test.mjs` — Node tests for frontend helper modules.

## Checks

```bash
npm test
npm run lint
npm run build
```
