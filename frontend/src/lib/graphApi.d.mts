export class GraphApiError extends Error {
  status: number;
  retryAfter: string | null;
  constructor(message: string, status: number, retryAfter?: string | null);
}

export function getOrCreateGraphSessionId(
  userId: string,
  storage?: Pick<Storage, "getItem" | "setItem">,
  cryptoApi?: Pick<Crypto, "randomUUID">,
): string;

export function loadGraphSession(
  apiUrl: string | undefined,
  accessToken: string,
  sessionId: string,
  fetchImpl?: typeof fetch,
): Promise<{ session_id: string; state: Record<string, unknown> }>;

export function loadAccountGraphSession(
  apiUrl: string | undefined,
  accessToken: string,
  fetchImpl?: typeof fetch,
): Promise<{ session_id: string; state: Record<string, unknown> }>;

export function sendGraphMessage(
  apiUrl: string | undefined,
  accessToken: string,
  sessionId: string,
  userInput: string,
  fetchImpl?: typeof fetch,
): Promise<{ response: string; state: Record<string, unknown> }>;

export function initializeCareerTree(
  apiUrl: string | undefined,
  accessToken: string,
  sessionId: string,
  rootLabel: string,
  userInput: string | null,
  profileContext?: Record<string, unknown>,
  fetchImpl?: typeof fetch,
): Promise<{ tree: Record<string, unknown>; response: string }>;

export function expandCareerTree(
  apiUrl: string | undefined,
  accessToken: string,
  sessionId: string,
  nodeId: string,
  fetchImpl?: typeof fetch,
): Promise<{ tree: Record<string, unknown> }>;

export function saveCareerTreeView(
  apiUrl: string | undefined,
  accessToken: string,
  sessionId: string,
  selectedNodeId: string | null,
  expandedNodeIds: string[],
  fetchImpl?: typeof fetch,
): Promise<{ tree: Record<string, unknown> }>;

export function resetCareerTree(
  apiUrl: string | undefined,
  accessToken: string,
  sessionId: string,
  fetchImpl?: typeof fetch,
): Promise<{ status: string }>;

export function deleteCareerTreeNode(
  apiUrl: string | undefined,
  accessToken: string,
  sessionId: string,
  nodeId: string,
  fetchImpl?: typeof fetch,
): Promise<{ tree: Record<string, unknown> }>;

export type CareerChangeProposal = {
  id: string;
  interests: string[];
  context: string;
  refresh: { id: string; label: string }[];
};

export type CareerJob = {
  id: string;
  title: string;
  company: string | null;
  location: string | null;
  posted: string | null;
  url: string;
  remote: boolean | null;
  description: string;
  interest: string;
};

export function continueCareerChat(
  apiUrl: string, accessToken: string, sessionId: string, message: string, selectedNodeId: string | null,
  fetchImpl?: typeof fetch,
): Promise<{ response: string; state: Record<string, unknown> & { pending_career_changes?: CareerChangeProposal } }>;

export function explainCareerNode(
  apiUrl: string, accessToken: string, sessionId: string, nodeId: string,
  fetchImpl?: typeof fetch,
): Promise<{ response: string; state: Record<string, unknown> & { pending_career_changes?: CareerChangeProposal } }>;

export function applyCareerChanges(
  apiUrl: string, accessToken: string, sessionId: string, proposalId: string, accept: boolean,
  fetchImpl?: typeof fetch,
): Promise<{ state: Record<string, unknown> & { pending_career_changes?: CareerChangeProposal } }>;

export function findCareerJobs(
  apiUrl: string, accessToken: string, sessionId: string, nodeId: string,
  filters: { country: "US"; location: string; workplace: "remote" | "local" }, fetchImpl?: typeof fetch,
): Promise<{ jobs: CareerJob[]; source: string }>;