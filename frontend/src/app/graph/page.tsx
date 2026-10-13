"use client";

import { useEffect, useRef, useCallback, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { AuthProvider } from "@/context/AuthContext";
import Navbar from "@/components/Navbar";
import ChatMarkdown from "@/components/ChatMarkdown";
import { CAREER_NODE_SIZE, radialTreeLayout } from "@/lib/radialTreeLayout.mjs";
import { canonicalizeCareerLabel } from "@/lib/careerLabels.mjs";
import { animateGraphFrames } from "@/lib/graphAnimation.mjs";
import { branchTree } from "@/lib/branchTree.mjs";
import { jobSearchFilters } from "@/lib/jobSearchFilters.mjs";
import {
  deleteCareerTreeNode,
  expandCareerTree,
  GraphApiError,
  initializeCareerTree,
  loadAccountGraphSession,
  resetCareerTree,
  saveCareerTreeView,
  continueCareerChat,
  explainCareerNode,
  applyCareerChanges,
  findCareerJobs,
  type CareerChangeProposal,
  type CareerJob,
} from "@/lib/graphApi.mjs";

const apiUrl = process.env.NEXT_PUBLIC_API_URL
  ?? process.env.NEXT_PUBLIC_BACKEND_URL
  ?? "http://localhost:8000";

type ChatMessage = { role: "assistant" | "user"; content: string };
type CareerNodeType = "user" | "interest" | "industry" | "role" | "job" | "skill";
type CareerTreeNode = { id: string; type: CareerNodeType; label: string; details: Record<string, unknown> };
type CareerTreeEdge = { id: string; source: string; target: string };
type CareerTree = {
  rootNodeId: string;
  nodes: CareerTreeNode[];
  edges: CareerTreeEdge[];
  selectedNodeId: string | null;
  expandedNodeIds: string[];
  generatedNodeIds: string[];
  profileContext: Record<string, unknown>;
  rebuildNotice?: string;
};

const expandableTypes: CareerNodeType[] = ["user", "interest", "industry"];

function LoadingSpinner() {
  return (
    <svg className="h-4 w-4 shrink-0 animate-spin motion-reduce:animate-none" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <circle className="opacity-25" cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="3" />
      <path d="M12 3a9 9 0 0 1 9 9" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
    </svg>
  );
}

function singleLineLabel(label: string) {
  return label.replace(/\s+/g, " ").trim();
}

function nodeSizeForLabel(label: string, fontSize: number) {
  const context = document.createElement("canvas").getContext("2d");
  if (!context) throw new Error("Could not measure career node titles.");
  context.font = `700 ${fontSize}px Arial, sans-serif`;
  return {
    width: Math.max(CAREER_NODE_SIZE.width, Math.ceil(context.measureText(label).width) + 64),
    height: CAREER_NODE_SIZE.height,
  };
}

function careerNodeMarkup() {
  return [
    { tagName: "rect", selector: "body" },
    { tagName: "text", selector: "label" },
    { tagName: "rect", selector: "toggleHitArea" },
    { tagName: "text", selector: "toggle" },
    {
      tagName: "g",
      selector: "loadingDots",
      children: [1, 2, 3].map((index) => ({
        tagName: "circle",
        selector: `loadingDot${index}`,
        attributes: { class: `career-loading-dot career-loading-dot-${index}` },
      })),
    },
  ];
}

function toggleHitAttrs(visible: boolean) {
  return {
    toggleHitArea: {
      x: "calc(w - 48)",
      y: "calc(h / 2 - 32)",
      width: 48,
      height: 64,
      fill: "transparent",
      stroke: "none",
      cursor: "pointer",
      pointerEvents: visible ? "all" : "none",
      display: visible ? "inline" : "none",
    },
    toggle: { display: visible ? "inline" : "none", pointerEvents: visible ? "auto" : "none" },
  };
}

function loadingDotAttrs(loading: boolean) {
  return {
    loadingDots: { display: loading ? "inline" : "none", pointerEvents: "none", role: "status", "aria-label": "Generating branch", "aria-hidden": !loading },
    loadingDot1: { cx: "calc(w - 40)", cy: "calc(h / 2)", r: 2.5, fill: "#173b2b" },
    loadingDot2: { cx: "calc(w - 32)", cy: "calc(h / 2)", r: 2.5, fill: "#173b2b" },
    loadingDot3: { cx: "calc(w - 24)", cy: "calc(h / 2)", r: 2.5, fill: "#173b2b" },
  };
}

function isCareerTree(value: unknown): value is CareerTree {
  if (!value || typeof value !== "object") return false;
  const tree = value as Partial<CareerTree>;
  return typeof tree.rootNodeId === "string"
    && Array.isArray(tree.nodes)
    && Array.isArray(tree.edges)
    && Array.isArray(tree.expandedNodeIds)
    && Array.isArray(tree.generatedNodeIds);
}

function visibleTreeNodeIds(tree: CareerTree) {
  const visible = new Set<string>([tree.rootNodeId]);
  const childrenByParent = new Map<string, string[]>();
  tree.edges.forEach(({ source, target }) => {
    childrenByParent.set(source, [...(childrenByParent.get(source) ?? []), target]);
  });
  const expanded = new Set(tree.expandedNodeIds);
  const queue = [tree.rootNodeId];
  while (queue.length) {
    const parentId = queue.shift()!;
    if (!expanded.has(parentId)) continue;
    (childrenByParent.get(parentId) ?? []).forEach((childId) => {
      if (visible.has(childId)) return;
      visible.add(childId);
      queue.push(childId);
    });
  }
  return visible;
}

function restoreChatHistory(state: Record<string, unknown>): ChatMessage[] {
  if (Array.isArray(state.chat_history)) {
    return state.chat_history.flatMap((turn) => {
      if (!turn || typeof turn !== "object") return [];
      const item = turn as { role?: unknown; content?: unknown };
      if ((item.role !== "user" && item.role !== "assistant") || typeof item.content !== "string") return [];
      return [{ role: item.role, content: item.content }];
    });
  }
  if (typeof state.user_input === "string" && state.user_input) {
    return [
      { role: "user", content: state.user_input },
      ...(typeof state.assistant_response === "string" && state.assistant_response
        ? [{ role: "assistant" as const, content: state.assistant_response }]
        : []),
    ];
  }
  return [];
}

function describeSavedProgress(state: Record<string, unknown>) {
  const sections = [
    ["Interests", state.interests],
    ["Industries", state.industries],
    ["Job paths", state.job_families],
    ["Skills", state.skills],
  ] as const;
  const saved = sections.flatMap(([label, value]) => {
    if (!Array.isArray(value) || value.length === 0) return [];
    return [`${label}: ${value.map((item) => canonicalizeCareerLabel(String(item))).join(", ")}`];
  });
  return saved.length ? saved.join(" · ") : "No saved career details yet.";
}

function GraphContent() {
  const { user, session, signOut, loading } = useAuth();
  const router = useRouter();
  const [helpOpen, setHelpOpen] = useState(false);
  const [chatOpen, setChatOpen] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [sessionOwnerId, setSessionOwnerId] = useState<string | null>(null);
  const [careerState, setCareerState] = useState<Record<string, unknown>>({});
  const [careerTree, setCareerTree] = useState<CareerTree | null>(null);
  const [expandingNodeIds, setExpandingNodeIds] = useState<string[]>([]);
  const [treeError, setTreeError] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [stateLoading, setStateLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [explaining, setExplaining] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);
  const [graphReady, setGraphReady] = useState(false);
  const [resetConfirmOpen, setResetConfirmOpen] = useState(false);
  const [resetting, setResetting] = useState(false);
  const [deleteNodeId, setDeleteNodeId] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [proposal, setProposal] = useState<CareerChangeProposal | null>(null);
  const [applyingChanges, setApplyingChanges] = useState(false);
  const [chatTab, setChatTab] = useState<"guide" | "jobs">("guide");
  const [jobNodeId, setJobNodeId] = useState<string | null>(null);
  const [hoveredNodeId, setHoveredNodeId] = useState<string | null>(null);
  const [jobLocation, setJobLocation] = useState("");
  const [jobWorkplace, setJobWorkplace] = useState("");
  const [jobs, setJobs] = useState<CareerJob[] | null>(null);
  const [jobError, setJobError] = useState<string | null>(null);
  const [searchingJobs, setSearchingJobs] = useState(false);
  const jobSearchRequestRef = useRef(0);
  const [changeStatus, setChangeStatus] = useState("");
  const chatEndRef = useRef<HTMLDivElement>(null);
  const selectedCareerNode = careerTree?.nodes.find((node) => node.id === careerTree.selectedNodeId);
  const hoveringRole = careerTree?.nodes.some((node) => node.id === hoveredNodeId && node.type === "role") ?? false;
  const jobNode = careerTree?.nodes.find((node) => node.id === jobNodeId);
  const userId = user?.id;
  const accessToken = session?.access_token;
  const activeSessionId = sessionOwnerId === userId ? sessionId : null;
  const canFindOpenings = selectedCareerNode?.type === "role" && !!activeSessionId && !stateLoading
    && !sending && !applyingChanges && !deleting && !resetting;
  const containerRef = useRef<HTMLDivElement>(null);
  const paperRef = useRef<import("@joint/core").dia.Paper | null>(null);
  const graphRef = useRef<import("@joint/core").dia.Graph | null>(null);
  const shapesRef = useRef<typeof import("@joint/core").shapes | null>(null);
  const careerTreeRef = useRef<CareerTree | null>(null);
  const draggedNodePositionsRef = useRef(new Map<string, { x: number; y: number }>());
  const nodeClickRef = useRef<(nodeId: string, toggleBranch: boolean) => void>(() => {});
  const expansionQueueRef = useRef<Promise<void>>(Promise.resolve());
  const viewSaveTimerRef = useRef<number | null>(null);
  const viewSavesRef = useRef(new Set<Promise<void>>());
  const reflowNodesRef = useRef(false);
  const stopBranchAnimationRef = useRef<(() => void) | null>(null);
  const animatedNodeIdsRef = useRef(new Set<string>());
  const treeRenderedRef = useRef(false);
  const visibleLayoutKeyRef = useRef("");
  careerTreeRef.current = careerTree;
  const firstName = (user?.user_metadata?.first_name as string | undefined) ?? "";
  const lastName = (user?.user_metadata?.last_name as string | undefined) ?? "";
  const rootLabel = `${firstName} ${lastName}`.trim() || user?.email || "You";
  const profileInterests = JSON.stringify(
    Array.isArray(user?.user_metadata?.career_interests)
      ? user.user_metadata.career_interests.map(String)
      : Array.isArray(user?.user_metadata?.interests)
        ? user.user_metadata.interests.map(String)
        : [],
  );

  // Smooth zoom state — target scale animates toward via RAF
  const targetScaleRef = useRef<number | null>(null);
  const zoomRafRef = useRef<number | null>(null);
  const zoomOriginRef = useRef<{ ox: number; oy: number } | null>(null);
  const stopViewAnimationRef = useRef<(() => void) | null>(null);

  const animateToScale = useCallback((targetScale: number, ox: number, oy: number) => {
    stopViewAnimationRef.current?.();
    stopViewAnimationRef.current = null;
    targetScaleRef.current = Math.min(3, Math.max(0.2, targetScale));
    zoomOriginRef.current = { ox, oy };
    if (zoomRafRef.current !== null) return; // already animating
    const step = () => {
      const paper = paperRef.current;
      if (!paper || targetScaleRef.current === null) { zoomRafRef.current = null; return; }
      const current = paper.scale().sx;
      const target = targetScaleRef.current;
      const diff = target - current;
      if (Math.abs(diff) < 0.001) {
        paper.scale(target, target);
        zoomRafRef.current = null;
        targetScaleRef.current = null;
        return;
      }
      const next = current + diff * 0.18; // easing factor
      const { ox: originX, oy: originY } = zoomOriginRef.current!;
      const t = paper.translate();
      const newTx = originX - (originX - t.tx) * (next / current);
      const newTy = originY - (originY - t.ty) * (next / current);
      paper.scale(next, next);
      paper.translate(newTx, newTy);
      zoomRafRef.current = requestAnimationFrame(step);
    };
    zoomRafRef.current = requestAnimationFrame(step);
  }, []);

  const zoom = useCallback((factor: number) => {
    const paper = paperRef.current;
    if (!paper) return;
    const current = targetScaleRef.current ?? paper.scale().sx;
    const svgEl = paper.el as HTMLElement;
    const rect = svgEl.getBoundingClientRect();
    const ox = rect.width / 2;
    const oy = rect.height / 2;
    animateToScale(current * factor, ox, oy);
  }, [animateToScale]);

  const resetView = useCallback(() => {
    const paper = paperRef.current;
    const container = containerRef.current;
    const root = graphRef.current?.getElements().find((element) => !element.get("careerGraphGenerated"));
    if (!paper || !container || !root) return;
    stopViewAnimationRef.current?.();
    if (zoomRafRef.current !== null) {
      cancelAnimationFrame(zoomRafRef.current);
      zoomRafRef.current = null;
    }
    targetScaleRef.current = null;
    const position = root.position();
    const size = root.size();
    const targetTx = container.clientWidth / 2 - position.x - size.width / 2;
    const targetTy = container.clientHeight / 2 - position.y - size.height / 2;
    const start = paper.translate();
    const startScale = paper.scale().sx;
    const frame = (progress: number) => {
      const scale = startScale + (1 - startScale) * progress;
      paper.scale(scale, scale);
      paper.translate(start.tx + (targetTx - start.tx) * progress, start.ty + (targetTy - start.ty) * progress);
    };
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      frame(1);
      stopViewAnimationRef.current = null;
    } else {
      stopViewAnimationRef.current = animateGraphFrames(frame, () => {
        stopViewAnimationRef.current = null;
      }, { duration: 200 });
    }
  }, []);

  // Redirect to home if not logged in
  async function explainSelectedNode() {
  if (!selectedCareerNode || selectedCareerNode.type === "user" || selectedCareerNode.id === careerTree?.rootNodeId || !activeSessionId || !accessToken || stateLoading || sending
    || applyingChanges || deleting || resetting || expandingNodeIds.length) return;
  const nodeId = selectedCareerNode.id;
  setChatTab("guide");
  setChatOpen(true);
  setApiError(null);
  setExplaining(true);
  setSending(true);
  try {
    await expansionQueueRef.current;
    if (viewSaveTimerRef.current !== null) {
      window.clearTimeout(viewSaveTimerRef.current);
      viewSaveTimerRef.current = null;
    }
    await Promise.all(viewSavesRef.current);
    const currentTree = careerTreeRef.current;
    if (currentTree) {
      await saveCareerTreeView(apiUrl, accessToken, activeSessionId,
        currentTree.selectedNodeId, currentTree.expandedNodeIds);
    }
    const result = await explainCareerNode(apiUrl, accessToken, activeSessionId, nodeId);
    setCareerState(result.state);
    setMessages(restoreChatHistory(result.state));
    setProposal(result.state.pending_career_changes ?? null);
  } catch (error) {
    setApiError(error instanceof Error ? error.message : "Could not explain this node. Please try again.");
  } finally {
    setExplaining(false);
    setSending(false);
  }
  }

  useEffect(() => {
    if (!loading && !user) {
      router.replace("/");
    }
  }, [user, loading, router]);

  useEffect(() => {
    if (!userId || !accessToken) return;
    const profileInterestList = JSON.parse(profileInterests) as string[];
    let cancelled = false;
    setStateLoading(true);
    setApiError(null);

    try {
      setSessionId(null);
      setSessionOwnerId(null);
      loadAccountGraphSession(apiUrl, accessToken)
        .then(async (result) => {
          if (!cancelled) {
            const savedSessionId = result.session_id;
            setSessionId(savedSessionId);
            setSessionOwnerId(userId);
            const savedState = result.state ?? {};
            setCareerState(savedState);
            setProposal((savedState.pending_career_changes as CareerChangeProposal | undefined) ?? null);
            setMessages(restoreChatHistory(savedState));
            if (isCareerTree(savedState.career_tree)) {
              setCareerTree(savedState.career_tree);
            } else if ((Array.isArray(savedState.interests) && savedState.interests.length) || profileInterestList.length) {
              const initialized = await initializeCareerTree(apiUrl, accessToken, savedSessionId, rootLabel, null, {
                name: rootLabel,
                interests: Array.isArray(savedState.interests) && savedState.interests.length ? savedState.interests : profileInterestList,
                education: user?.user_metadata?.education,
                background: user?.user_metadata?.background,
                skills: savedState.skills,
              });
              if (!cancelled) {
                setCareerTree(initialized.tree as CareerTree);
                setCareerState({ ...savedState, career_tree: initialized.tree });
              }
            } else {
              setChatOpen(true);
            }
          }
        })
        .catch((error: unknown) => {
          if (!cancelled) {
            setApiError(error instanceof Error ? error.message : "Could not load your saved career progress.");
            setChatOpen(true);
          }
        })
        .finally(() => {
          if (!cancelled) setStateLoading(false);
        });
    } catch (error) {
      setApiError(error instanceof Error ? error.message : "Could not open your career session.");
      setChatOpen(true);
      setStateLoading(false);
    }

    return () => { cancelled = true; };
  }, [userId, accessToken, rootLabel, user?.user_metadata, profileInterests]);

  async function submitChat(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const userInput = chatInput.trim();
    if (!userInput || !activeSessionId || !session?.access_token || sending) return;

    setChatInput("");
    setApiError(null);
    setMessages((current) => [...current, { role: "user", content: userInput }]);
    setSending(true);
    try {
      await expansionQueueRef.current;
      if (viewSaveTimerRef.current !== null) {
        window.clearTimeout(viewSaveTimerRef.current);
        viewSaveTimerRef.current = null;
      }
      await Promise.all(viewSavesRef.current);
      if (careerTreeRef.current) {
        await saveCareerTreeView(apiUrl, session.access_token, activeSessionId,
          careerTreeRef.current.selectedNodeId, careerTreeRef.current.expandedNodeIds);
        const result = await continueCareerChat(apiUrl, session.access_token, activeSessionId, userInput, careerTreeRef.current.selectedNodeId);
        setCareerState(result.state);
        setProposal(result.state.pending_career_changes ?? null);
        setMessages(restoreChatHistory(result.state));
        setChangeStatus("");
        return;
      }
      const initialized = await initializeCareerTree(
        apiUrl,
        session.access_token,
        activeSessionId,
        rootLabel,
        userInput,
        {
          education: user?.user_metadata?.education,
          background: user?.user_metadata?.background,
          skills: careerState.skills,
        },
      );
      setCareerTree(initialized.tree as CareerTree);
      setCareerState((current) => ({
        ...current,
        interests: (initialized.tree as CareerTree).nodes.filter((node) => node.type === "interest").map((node) => node.label),
        career_tree: initialized.tree,
      }));
      setTreeError(null);
      setChatOpen(true);
      setMessages((current) => [...current, {
        role: "assistant",
        content: initialized.response || "I found your interests. Select one to explore connected paths.",
      }]);
    } catch (error) {
      setChatInput(userInput);
      setApiError(error instanceof GraphApiError || error instanceof Error
        ? error.message
        : "Your message could not be sent. Please try again.");
    } finally {
      setSending(false);
    }
  }

    useEffect(() => {
      if (chatOpen && chatTab === "guide") chatEndRef.current?.scrollIntoView({ block: "nearest" });
    }, [messages, sending, proposal, chatOpen, chatTab]);

    async function confirmChanges(accept: boolean) {
      if (!proposal || !activeSessionId || !accessToken || applyingChanges) return;
      setApplyingChanges(true);
      setApiError(null);
      try {
        await expansionQueueRef.current;
        if (viewSaveTimerRef.current !== null) {
          window.clearTimeout(viewSaveTimerRef.current);
          viewSaveTimerRef.current = null;
        }
        await Promise.all(viewSavesRef.current);
        const result = await applyCareerChanges(apiUrl, accessToken, activeSessionId, proposal.id, accept);
        setCareerState(result.state);
        if (isCareerTree(result.state.career_tree)) {
          careerTreeRef.current = result.state.career_tree;
          setCareerTree(result.state.career_tree);
        }
        setProposal(null);
        setChangeStatus(accept ? "Changes saved. Existing branches were kept unless you approved refreshing them." : "Proposal dismissed. Your tree is unchanged.");
      } catch (error) {
        setApiError(error instanceof Error ? error.message : "Could not apply these changes.");
      } finally {
        setApplyingChanges(false);
      }
    }

    function openJobSearch() {
      if (!selectedCareerNode || selectedCareerNode.type !== "role") return;
      jobSearchRequestRef.current += 1;
      setSearchingJobs(false);
      setJobNodeId(selectedCareerNode.id);
      setJobs(null);
      setJobError(null);
      setChatTab("jobs");
      setChatOpen(true);
    }

    async function submitJobSearch(event: React.FormEvent<HTMLFormElement>) {
      event.preventDefault();
      if (!activeSessionId || !accessToken || !jobNodeId || searchingJobs) return;
      const requestId = ++jobSearchRequestRef.current;
      setSearchingJobs(true);
      setJobError(null);
      setJobs(null);
      try {
        const result = await findCareerJobs(apiUrl, accessToken, activeSessionId, jobNodeId,
          jobSearchFilters(jobWorkplace, jobLocation));
        if (requestId === jobSearchRequestRef.current) setJobs(result.jobs);
      } catch (error) {
        if (requestId === jobSearchRequestRef.current) {
          setJobError(error instanceof Error ? error.message : "Could not search openings.");
        }
      } finally {
        if (requestId === jobSearchRequestRef.current) setSearchingJobs(false);
      }
    }

  async function confirmGraphReset() {
    if (!activeSessionId || !accessToken || resetting) return;
    setResetting(true);
    setApiError(null);
    try {
      await resetCareerTree(apiUrl, accessToken, activeSessionId);
      careerTreeRef.current = null;
      setCareerTree(null);
      setCareerState((current) => {
        const next = { ...current };
        ["career_tree", "interests", "industries", "career_paths", "selected_industry", "job_families", "selected_job_family", "jobs", "selected_job", "skills", "user_input", "assistant_response", "chat_history"].forEach((key) => delete next[key]);
        return next;
      });
      setMessages([]);
      setProposal(null);
      setJobs(null);
      jobSearchRequestRef.current += 1;
      setSearchingJobs(false);
      setJobNodeId(null);
      setChatTab("guide");
      setChatInput("");
      setTreeError(null);
      setResetConfirmOpen(false);
      setChatOpen(true);
      resetView();
    } catch (error) {
      setApiError(error instanceof Error ? error.message : "Could not reset your career graph.");
    } finally {
      setResetting(false);
    }
  }

  function commitTreeView(nextTree: CareerTree) {
    careerTreeRef.current = nextTree;
    setCareerTree(nextTree);
    if (!activeSessionId || !accessToken) return;
    if (viewSaveTimerRef.current !== null) window.clearTimeout(viewSaveTimerRef.current);
    viewSaveTimerRef.current = window.setTimeout(() => {
      const save = saveCareerTreeView(
        apiUrl,
        accessToken,
        activeSessionId,
        nextTree.selectedNodeId,
        nextTree.expandedNodeIds,
      ).then(() => undefined).catch((error: unknown) => {
        setTreeError(error instanceof Error ? error.message : "Could not save your graph view.");
      });
      viewSavesRef.current.add(save);
      void save.finally(() => viewSavesRef.current.delete(save));
    }, 400);
  }

  function handleCareerNodeClick(nodeId: string, toggleBranch: boolean) {
    const current = careerTreeRef.current;
    const node = current?.nodes.find((item) => item.id === nodeId);
    if (!current || !node || expandingNodeIds.includes(nodeId) || deleteNodeId || deleting || sending || applyingChanges) return;

    const expanded = new Set(current.expandedNodeIds);
    const selectedTree = { ...current, selectedNodeId: nodeId };
    if (!toggleBranch || !expandableTypes.includes(node.type)) {
      commitTreeView(selectedTree);
      return;
    }
    if (expanded.has(nodeId)) {
      expanded.delete(nodeId);
      commitTreeView({ ...selectedTree, expandedNodeIds: [...expanded] });
      return;
    }
    if (current.generatedNodeIds.includes(nodeId)) {
      expanded.add(nodeId);
      commitTreeView({ ...selectedTree, expandedNodeIds: [...expanded] });
      return;
    }

    commitTreeView(selectedTree);
    setTreeError(null);
    setExpandingNodeIds((currentIds) => currentIds.includes(nodeId) ? currentIds : [...currentIds, nodeId]);
    const request = expansionQueueRef.current.then(() => {
      if (!activeSessionId || !accessToken) throw new Error("Your session is not ready. Please try again.");
      return expandCareerTree(apiUrl, accessToken, activeSessionId, nodeId);
    });
    expansionQueueRef.current = request.then(() => undefined, () => undefined);
    void request
      .then(({ tree: expandedTree }) => {
        const result = expandedTree as CareerTree;
        const nextTree = {
          ...result,
          selectedNodeId: nodeId,
          expandedNodeIds: [...new Set([...result.expandedNodeIds, nodeId])],
        };
        commitTreeView(nextTree);
      })
      .catch((error: unknown) => {
        setTreeError(error instanceof Error ? error.message : "Could not expand this career branch.");
      })
      .finally(() => setExpandingNodeIds((currentIds) => currentIds.filter((currentId) => currentId !== nodeId)));
  }

  nodeClickRef.current = handleCareerNodeClick;

  async function confirmNodeDeletion() {
    if (!deleteNodeId || !activeSessionId || !accessToken || deleting || expandingNodeIds.length) return;
    const current = careerTreeRef.current;
    if (deleteNodeId === current?.rootNodeId || current?.nodes.find((node) => node.id === deleteNodeId)?.type === "user") {
      setDeleteError("The central name node cannot be deleted.");
      return;
    }
    setDeleting(true);
    setDeleteError(null);
    if (viewSaveTimerRef.current !== null) {
      window.clearTimeout(viewSaveTimerRef.current);
      viewSaveTimerRef.current = null;
    }
    try {
      await Promise.all(viewSavesRef.current);
      const { tree } = await deleteCareerTreeNode(apiUrl, accessToken, activeSessionId, deleteNodeId);
      const nextTree = tree as CareerTree;
      reflowNodesRef.current = true;
      draggedNodePositionsRef.current.clear();
      careerTreeRef.current = nextTree;
      setCareerTree(nextTree);
      setCareerState((current) => ({
        ...current,
        career_tree: nextTree,
        interests: nextTree.nodes.filter((node) => node.type === "interest").map((node) => node.label),
      }));
      setDeleteNodeId(null);
      setTreeError(null);
    } catch (error) {
      setDeleteError(error instanceof Error ? error.message : "Could not delete this node. Please try again.");
    } finally {
      setDeleting(false);
    }
  }

  // Initialize JointJS canvas
  useEffect(() => {
    if (!user || !containerRef.current) return;

    let cancelled = false;
    let cleanup: (() => void) | undefined;

    (async () => {
      const { dia, shapes } = await import("@joint/core");
      if (cancelled || !containerRef.current) return;

      shapesRef.current = shapes;
      const graph = new dia.Graph({}, { cellNamespace: shapes });

      const containerEl = containerRef.current!;
      const paperEl = document.createElement("div");
      paperEl.style.height = "100%";
      paperEl.style.width = "100%";
      containerEl.appendChild(paperEl);
      const w = containerEl.clientWidth || 800;
      const h = containerEl.clientHeight || 600;

      const paper = new dia.Paper({
        el: paperEl,
        model: graph,
        width: "100%",
        height: "100%",
        gridSize: 10,
        drawGrid: { name: "mesh", args: { color: "#dcfce7", thickness: 1 } },
        background: { color: "#f7fdf9" },
        cellViewNamespace: shapes,
        interactive: true,
        // Infinite canvas — allow panning beyond the initial viewport
        overflow: true,
      });

      paperRef.current = paper;
      graphRef.current = graph;
      paper.on("element:pointerclick", (cellView: { model: { get: (key: string) => unknown } }, event: { target: EventTarget | null }) => {
        const nodeId = cellView.model.get("careerTreeNodeId");
        const toggleBranch = event.target instanceof Element
          && event.target.closest('[joint-selector="toggle"], [joint-selector="toggleHitArea"]') !== null;
        if (typeof nodeId === "string") nodeClickRef.current(nodeId, toggleBranch);
      });
      paper.on("element:mouseenter", (cellView: { model: { get: (key: string) => unknown } }) => {
        const nodeId = cellView.model.get("careerTreeNodeId");
        setHoveredNodeId(typeof nodeId === "string" ? nodeId : null);
      });
      paper.on("element:mouseleave", () => setHoveredNodeId(null));
      const deselectRole = () => {
        setHoveredNodeId(null);
        const tree = careerTreeRef.current;
        if (tree) nodeClickRef.current(tree.rootNodeId, false);
      };
      paper.on("blank:pointerclick", deselectRole);
      paper.on("link:pointerclick", deselectRole);

      const svgEl = paper.el as HTMLElement;
      svgEl.style.cursor = "move";

      // Pan on left-click drag on the blank paper background
      let isPanning = false;
      let panStart = { x: 0, y: 0 };
      let translateStart = { tx: 0, ty: 0 };

      paper.on("blank:pointerdown", (evt: object) => {
        stopViewAnimationRef.current?.();
        stopViewAnimationRef.current = null;
        const e = evt as MouseEvent;
        isPanning = true;
        panStart = { x: e.clientX, y: e.clientY };
        const t = paper.translate();
        translateStart = { tx: t.tx, ty: t.ty };
        svgEl.style.cursor = "grabbing";
      });

      const onMouseMove = (e: MouseEvent) => {
        if (!isPanning) return;
        const dx = e.clientX - panStart.x;
        const dy = e.clientY - panStart.y;
        paper.translate(translateStart.tx + dx, translateStart.ty + dy);
      };
      const onMouseUp = () => {
        isPanning = false;
        svgEl.style.cursor = "move";
      };
      const onContextMenu = (e: Event) => e.preventDefault();

      // Scroll-wheel zoom — accumulate target scale and animate via RAF
      const onWheel = (e: WheelEvent) => {
        e.preventDefault();
        const factor = e.deltaY < 0 ? 1.1 : 1 / 1.1;
        const current = targetScaleRef.current ?? paper.scale().sx;
        const rect = svgEl.getBoundingClientRect();
        const ox = e.clientX - rect.left;
        const oy = e.clientY - rect.top;
        animateToScale(current * factor, ox, oy);
      };

      window.addEventListener("mousemove", onMouseMove);
      window.addEventListener("mouseup", onMouseUp);
      svgEl.addEventListener("contextmenu", onContextMenu);
      svgEl.addEventListener("wheel", onWheel, { passive: false });

      const firstName = (user.user_metadata?.first_name as string | undefined) ?? "";
      const lastName = (user.user_metadata?.last_name as string | undefined) ?? "";
      const displayName = singleLineLabel(`${firstName} ${lastName}`.trim() || user.email || "Me");

      const { width: nodeW, height: nodeH } = nodeSizeForLabel(`${displayName}   +`, 18);
      const root = new shapes.standard.Rectangle({
        markup: careerNodeMarkup(),
        z: 1,
        position: { x: Math.round(w / 2 - nodeW / 2), y: Math.round(h / 2 - nodeH / 2) },
        size: { width: nodeW, height: nodeH },
        attrs: {
          ...loadingDotAttrs(false),
          ...toggleHitAttrs(false),
          root: { cursor: "move" },
          body: { fill: "#86efac", stroke: "#15803d", strokeWidth: 2, rx: 12, ry: 12 },
          label: {
            text: displayName,
            fill: "#166534",
            fontSize: 18,
            fontWeight: "700",
            fontFamily: "Arial, sans-serif",
          },
          toggle: {
            text: "",
            x: "calc(w - 24)",
            y: "calc(h / 2)",
            textAnchor: "middle",
            textVerticalAnchor: "middle",
            cursor: "pointer",
            fill: "#166534",
            fontSize: 18,
            fontWeight: "700",
            fontFamily: "Arial, sans-serif",
          },
        },
      });
      root.set("careerTreeNodeId", "you");

      graph.addCell(root);
      setGraphReady(true);

      cleanup = () => {
        stopViewAnimationRef.current?.();
        stopViewAnimationRef.current = null;
        stopBranchAnimationRef.current?.();
        stopBranchAnimationRef.current = null;
        animatedNodeIdsRef.current.clear();
        treeRenderedRef.current = false;
        visibleLayoutKeyRef.current = "";
        window.removeEventListener("mousemove", onMouseMove);
        window.removeEventListener("mouseup", onMouseUp);
        svgEl.removeEventListener("contextmenu", onContextMenu);
        svgEl.removeEventListener("wheel", onWheel);
        if (zoomRafRef.current !== null) { cancelAnimationFrame(zoomRafRef.current); zoomRafRef.current = null; }
        paper.remove();
        paperRef.current = null;
        graphRef.current = null;
        shapesRef.current = null;
        setHoveredNodeId(null);
        setGraphReady(false);
      };
    })();

    return () => {
      cancelled = true;
      cleanup?.();
    };
  }, [user, animateToScale]);

  useEffect(() => {
    const graph = graphRef.current;
    const shapes = shapesRef.current;
    const tree = careerTree ? branchTree(careerTree) : null;
    if (!graph || !graphReady || !shapes) return;
    stopBranchAnimationRef.current?.();
    stopBranchAnimationRef.current = null;
    if (!tree) {
      treeRenderedRef.current = false;
      visibleLayoutKeyRef.current = "";
      animatedNodeIdsRef.current.clear();
      const root = graph.getElements().find((element) => !element.get("careerGraphGenerated"));
      root?.attr({ ...loadingDotAttrs(false), ...toggleHitAttrs(false), label: { x: "calc(w / 2)" }, toggle: { text: "" } });
      draggedNodePositionsRef.current.clear();
      graph.getCells().filter((cell) => cell.get("careerGraphGenerated")).forEach((cell) => cell.remove());
      return;
    }
    const visibleIds = visibleTreeNodeIds(tree);
    const nodes = tree.nodes.filter((node) => node.id !== tree.rootNodeId && visibleIds.has(node.id));
    const root = graph.getElements().find((element) => element.get("careerTreeNodeId") === tree.rootNodeId);
    if (!root) return;
    const rootPosition = root.position();
    const rootSize = root.size();
    const nodeLabels = new Map(tree.nodes.map((node) => [
      node.id,
      singleLineLabel(canonicalizeCareerLabel(node.label)),
    ]));
    const toggleLabel = (node: CareerTreeNode & { originalId: string }) => !expandableTypes.includes(node.type)
      ? ""
      : expandingNodeIds.includes(node.originalId) ? "" : tree.expandedNodeIds.includes(node.id) ? "−" : "+";
    const nodeSizes = new Map(tree.nodes.map((node) => [
      node.id, node.type === "user" ? rootSize : nodeSizeForLabel(`${nodeLabels.get(node.id)!}${expandableTypes.includes(node.type) ? "   +" : ""}`, 16),
    ]));
    const visibleTree = {
      ...tree,
      nodes: tree.nodes.filter((node) => visibleIds.has(node.id)),
      edges: tree.edges.filter((edge) => visibleIds.has(edge.source) && visibleIds.has(edge.target)),
    };
    const layoutKey = JSON.stringify({
      nodes: visibleTree.nodes.map(({ id }) => [id, nodeSizes.get(id)]).sort(),
      edges: visibleTree.edges.map(({ source, target }) => [source, target]).sort(),
    });
    const layoutChanged = layoutKey !== visibleLayoutKeyRef.current;
    visibleLayoutKeyRef.current = layoutKey;
    if (layoutChanged) draggedNodePositionsRef.current.clear();
    graph.getElements().forEach((element) => {
      const nodeId = element.get("careerGraphGenerated") ? element.id.toString() : element.get("careerTreeNodeId");
      const automaticPosition = element.get("careerGraphLayoutPosition") as { x: number; y: number } | undefined;
      const position = element.position();
      if (!layoutChanged && !reflowNodesRef.current && typeof nodeId === "string" && !animatedNodeIdsRef.current.has(nodeId) && automaticPosition
        && (position.x !== automaticPosition.x || position.y !== automaticPosition.y)) {
        draggedNodePositionsRef.current.set(nodeId, position);
      }
    });
    animatedNodeIdsRef.current.clear();
    reflowNodesRef.current = false;
    const layoutPositions = radialTreeLayout(visibleTree, {
      x: rootPosition.x + rootSize.width / 2,
      y: rootPosition.y + rootSize.height / 2,
    }, nodeSizes);
    const animate = treeRenderedRef.current && !window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    treeRenderedRef.current = true;
    type Motion = {
      cell: import("@joint/core").dia.Cell;
      from?: { x: number; y: number };
      to?: { x: number; y: number };
      fromOpacity: number;
      toOpacity: number;
      remove?: boolean;
    };
    const motions: Motion[] = [];
    const parentByNode = new Map<string, string>();
    tree.edges.forEach(({ source, target }) => {
      if (!parentByNode.has(target)) parentByNode.set(target, source);
    });
    const parentPosition = (nodeId: string, size: { width: number; height: number }) => {
      const visited = new Set([nodeId]);
      let parentId = parentByNode.get(nodeId);
      while (parentId && !visited.has(parentId)) {
        visited.add(parentId);
        if (visibleIds.has(parentId)) {
          const parent = parentId === tree.rootNodeId ? root : graph.getCell(parentId);
          const parentElement = parent?.isElement() ? parent : undefined;
          const position = parentElement?.position() ?? layoutPositions.get(parentId) ?? rootPosition;
          const parentSize = parentElement?.size() ?? nodeSizes.get(parentId) ?? rootSize;
          return { x: position.x + (parentSize.width - size.width) / 2, y: position.y + (parentSize.height - size.height) / 2 };
        }
        parentId = parentByNode.get(parentId);
      }
      return { x: rootPosition.x + (rootSize.width - size.width) / 2, y: rootPosition.y + (rootSize.height - size.height) / 2 };
    };
    nodes.forEach((node) => {
      const automaticPosition = layoutPositions.get(node.id)!;
      const position = draggedNodePositionsRef.current.get(node.id) ?? automaticPosition;
      const colors: Record<CareerNodeType, { fill: string; stroke: string }> = {
        user: { fill: "#86efac", stroke: "#15803d" },
        interest: { fill: "#f0fdf4", stroke: "#86b99b" },
        industry: { fill: "#e1f0f0", stroke: "#4d9292" },
        role: { fill: "#eef0f4", stroke: "#738096" },
        job: { fill: "#fff1dd", stroke: "#d39850" },
        skill: { fill: "#fce8e6", stroke: "#ca776c" },
      };
      const selected = tree.selectedNodeId === node.originalId;
      const existing = graph.getCell(node.id);
      const cell = existing?.isElement() ? existing : new shapes.standard.Rectangle({
        markup: careerNodeMarkup(),
        id: node.id,
        z: 1,
        position,
        size: nodeSizes.get(node.id),
        attrs: {
          ...loadingDotAttrs(expandingNodeIds.includes(node.originalId)),
          ...toggleHitAttrs(Boolean(toggleLabel(node))),
          root: { cursor: "move" },
          body: { fill: colors[node.type].fill, stroke: selected ? "#17252b" : colors[node.type].stroke, strokeWidth: selected ? 2.5 : 1.5, rx: 7, ry: 7 },
          label: { text: nodeLabels.get(node.id), x: expandableTypes.includes(node.type) ? "calc(w / 2 - 16)" : "calc(w / 2)", cursor: "move", fill: "#173b2b", fontSize: 16, fontFamily: "Arial, sans-serif", fontWeight: selected ? "700" : "600" },
          toggle: {
            text: toggleLabel(node),
            x: "calc(w - 24)",
            y: "calc(h / 2)",
            textAnchor: "middle",
            textVerticalAnchor: "middle",
            cursor: "pointer",
            fill: "#173b2b",
            fontSize: 16,
            fontFamily: "Arial, sans-serif",
            fontWeight: "700",
          },
        },
      });
      const size = nodeSizes.get(node.id)!;
      cell.resize(size.width, size.height);
      cell.attr({
        ...loadingDotAttrs(expandingNodeIds.includes(node.originalId)),
        ...toggleHitAttrs(Boolean(toggleLabel(node))),
        root: { pointerEvents: "auto", cursor: node.type === "role" ? "pointer" : "move" },
        body: { stroke: selected ? "#17252b" : colors[node.type].stroke, strokeWidth: selected ? 2.5 : 1.5 },
        label: { text: nodeLabels.get(node.id), x: expandableTypes.includes(node.type) ? "calc(w / 2 - 16)" : "calc(w / 2)", fontWeight: selected ? "700" : "600", cursor: node.type === "role" ? "pointer" : "move" },
        toggle: { text: toggleLabel(node) },
      });
      const from = existing ? cell.position() : parentPosition(node.id, size);
      const fromOpacity = existing ? Number(cell.attr("root/opacity") ?? 1) : 0;
      if (animate && (from.x !== position.x || from.y !== position.y || fromOpacity !== 1)) {
        cell.position(from.x, from.y);
        cell.attr({ root: { opacity: fromOpacity, pointerEvents: "none" } });
        animatedNodeIdsRef.current.add(node.id);
        motions.push({ cell, from, to: position, fromOpacity, toOpacity: 1 });
      } else {
        cell.position(position.x, position.y);
        cell.attr("root/opacity", 1);
      }
      cell.set("careerGraphGenerated", true);
      cell.set("careerGraphLayoutPosition", automaticPosition);
      cell.set("careerTreeNodeId", node.originalId);
      cell.set("careerTreeNodeType", node.type);
      if (!existing) graph.addCell(cell);
    });
    root.attr("body/stroke", tree.selectedNodeId === tree.rootNodeId ? "#17252b" : "#15803d");
    const rootNode = tree.nodes.find((node) => node.id === tree.rootNodeId);
    root.attr({ ...loadingDotAttrs(expandingNodeIds.includes(tree.rootNodeId)), ...toggleHitAttrs(Boolean(rootNode && toggleLabel(rootNode))), label: { x: "calc(w / 2 - 16)" }, toggle: { text: rootNode ? toggleLabel(rootNode) : "" } });
    root.attr("body/strokeWidth", tree.selectedNodeId === tree.rootNodeId ? 3 : 2);

    const jointIds = new Map<string, string>();
    jointIds.set(tree.rootNodeId, root.id.toString());
    nodes.forEach((node) => jointIds.set(node.id, node.id));
    const visibleLinkIds = new Set<string>();
    tree.edges.filter((edge) => visibleIds.has(edge.source) && visibleIds.has(edge.target)).forEach((edge) => {
      const source = jointIds.get(edge.source);
      const target = jointIds.get(edge.target);
      if (!source || !target) return;
      const linkId = `career-edge:${edge.id}`;
      visibleLinkIds.add(linkId);
      const existing = graph.getCell(linkId);
      const link = existing ?? new shapes.standard.Link({
        id: `career-edge:${edge.id}`,
        z: 0,
        source: { id: source, anchor: { name: "center" }, connectionPoint: { name: "anchor" } },
        target: { id: target, anchor: { name: "center" }, connectionPoint: { name: "anchor" } },
        attrs: { line: { stroke: "#8c9c97", strokeWidth: 1.5, sourceMarker: { type: "path", d: "" }, targetMarker: { type: "path", d: "" } } },
      });
      const fromOpacity = existing ? Number(link.attr("root/opacity") ?? 1) : 0;
      if (animate && fromOpacity !== 1) {
        link.attr("root/opacity", fromOpacity);
        motions.push({ cell: link, fromOpacity, toOpacity: 1 });
      } else link.attr("root/opacity", 1);
      link.set("careerGraphGenerated", true);
      if (!existing) graph.addCell(link);
    });
    graph.getCells().filter((cell) => cell.get("careerGraphGenerated")).forEach((cell) => {
      const nodeId = cell.id.toString();
      const retained = cell.isElement() ? visibleIds.has(nodeId) : visibleLinkIds.has(cell.id.toString());
      if (retained) return;
      if (!animate) { cell.remove(); return; }
      cell.attr("root/pointerEvents", "none");
      if (cell.isElement()) {
        animatedNodeIdsRef.current.add(nodeId);
        motions.push({
          cell, from: cell.position(), to: parentPosition(nodeId, cell.size()),
          fromOpacity: Number(cell.attr("root/opacity") ?? 1), toOpacity: 0, remove: true,
        });
      } else {
        motions.push({ cell, fromOpacity: Number(cell.attr("root/opacity") ?? 1), toOpacity: 0, remove: true });
      }
    });
    if (motions.length) {
      stopBranchAnimationRef.current = animateGraphFrames((progress) => {
        motions.forEach(({ cell, from, to, fromOpacity, toOpacity }) => {
          if (cell.isElement() && from && to) {
            cell.position(from.x + (to.x - from.x) * progress, from.y + (to.y - from.y) * progress);
          }
          cell.attr("root/opacity", fromOpacity + (toOpacity - fromOpacity) * progress);
        });
      }, () => {
        motions.forEach(({ cell, remove }) => {
          if (remove) cell.remove();
          else cell.attr("root/pointerEvents", "auto");
        });
        animatedNodeIdsRef.current.clear();
        stopBranchAnimationRef.current = null;
      });
    }
  }, [careerTree, expandingNodeIds, graphReady]);

  useEffect(() => {
    if (!helpOpen && !chatOpen && !resetConfirmOpen && !deleteNodeId) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setHelpOpen(false);
        setChatOpen(false);
        setResetConfirmOpen(false);
        if (!deleting) setDeleteNodeId(null);
      }
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [helpOpen, chatOpen, resetConfirmOpen, deleteNodeId, deleting]);

  const canDeleteSelectedNode = selectedCareerNode && selectedCareerNode.type !== "user" && selectedCareerNode.id !== careerTree?.rootNodeId;
  const nodeToDelete = careerTree?.nodes.find((node) => node.id === deleteNodeId);

  if (loading || !user) return null;

  return (
    <div className="flex h-dvh flex-col bg-background-light text-sm">
      <Navbar user={user} onLogin={() => {}} onSignup={() => {}} onSignOut={async () => { await signOut(); router.replace("/"); }} />
      <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
        {/* Toolbar */}
        <div className="grid shrink-0 grid-cols-2 items-center gap-2 border-b border-primary-200 bg-primary-50 px-3 py-2 md:flex md:flex-wrap md:px-6">
          <span className="col-span-2 whitespace-nowrap text-lg font-semibold text-primary-900 md:text-base">Career Graph</span>
          <span className="hidden text-sm text-neutral-500 xl:block">— drag nodes to explore your path</span>
          <button type="button" onClick={() => setResetConfirmOpen(true)} disabled={!activeSessionId || resetting || sending || applyingChanges || expandingNodeIds.length > 0} className={`${canDeleteSelectedNode ? "max-[359px]:col-span-2" : "col-span-2"} row-start-3 inline-flex min-h-11 min-w-0 items-center justify-center gap-2 whitespace-nowrap rounded-lg border border-red-300 bg-white px-3 py-2 text-sm font-semibold text-red-800 transition hover:bg-red-50 disabled:opacity-50 md:ml-4 md:min-h-9`} title="Reset saved career graph" aria-label="Reset graph">
            <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M2.5 5.5A5.5 5.5 0 1 1 2 9"/><path d="M2.5 2.5v3h3"/></svg>
            Reset graph
          </button>
          {canDeleteSelectedNode && (
            <button
              type="button"
              disabled={!activeSessionId || expandingNodeIds.length > 0 || deleting || sending || applyingChanges}
              onClick={() => { setDeleteError(null); setDeleteNodeId(selectedCareerNode.id); }}
              className="row-start-3 min-h-11 min-w-0 whitespace-nowrap rounded-lg border border-red-300 bg-white px-3 py-2 font-semibold text-red-800 hover:bg-red-50 disabled:opacity-50 max-[359px]:col-span-2 max-[359px]:row-start-4 md:min-h-9"
            >
              Delete node
            </button>
          )}
          <button
            onClick={() => { setChatTab("guide"); setChatOpen((open) => chatTab === "jobs" ? true : !open); }}
            className="col-start-1 row-start-2 inline-flex min-h-11 min-w-0 items-center justify-center gap-2 whitespace-nowrap rounded-lg border border-primary-300 bg-white px-3 py-2 text-sm font-semibold text-primary-800 shadow-sm transition hover:bg-primary-100 md:ml-auto md:min-h-9"
            aria-expanded={chatOpen}
            aria-controls="career-chat-sidebar"
            title={chatOpen ? "Close AI chat" : "Open AI chat"}
          >
            <svg width="15" height="15" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M3 3.75h9a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2H7l-4 2v-9a2 2 0 0 1 2-2Z" /></svg>
            AI Chat
          </button>
          <button
            onClick={() => setHelpOpen(true)}
            className="col-start-2 row-start-2 inline-flex min-h-11 min-w-0 items-center justify-center gap-2 whitespace-nowrap rounded-lg border border-primary-200 bg-white px-3 py-2 text-sm font-semibold text-primary-700 shadow-sm transition hover:bg-primary-100 md:min-h-9"
            aria-haspopup="dialog"
            aria-expanded={helpOpen}
          >
            <span className="flex h-4 w-4 items-center justify-center rounded-full border border-primary-400 text-[11px]">?</span>
            How to use
          </button>
        </div>
        {careerTree && (
          <div className="flex shrink-0 flex-wrap items-center justify-between gap-2 border-b border-primary-200 bg-white px-4 py-2">
            <span id="openings-selection-hint" className="min-w-0 text-sm text-primary-950">
              {selectedCareerNode
                ? `Selected: ${canonicalizeCareerLabel(selectedCareerNode.label)}`
                : "Select a node to learn about it, or a purple role to find jobs."}
            </span>
            <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={() => void explainSelectedNode()}
              disabled={!selectedCareerNode || selectedCareerNode.type === "user" || selectedCareerNode.id === careerTree.rootNodeId || !activeSessionId || stateLoading || sending || applyingChanges || deleting || resetting || expandingNodeIds.length > 0}
              aria-busy={explaining}
              aria-controls="career-chat-sidebar"
              className="inline-flex min-h-11 items-center justify-center gap-2 rounded-lg border border-primary-300 bg-white px-3 py-2 font-semibold text-primary-800 transition hover:bg-primary-50 disabled:cursor-not-allowed disabled:opacity-60 md:min-h-9"
            >
              {explaining && <LoadingSpinner />}
              {explaining ? "Explaining..." : "Explain node"}
            </button>
            <button
              onClick={openJobSearch}
              disabled={!canFindOpenings || (searchingJobs && selectedCareerNode?.id === jobNodeId)}
              aria-busy={searchingJobs && selectedCareerNode?.id === jobNodeId}
              aria-describedby="openings-selection-hint"
              className={`inline-flex min-h-11 items-center justify-center gap-2 rounded-lg bg-primary-700 px-3 py-2 font-semibold text-white transition-opacity motion-reduce:transition-none enabled:hover:bg-primary-800 disabled:cursor-not-allowed md:min-h-9 ${
                canFindOpenings || hoveringRole ? "opacity-100" : "opacity-60"
              }`}
            >
              {searchingJobs && selectedCareerNode?.id === jobNodeId ? (
                <><LoadingSpinner /> Searching...</>
              ) : "Find openings"}
            </button>
            </div>
          </div>
        )}
        {careerTree?.rebuildNotice && (
          <div role="status" className="border-b border-primary-200 bg-primary-50 px-4 py-3 text-primary-950">
            {careerTree.rebuildNotice}
          </div>
        )}
        {treeError && (
          <p role="alert" className="shrink-0 border-b border-red-200 bg-red-50 px-6 py-3 text-sm text-red-700">
            {treeError}
          </p>
        )}
        {/* Canvas */}
        <div className="relative flex min-h-0 flex-1 flex-col overflow-hidden md:flex-row">
          <div
            ref={containerRef}
            className="h-full min-h-0 min-w-0 w-full flex-1"
            role="img"
            aria-label="Interactive career graph. Drag to pan and use the zoom controls to explore your path."
          />

          {/* Zoom controls */}
          <div className="absolute bottom-6 right-6 flex flex-col gap-1 overflow-hidden rounded-xl border border-primary-200 bg-white shadow-md">
            <button
              onClick={() => zoom(1.2)}
              className="cursor-pointer flex h-11 w-11 items-center justify-center text-primary-700 hover:bg-primary-50 transition"
              aria-label="Zoom in"
            >
              <svg width="19" height="19" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><line x1="8" y1="2" x2="8" y2="14"/><line x1="2" y1="8" x2="14" y2="8"/></svg>
            </button>
            <div className="h-px bg-primary-200" />
            <button
              onClick={() => zoom(1 / 1.2)}
              className="cursor-pointer flex h-11 w-11 items-center justify-center text-primary-700 hover:bg-primary-50 transition"
              aria-label="Zoom out"
            >
              <svg width="19" height="19" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><line x1="2" y1="8" x2="14" y2="8"/></svg>
            </button>
            <div className="h-px bg-primary-200" />
            <button
              onClick={resetView}
              className="cursor-pointer flex h-11 w-11 items-center justify-center text-primary-700 hover:bg-primary-50 transition"
              aria-label="Reset view"
              title="Reset view"
            >
              <svg width="15" height="15" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M1 4V1h3"/><path d="M14 11v3h-3"/><path d="M1 4a7 7 0 0 1 12 2"/><path d="M14 11a7 7 0 0 1-12-2"/></svg>
            </button>
          </div>
          <button
            type="button"
            tabIndex={chatOpen ? 0 : -1}
            aria-hidden={!chatOpen}
            aria-label="Close AI chat"
            onClick={() => setChatOpen(false)}
            className={`absolute inset-0 z-20 bg-neutral-950/15 transition-opacity duration-300 motion-reduce:transition-none ${chatOpen ? "opacity-100" : "pointer-events-none opacity-0"}`}
          />
          <section
            id="career-chat-sidebar"
            aria-label="Career guide chat"
            aria-hidden={!chatOpen}
            inert={!chatOpen}
            className={`absolute inset-y-0 right-0 z-30 flex w-full max-w-96 flex-col border-l border-primary-200 bg-white shadow-xl transition-transform duration-300 ease-in-out motion-reduce:transition-none ${chatOpen ? "translate-x-0" : "pointer-events-none translate-x-full"}`}
          >
            <header className="flex shrink-0 items-center justify-between border-b border-primary-100 px-4 py-3">
              <div>
                <h2 className="text-base font-semibold text-primary-950">Career guide</h2>
                <p className="mt-1 text-sm text-neutral-500">Explore your next direction</p>
              </div>
              <button
                type="button"
                onClick={() => setChatOpen(false)}
                className="flex h-9 w-9 items-center justify-center rounded-lg text-neutral-600 transition hover:bg-primary-50 hover:text-primary-900"
                aria-label="Close AI chat"
                title="Close AI chat"
              >
                <svg width="17" height="17" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" aria-hidden="true"><path d="m4 4 9 9M13 4l-9 9" /></svg>
              </button>
            </header>
            <div className="flex shrink-0 gap-2 border-b border-primary-100 px-4 py-2" role="tablist" aria-label="Career guide sections">
              <button role="tab" aria-selected={chatTab === "guide"} onClick={() => setChatTab("guide")} className={`min-h-11 flex-1 rounded-lg px-3 py-2 font-semibold md:min-h-9 ${chatTab === "guide" ? "bg-primary-100 text-primary-950" : "text-neutral-600"}`}>Chat</button>
              <button role="tab" aria-selected={chatTab === "jobs"} onClick={() => setChatTab("jobs")} className={`min-h-11 flex-1 rounded-lg px-3 py-2 font-semibold md:min-h-9 ${chatTab === "jobs" ? "bg-primary-100 text-primary-950" : "text-neutral-600"}`}>Openings</button>
            </div>
            {chatTab === "guide" ? (
            <>
            <div className="min-h-0 flex-1 overflow-y-auto px-4 py-4" aria-live="polite" aria-relevant="additions text">
              {stateLoading || !activeSessionId ? (
                <p className="text-sm text-neutral-500" role="status">Loading your saved career progress...</p>
              ) : messages.length === 0 ? (
                <div className="space-y-4">
                  <p className="text-sm leading-6 text-neutral-700">
                    Hi! I&apos;m glad you&apos;re here. We can explore career paths that fit what you enjoy and what you&apos;d like to learn. What kinds of things energize you?
                  </p>
                  <p className="border-t border-primary-100 pt-4 text-sm leading-6 text-neutral-500">
                    <span className="font-semibold text-primary-800">Saved progress</span>
                    <span className="ml-2">{describeSavedProgress(careerState)}</span>
                  </p>
                </div>
              ) : (
                <>
                  <ol className="space-y-4">
                    {messages.map((message, index) => (
                      <li key={`${index}-${message.role}`} className="space-y-2 text-sm leading-6">
                        {message.role === "assistant" ? (
                          <>
                            <p className="text-base font-semibold text-primary-800">Guide</p>
                            <ChatMarkdown content={canonicalizeCareerLabel(message.content)} />
                          </>
                        ) : (
                          <>
                            <p className="text-base font-semibold text-primary-800">You</p>
                            <p className="whitespace-pre-wrap text-neutral-700">{message.content}</p>
                          </>
                        )}
                      </li>
                    ))}
                  </ol>
                  <details className="mt-5 border-t border-primary-100 pt-4 text-sm leading-6 text-neutral-500">
                    <summary className="cursor-pointer font-semibold text-primary-800">Saved progress</summary>
                  <p>
                    <span className="font-semibold text-primary-800">Progress</span>
                    <span className="ml-2">{describeSavedProgress(careerState)}</span>
                  </p>
                  </details>
                </>
              )}
              {sending && (
                <p className="mt-4 flex items-center gap-2 text-sm text-neutral-500" role="status">
                  <LoadingSpinner />
                  {explaining ? "Preparing an overview, skills, qualifications, and learning resources..." : "Thinking..."}
                </p>
              )}
              {apiError && <p className="mt-3 text-sm text-red-700" role="alert">{apiError}</p>}
              {proposal && (
                <section aria-label="Proposed tree changes" className="mt-4 space-y-3 rounded-xl border border-primary-200 bg-primary-50 p-4">
                  <h3 className="font-semibold text-primary-950">Review changes</h3>
                  {proposal.interests.length > 0 && <p>Add interests: <strong>{proposal.interests.map(canonicalizeCareerLabel).join(", ")}</strong></p>}
                  {proposal.context && <p>Save background: {proposal.context}</p>}
                  {proposal.refresh.length > 0 && <p className="text-red-800">Refresh {proposal.refresh.map((item) => canonicalizeCareerLabel(item.label)).join(", ")}: generated descendants will be cleared. Interests and other branches stay.</p>}
                  <p className="text-sm text-neutral-600">No changes are made until you apply. Saved background guides future suggestions; existing branches stay unless listed for refresh.</p>
                  <div className="flex flex-wrap gap-2">
                    <button onClick={() => void confirmChanges(true)} disabled={applyingChanges || sending} className="min-h-11 rounded-lg bg-primary-700 px-4 py-2 font-semibold text-white disabled:opacity-50">{applyingChanges ? "Saving..." : "Apply changes"}</button>
                    <button onClick={() => void confirmChanges(false)} disabled={applyingChanges || sending} className="min-h-11 rounded-lg border border-primary-300 bg-white px-4 py-2 disabled:opacity-50">Keep tree as is</button>
                  </div>
                </section>
              )}
              {changeStatus && <p role="status" className="mt-3 text-sm text-primary-900">{changeStatus}</p>}
              <div ref={chatEndRef} />
            </div>
            <div className="shrink-0 border-t border-primary-100">
              {selectedCareerNode && selectedCareerNode.type !== "user" && (
                <p className="mx-4 mt-3 rounded-lg bg-primary-50 px-3 py-2 text-sm text-primary-950">Discussing: <strong>{canonicalizeCareerLabel(selectedCareerNode.label)}</strong></p>
              )}
            <form onSubmit={submitChat} className="flex items-end gap-2 px-4 py-3">
              <label htmlFor="career-chat-input" className="sr-only">Message your career guide</label>
              <textarea
                id="career-chat-input"
                rows={2}
                value={chatInput}
                onChange={(event) => setChatInput(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
                    event.preventDefault();
                    event.currentTarget.form?.requestSubmit();
                  }
                }}
                placeholder="Share interests, ask questions, or refine a path..."
                maxLength={4000}
                disabled={stateLoading || sending || applyingChanges || !activeSessionId}
                className="min-w-0 flex-1 resize-none rounded-lg border border-primary-200 bg-background-light px-3 py-2 text-base text-neutral-900 outline-none placeholder:text-neutral-500 focus:border-primary-500 focus:ring-2 focus:ring-primary-100 disabled:opacity-60 sm:text-sm"
              />
              <button
                type="submit"
                disabled={stateLoading || sending || applyingChanges || !chatInput.trim() || !activeSessionId}
                className="min-h-11 rounded-lg bg-primary-700 px-3 py-2 text-sm font-semibold text-white transition hover:bg-primary-800 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {sending ? "Sending..." : "Send"}
              </button>
            </form>
            </div>
            </>
            ) : (
              <div className="min-h-0 flex-1 overflow-y-auto px-4 py-4">
                {!jobNode ? <p className="leading-7 text-neutral-700">The tree ends at purple role nodes. Select one, then choose <strong>Find openings</strong>. Use Chat for specific titles, skills, and qualifications.</p> : (
                  <>
                    <h3 className="font-semibold text-primary-950">{canonicalizeCareerLabel(jobNode.label)}</h3>
                    <p className="mt-2 text-sm leading-6 text-neutral-600">Search this role and closely related employer job titles in its career branch. Results are U.S.-based postings from the last 30 days via TheirStack. Each search uses provider credits. Confirm availability and eligibility on the original listing.</p>
                    <form onSubmit={submitJobSearch} className="mt-4 space-y-3">
                      <fieldset disabled={searchingJobs}>
                        <legend className="text-lg font-semibold text-primary-950">Work setting (required)</legend>
                        <div className="mt-2 grid gap-2 sm:grid-cols-2">
                          {[["remote", "Remote"], ["local", "Hybrid / in-person"]].map(([value, label]) => (
                            <label key={value} className={`flex min-h-12 cursor-pointer items-center gap-3 rounded-lg border px-3 py-3 text-sm font-semibold transition-colors focus-within:ring-2 focus-within:ring-primary-400 ${jobWorkplace === value ? "border-primary-600 bg-primary-50 text-primary-950" : "border-primary-200 bg-white text-neutral-700"} ${searchingJobs ? "cursor-not-allowed opacity-60" : "hover:border-primary-500"}`}>
                              <input type="radio" name="job-workplace" value={value} required checked={jobWorkplace === value} onChange={() => { setJobWorkplace(value); setJobs(null); setJobError(null); }} className="h-4 w-4 shrink-0 accent-primary-700" />
                              {label}
                            </label>
                          ))}
                        </div>
                      </fieldset>
                      {jobWorkplace === "local" && (
                        <label className="block text-sm font-semibold"><span className="text-lg text-primary-950">City, state (optional)</span>
                          <input aria-label="Job location" aria-describedby="job-location-format" placeholder="Boston, MA" value={jobLocation} onChange={(event) => { setJobLocation(event.target.value); setJobs(null); setJobError(null); }} disabled={searchingJobs} maxLength={120} className="mt-1 min-h-11 w-full rounded-lg border border-primary-200 px-3 py-2" />
                          <span id="job-location-format" className="mt-1 block font-normal text-neutral-600">Use City, ST, such as Boston, MA. Leave blank to search across the U.S.</span>
                        </label>
                      )}
                      {jobWorkplace === "remote" && <p className="text-sm text-neutral-600">Remote openings across the United States. No city required.</p>}
                      <p className="text-sm text-neutral-600">Use Chat to discuss your qualifications. Listings are not a claim that you qualify.</p>
                      <button
                        type="submit"
                        disabled={searchingJobs || !activeSessionId}
                        aria-busy={searchingJobs}
                        className="inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-lg bg-primary-700 px-4 py-2 font-semibold text-white disabled:cursor-not-allowed disabled:opacity-70"
                      >
                        {searchingJobs && <LoadingSpinner />}
                        {searchingJobs ? "Searching..." : "Search openings"}
                      </button>
                    </form>
                    {jobError && <p role="alert" className="mt-4 text-red-700">{jobError}</p>}
                    {searchingJobs && (
                      <div role="status" className="mt-4 flex items-start gap-3 rounded-lg border border-primary-200 bg-primary-50 p-3 text-primary-950">
                        <div className="mt-1"><LoadingSpinner /></div>
                        <div>
                          <p className="font-semibold">Searching for openings</p>
                          <p className="mt-1 text-sm leading-6 text-neutral-600">Matching related job titles and checking recent listings. This can take about a minute.</p>
                        </div>
                      </div>
                    )}
                    {jobs?.length === 0 && <p role="status" className="mt-4 leading-7">No recent listings matched this role or its related job titles with your filters. Try another work setting or clear the city for a nationwide search. Openings are not guaranteed for every career path.</p>}
                    {jobs && jobs.length > 0 && <div className="mt-5 space-y-4" aria-label="Job results">
                      <p className="text-sm text-neutral-500">Source: TheirStack · Up to 5 results</p>
                      {jobs.map((job) => <article key={job.id} className="rounded-xl border border-primary-200 p-4">
                        <h4 className="font-semibold text-primary-950">{canonicalizeCareerLabel(job.title)}</h4>
                        <p className="mt-1 text-sm text-neutral-700">{job.company || "Company not supplied"} · {job.location || "Location not supplied"}</p>
                        <p className="mt-1 text-sm text-neutral-500">{job.remote ? "Remote · " : ""}Posted: {job.posted || "Date not supplied"}</p>
                        {job.description && <details className="mt-2 text-sm"><summary className="cursor-pointer text-primary-800">Description &amp; requirements</summary><p className="mt-2 whitespace-pre-wrap break-words leading-6">{job.description}</p></details>}
                        <a href={job.url} target="_blank" rel="noopener noreferrer" className="mt-3 inline-flex min-h-11 items-center rounded-lg border border-primary-300 px-3 py-2 font-semibold text-primary-800">View original listing ↗</a>
                      </article>)}
                    </div>}
                  </>
                )}
              </div>
            )}
          </section>
        </div>
      </div>

      {helpOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-primary-950/25 p-4 backdrop-blur-sm"
          onClick={() => setHelpOpen(false)}
          role="presentation"
        >
          <section
            className="max-h-[calc(100dvh-2rem)] w-full max-w-2xl overflow-y-auto overscroll-contain rounded-2xl border border-primary-100 bg-white p-6 shadow-2xl sm:p-8"
            onClick={(event) => event.stopPropagation()}
            role="dialog"
            aria-modal="true"
            aria-labelledby="graph-help-title"
          >
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-primary-600">Quick guide</p>
                <h2 id="graph-help-title" className="mt-2 text-2xl font-bold tracking-tight text-primary-950">Explore your career graph</h2>
              </div>
              <button
                autoFocus
                onClick={() => setHelpOpen(false)}
                className="shrink-0 rounded-full p-2 text-neutral-500 transition hover:bg-primary-50 hover:text-primary-800"
                aria-label="Close how to use guide"
              >
                <svg width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2"><line x1="3" y1="3" x2="15" y2="15"/><line x1="15" y1="3" x2="3" y2="15"/></svg>
              </button>
            </div>

            <div className="mt-5 grid gap-3 sm:grid-cols-2">
              <div className="rounded-xl border border-primary-100 bg-primary-50/70 p-4">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-white text-lg text-primary-700 shadow-sm">✦</div>
                <p className="mt-4 text-sm font-semibold text-primary-950">Expand branches</p>
                <p className="mt-1 text-sm leading-6 text-neutral-600">Click + or − to expand or collapse. Pulsing dots mean a branch is loading.</p>
              </div>
              <div className="rounded-xl border border-primary-100 bg-primary-50/70 p-4">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-white text-lg text-primary-700 shadow-sm">↔</div>
                <p className="mt-4 text-sm font-semibold text-primary-950">Move &amp; zoom</p>
                <p className="mt-1 text-sm leading-6 text-neutral-600">Drag the canvas to pan or a node to move it. Scroll or use the zoom controls.</p>
              </div>
              <div className="rounded-xl border border-primary-100 bg-primary-50/70 p-4">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-white text-lg text-primary-700">−</div>
                <p className="mt-4 text-sm font-semibold text-primary-950">Delete a node</p>
                <p className="mt-1 text-sm leading-6 text-neutral-600">Click its title, then Delete node. Review the warning; your name node is protected.</p>
              </div>
              <div className="rounded-xl border border-primary-100 bg-primary-50/70 p-4">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-white text-lg text-primary-700">?</div>
                <p className="mt-4 text-sm font-semibold text-primary-950">Start with AI Chat</p>
                <p className="mt-1 text-sm leading-6 text-neutral-600">Ask questions or add interests anytime. Review changes before applying.</p>
              </div>
              <div className="rounded-xl border border-primary-100 bg-primary-50/70 p-4 sm:col-span-2">
                <div className="inline-flex min-h-9 items-center rounded-lg border border-primary-300 bg-white px-3 py-2 text-sm font-semibold text-primary-800">Explain node</div>
                <p className="mt-4 text-sm font-semibold text-primary-950">Learn about a career path</p>
                <p className="mt-1 text-sm leading-6 text-neutral-600">Click an interest, industry, or role node, then click Explain node. AI Chat opens with an overview of the work, typical skills and qualifications, and suggested resources and practical steps for building them.</p>
                <p className="mt-2 text-sm leading-6 text-neutral-600">A spinner appears while the explanation is prepared. It is saved in your chat history without changing your tree. The button is disabled for your central name node.</p>
                <p className="mt-2 text-xs leading-5 text-neutral-500">Requirements vary by employer and location. Verify suggested learning resources and licensing requirements with official sources.</p>
              </div>
            </div>

            <p className="mt-4 text-sm leading-6 text-neutral-600">Jobs can only be found at the purple role level. Click a purple node, then Find openings. Hovering highlights the button; clicking enables it.</p>
            <p className="mt-2 text-xs leading-5 text-neutral-500">Career suggestions are starting points, not employment guarantees.</p>

            <div className="mt-6 flex flex-col gap-3 rounded-xl border border-primary-100 px-4 py-3 text-sm text-neutral-600 sm:flex-row sm:items-center sm:justify-between">
              <span><strong className="font-semibold text-primary-900">Tip:</strong> Reset view returns to the center.</span>
              <button onClick={() => setHelpOpen(false)} className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-primary-700">Got it</button>
            </div>
          </section>
        </div>
      )}

      {nodeToDelete && (
        <div className="fixed inset-0 z-60 flex items-center justify-center bg-neutral-950/45 px-4" onClick={() => !deleting && setDeleteNodeId(null)} role="presentation">
          <section
            className="w-full max-w-lg rounded-md border border-neutral-200 bg-white p-6 shadow-2xl"
            onClick={(event) => event.stopPropagation()}
            onKeyDown={(event) => {
              if (event.key !== "Tab") return;
              const buttons = Array.from(event.currentTarget.querySelectorAll<HTMLButtonElement>("button:not(:disabled)"));
              const currentIndex = buttons.findIndex((button) => button === document.activeElement);
              event.preventDefault();
              buttons[(currentIndex + (event.shiftKey ? -1 : 1) + buttons.length) % buttons.length]?.focus();
            }}
            role="alertdialog"
            aria-modal="true"
            aria-busy={deleting}
            aria-labelledby="delete-node-title"
            aria-describedby="delete-node-warning"
          >
            <h2 id="delete-node-title" className="text-xl font-semibold text-neutral-950">Delete this node?</h2>
            <p id="delete-node-warning" className="mt-3 leading-7 text-neutral-700">
              This permanently removes &quot;{canonicalizeCareerLabel(nodeToDelete.label)}&quot; and descendants exclusive to this branch from your saved graph. Descendants connected to another branch stay. Remaining nodes will redistribute evenly, including any nodes you moved manually. This cannot be undone.
              {" "}Shared nodes are linked copies of one saved node; deleting one removes all of its copies.
            </p>
            {deleteError && <p role="alert" className="mt-3 text-red-700">{deleteError}</p>}
            <div className="mt-6 flex justify-end gap-3">
              <button autoFocus type="button" onClick={() => setDeleteNodeId(null)} disabled={deleting} className="rounded-lg border border-neutral-300 px-4 py-2 font-semibold text-neutral-700 hover:bg-neutral-50 disabled:opacity-50">Cancel</button>
              <button type="button" onClick={confirmNodeDeletion} disabled={deleting || expandingNodeIds.length > 0} className="rounded-lg bg-red-700 px-4 py-2 font-semibold text-white hover:bg-red-800 disabled:opacity-50">{deleting ? "Deleting..." : "Delete node"}</button>
            </div>
          </section>
        </div>
      )}

      {resetConfirmOpen && (
        <div className="fixed inset-0 z-60 flex items-center justify-center bg-neutral-950/45 px-4" onClick={() => !resetting && setResetConfirmOpen(false)} role="presentation">
          <section className="w-full max-w-md rounded-md border border-neutral-200 bg-white p-6 shadow-2xl" onClick={(event) => event.stopPropagation()} role="alertdialog" aria-modal="true" aria-labelledby="reset-graph-title" aria-describedby="reset-graph-warning">
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-red-50 text-red-700" aria-hidden="true">
              <svg width="19" height="19" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><path d="M10 2.5 18 17H2L10 2.5Z"/><path d="M10 7v4M10 14h.01"/></svg>
            </div>
            <h2 id="reset-graph-title" className="mt-4 text-lg font-semibold text-neutral-950">Reset this career graph?</h2>
            <p id="reset-graph-warning" className="mt-2 text-sm leading-6 text-neutral-600">This clears the saved graph, explored branches, interests, and career-guide history for this session. Your account and profile remain unchanged. You can start a new map afterward.</p>
            {apiError && <p role="alert" className="mt-3 text-sm text-red-700">{apiError}</p>}
            <div className="mt-6 flex justify-end gap-2">
              <button type="button" onClick={() => setResetConfirmOpen(false)} disabled={resetting} className="rounded border border-neutral-300 px-4 py-2 text-sm font-semibold text-neutral-700 hover:bg-neutral-50 disabled:opacity-50">Cancel</button>
              <button type="button" onClick={confirmGraphReset} disabled={resetting} className="rounded bg-red-700 px-4 py-2 text-sm font-semibold text-white hover:bg-red-800 disabled:opacity-60">{resetting ? "Resetting..." : "Reset graph"}</button>
            </div>
          </section>
        </div>
      )}
    </div>
  );
}

export default function GraphPage() {
  return (
    <AuthProvider>
      <GraphContent />
    </AuthProvider>
  );
}
