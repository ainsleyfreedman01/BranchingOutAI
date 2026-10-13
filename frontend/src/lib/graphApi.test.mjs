import assert from "node:assert/strict";
import test from "node:test";
import {
  deleteCareerTreeNode,
  getOrCreateGraphSessionId,
  GraphApiError,
  expandCareerTree,
  initializeCareerTree,
  loadAccountGraphSession,
  resetCareerTree,
  saveCareerTreeView,
  continueCareerChat,
  applyCareerChanges,
  findCareerJobs,
  explainCareerNode,
} from "./graphApi.mjs";

test("ongoing guidance, confirmed changes, and jobs use authenticated graph endpoints", async () => {
  const calls = [];
  const fetchImpl = async (url, options) => {
    calls.push({ url, options });
    return response(200, { state: {}, jobs: [] });
  };
  await continueCareerChat("http://localhost:8000", "access-token", "session", "Add music", "interest:data", fetchImpl);
  await applyCareerChanges("http://localhost:8000", "access-token", "session", "proposal", false, fetchImpl);
  await findCareerJobs("http://localhost:8000", "access-token", "session", "role", { country: "US", location: "Boston", workplace: "remote" }, fetchImpl);
  assert.deepEqual(calls.map(({ url }) => url.split("/").at(-1)), ["message", "changes", "jobs"]);
  assert.deepEqual(JSON.parse(calls[0].options.body), { session_id: "session", message: "Add music", selected_node_id: "interest:data" });
  assert.deepEqual(JSON.parse(calls[1].options.body), { session_id: "session", proposal_id: "proposal", accept: false });
  assert.deepEqual(JSON.parse(calls[2].options.body), { session_id: "session", node_id: "role", country: "US", location: "Boston", workplace: "remote" });
  for (const { options } of calls) {
    assert.equal(options.method, "POST");
    assert.equal(options.headers.Authorization, `Bearer ${"access-token"}`);
    assert.equal(JSON.stringify(options).includes("THEIRSTACK_API_KEY"), false);
  }
});

function response(status, payload, headers = {}) {
  return {
    ok: status >= 200 && status < 300,
    status,
    headers: new Headers(headers),
    json: async () => payload,
  };
}

test("node explanations send the selected ID with authentication and preserve the response", async () => {
  const result = { response: "Overview\nTypical work", state: { chat_history: [] } };
  const fetched = await explainCareerNode("http://localhost:8000/", "access-token", "session", "interest:music", async (url, options) => {
    assert.equal(url, "http://localhost:8000/career-tree/explain");
    assert.equal(options.method, "POST");
    assert.equal(options.headers.Authorization, `Bearer ${"access-token"}`);
    assert.deepEqual(JSON.parse(options.body), { session_id: "session", node_id: "interest:music" });
    return response(200, result);
  });
  assert.deepEqual(fetched, result);
});

test("account graph loads without a browser-local session ID", async () => {
  const calls = [];
  const fetchImpl = async (url, options) => {
    calls.push({ url, options });
    return response(200, { session_id: "career-graph:user-a", state: { interests: ["AI"] } });
  };
  const firstBrowser = await loadAccountGraphSession("http://localhost:8000/", "token-a", fetchImpl);
  const secondBrowser = await loadAccountGraphSession("http://localhost:8000", "token-a", fetchImpl);
  assert.deepEqual(firstBrowser, secondBrowser);
  assert.equal(calls[0].url, "http://localhost:8000/career-tree/session");
  assert.equal(calls[0].options.headers.Authorization, "Bearer token-a");
  assert.equal(calls[0].options.body, undefined);
});

test("session IDs persist for one user and are isolated between users", () => {
  const values = new Map();
  const storage = {
    getItem: (key) => values.get(key) ?? null,
    setItem: (key, value) => values.set(key, value),
  };
  let nextId = 0;
  const cryptoApi = { randomUUID: () => `session-${++nextId}` };

  const firstUserSession = getOrCreateGraphSessionId("user-a", storage, cryptoApi);
  assert.equal(getOrCreateGraphSessionId("user-a", storage, cryptoApi), firstUserSession);
  assert.notEqual(getOrCreateGraphSessionId("user-b", storage, cryptoApi), firstUserSession);
  assert.equal(nextId, 2);
});

