/* ──────────────────────────────────────────────────────────────
 *  Zustand stores — global state for chat + UI
 * ────────────────────────────────────────────────────────────── */

import { create } from "zustand";
import type { Patient, ChatMessage, Citation, AgentStatus } from "@/lib/types";

// ── Chat Store ──────────────────────────────────────────────
interface ChatState {
  currentPatient: Patient | null;
  setCurrentPatient: (p: Patient) => void;

  messages: ChatMessage[];
  addMessage: (msg: ChatMessage) => void;
  setMessages: (msgs: ChatMessage[] | ((prev: ChatMessage[]) => ChatMessage[])) => void;

  citations: Citation[];
  setCitations: (c: Citation[]) => void;

  agentStatus: AgentStatus;
  setAgentStatus: (s: AgentStatus) => void;

  sidebarOpen: boolean;
  setSidebarOpen: (open: boolean) => void;

  reset: () => void;
}

const initialChatState = {
  currentPatient: null,
  messages: [] as ChatMessage[],
  citations: [] as Citation[],
  agentStatus: "idle" as AgentStatus,
  sidebarOpen: false,
};

export const useChatStore = create<ChatState>((set) => ({
  ...initialChatState,

  setCurrentPatient: (p) => set({ currentPatient: p }),

  addMessage: (msg) => set((s) => ({ messages: [...s.messages, msg] })),
  setMessages: (msgs) =>
    set((s) => ({
      messages: typeof msgs === "function" ? msgs(s.messages) : msgs,
    })),

  setCitations: (c) => set({ citations: c }),

  setAgentStatus: (status) => set({ agentStatus: status }),

  setSidebarOpen: (open) => set({ sidebarOpen: open }),

  reset: () => set(initialChatState),
}));

// ── UI Store ────────────────────────────────────────────────
interface UIState {
  backendOnline: boolean;
  setBackendOnline: (online: boolean) => void;
}

export const useUIStore = create<UIState>((set) => ({
  backendOnline: false,
  setBackendOnline: (online) => set({ backendOnline: online }),
}));
