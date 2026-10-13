export class GraphApiError extends Error {
  constructor(message, status, retryAfter = null) {
    super(message);
    this.name = "GraphApiError";
    this.status = status;
    this.retryAfter = retryAfter;
  }
}

export function getOrCreateGraphSessionId(userId, storage = globalThis.localStorage, cryptoApi = globalThis.crypto) {
  const key = `branchingoutai:graph-session:${userId}`;
  const savedSessionId = storage.getItem(key);
  if (savedSessionId) return savedSessionId;

  const sessionId = cryptoApi.randomUUID();
  storage.setItem(key, sessionId);
  return sessionId;
}

async function requestJson(apiUrl, accessToken, path, options = {}, fetchImpl = globalThis.fetch) {
  const baseUrl = apiUrl?.replace(/\/+$/, "");
  if (!baseUrl) throw new Error("The backend API URL is not configured.");

  const response = await fetchImpl(`${baseUrl}${path}`, {
    ...options,
    headers: {
      Authorization: `Bearer ${accessToken}`,
      ...(options.body ? { "Content-Type": "application/json" } : {}),
      ...options.headers,
    },
  });

  if (response.ok) return response.json();

  const body = await response.json().catch(() => null);
  if (response.status === 401) {
    throw new GraphApiError("Your sign-in session has expired. Please sign in again.", 401);
  }
  if (response.status === 429) {
    const retryAfter = response.headers.get("Retry-After");
    const retryMessage = retryAfter && /^\d+$/.test(retryAfter)
      ? `Try again in ${retryAfter} seconds.`
      : retryAfter
        ? `Retry after ${retryAfter}.`
        : "Please try again shortly.";
    throw new GraphApiError(`The service is receiving too many requests. ${retryMessage}`, 429, retryAfter);
  }

  throw new GraphApiError(body?.detail || `The request failed (${response.status}).`, response.status);
}

export function loadAccountGraphSession(apiUrl, accessToken, fetchImpl) {
  return requestJson(apiUrl, accessToken, "/career-tree/session", {}, fetchImpl);
}

export function initializeCareerTree(apiUrl, accessToken, sessionId, rootLabel, userInput, profileContext = {}, fetchImpl) {
  return requestJson(apiUrl, accessToken, "/career-tree/initialize", {
    method: "POST",
    body: JSON.stringify({ session_id: sessionId, root_label: rootLabel, user_input: userInput, profile_context: profileContext }),
  }, fetchImpl);
}

export function expandCareerTree(apiUrl, accessToken, sessionId, nodeId, fetchImpl) {
  return requestJson(apiUrl, accessToken, "/career-tree/expand", {
    method: "POST",
    body: JSON.stringify({ session_id: sessionId, node_id: nodeId }),
  }, fetchImpl);
}

export function saveCareerTreeView(apiUrl, accessToken, sessionId, selectedNodeId, expandedNodeIds, fetchImpl) {
  return requestJson(apiUrl, accessToken, "/career-tree/state", {
    method: "PUT",
    body: JSON.stringify({
      session_id: sessionId,
      selected_node_id: selectedNodeId,
      expanded_node_ids: expandedNodeIds,
    }),
  }, fetchImpl);
}

export function resetCareerTree(apiUrl, accessToken, sessionId, fetchImpl) {
  return requestJson(apiUrl, accessToken, "/career-tree/reset", {
    method: "POST",
    body: JSON.stringify({ session_id: sessionId }),
  }, fetchImpl);
}

export function deleteCareerTreeNode(apiUrl, accessToken, sessionId, nodeId, fetchImpl) {
  return requestJson(apiUrl, accessToken, "/career-tree/delete", {
    method: "POST",
    body: JSON.stringify({ session_id: sessionId, node_id: nodeId }),
  }, fetchImpl);
}

export function continueCareerChat(apiUrl, accessToken, sessionId, message, selectedNodeId, fetchImpl) {
  return requestJson(apiUrl, accessToken, "/career-tree/message", {
    method: "POST",
    body: JSON.stringify({ session_id: sessionId, message, selected_node_id: selectedNodeId }),
  }, fetchImpl);
}

export function explainCareerNode(apiUrl, accessToken, sessionId, nodeId, fetchImpl) {
  return requestJson(apiUrl, accessToken, "/career-tree/explain", {
    method: "POST",
    body: JSON.stringify({ session_id: sessionId, node_id: nodeId }),
  }, fetchImpl);
}

export function applyCareerChanges(apiUrl, accessToken, sessionId, proposalId, accept, fetchImpl) {
  return requestJson(apiUrl, accessToken, "/career-tree/changes", {
    method: "POST",
    body: JSON.stringify({ session_id: sessionId, proposal_id: proposalId, accept }),
  }, fetchImpl);
}

export function findCareerJobs(apiUrl, accessToken, sessionId, nodeId, filters, fetchImpl) {
  return requestJson(apiUrl, accessToken, "/career-tree/jobs", {
    method: "POST",
    body: JSON.stringify({ session_id: sessionId, node_id: nodeId, ...filters }),
  }, fetchImpl);
}