test("session load and chat requests send the bearer token and expected payload", async () => {
  const calls = [];
  const fetchImpl = async (url, options) => {
    calls.push({ url, options });
    return response(200, calls.length === 1
      ? { session_id: "session-1", state: { interests: ["design"] } }
      : { response: "Which industry interests you?", state: { user_input: "design" } });
  };

  await loadAccountGraphSession("http://localhost:8000/", "access-token", fetchImpl);
  await continueCareerChat("http://localhost:8000", "access-token", "session-1", "design", null, fetchImpl);

  assert.equal(calls[0].url, "http://localhost:8000/career-tree/session");
  assert.equal(calls[0].options.headers.Authorization, "Bearer access-token");
  assert.equal(calls[1].url, "http://localhost:8000/career-tree/message");
  assert.equal(calls[1].options.headers.Authorization, "Bearer access-token");
  assert.equal(calls[1].options.headers["Content-Type"], "application/json");
  assert.deepEqual(JSON.parse(calls[1].options.body), {
    session_id: "session-1",
    message: "design",
    selected_node_id: null,
  });
});

test("career tree requests initialize, expand, and persist view state", async () => {
  const calls = [];
  const fetchImpl = async (url, options) => {
    calls.push({ url, options });
    return response(200, { tree: {} });
  };

  await initializeCareerTree("http://localhost:8000", "access-token", "session-1", "Avery", "I enjoy data", { interests: ["data"] }, fetchImpl);
  await expandCareerTree("http://localhost:8000", "access-token", "session-1", "interest:data", fetchImpl);
  await saveCareerTreeView("http://localhost:8000", "access-token", "session-1", "interest:data", ["you", "interest:data"], fetchImpl);
  await resetCareerTree("http://localhost:8000", "access-token", "session-1", fetchImpl);

  assert.deepEqual(calls.map(({ url }) => url), [
    "http://localhost:8000/career-tree/initialize",
    "http://localhost:8000/career-tree/expand",
    "http://localhost:8000/career-tree/state",
    "http://localhost:8000/career-tree/reset",
  ]);
  assert.equal(calls[0].options.headers.Authorization, "Bearer access-token");
  assert.deepEqual(JSON.parse(calls[0].options.body), {
    session_id: "session-1",
    root_label: "Avery",
    user_input: "I enjoy data",
    profile_context: { interests: ["data"] },
  });
  assert.deepEqual(JSON.parse(calls[2].options.body), {
    session_id: "session-1",
    selected_node_id: "interest:data",
    expanded_node_ids: ["you", "interest:data"],
  });
  assert.equal(calls[3].options.method, "POST");
  assert.deepEqual(JSON.parse(calls[3].options.body), { session_id: "session-1" });
});

test("401 reports an expired sign-in session", async () => {
  await assert.rejects(
    loadAccountGraphSession("http://localhost:8000", "expired-token", async () =>
      response(401, { detail: "Invalid authentication token" })),
    (error) => error instanceof GraphApiError
      && error.status === 401
      && error.message.includes("sign-in session has expired"),
  );
});

test("node deletion sends the session and node ID and reports failures", async () => {
  let request;
  const result = await deleteCareerTreeNode("http://localhost:8000", "access-token", "session-1", "interest:design", async (url, options) => {
    request = { url, options };
    return response(200, { tree: { nodes: [] } });
  });
  assert.equal(request.url, "http://localhost:8000/career-tree/delete");
  assert.equal(request.options.method, "POST");
  assert.deepEqual(JSON.parse(request.options.body), { session_id: "session-1", node_id: "interest:design" });
  assert.deepEqual(result, { tree: { nodes: [] } });
  await assert.rejects(deleteCareerTreeNode("http://localhost:8000", "access-token", "session-1", "you", async () =>
    response(400, { detail: "The central name node cannot be deleted" })), /central name node/);
});

test("429 reports the server Retry-After value", async () => {
  await assert.rejects(
    continueCareerChat("http://localhost:8000", "access-token", "session-1", "hello", null, async () =>
      response(429, { detail: "Too many requests" }, { "Retry-After": "17" })),
    (error) => error instanceof GraphApiError
      && error.status === 429
      && error.retryAfter === "17"
      && error.message.includes("17 seconds"),
  );
});