import { create } from "zustand";
import type { ConversationRead, MessageRead } from "@/lib/types";

interface ChatState {
  conversations: ConversationRead[];
  setConversations: (conversations: ConversationRead[]) => void;
  upsertConversation: (conversation: ConversationRead) => void;

  messagesByConversation: Record<string, MessageRead[]>;
  setMessages: (conversationId: string, messages: MessageRead[]) => void;
  appendMessage: (conversationId: string, message: MessageRead) => void;
  updateMessage: (conversationId: string, messageId: string, patch: Partial<MessageRead>) => void;

  activeConversationId: string | null;
  setActiveConversationId: (id: string | null) => void;
}

export const useChatStore = create<ChatState>()((set) => ({
  conversations: [],
  setConversations: (conversations) => set({ conversations }),
  upsertConversation: (conversation) =>
    set((state) => {
      const idx = state.conversations.findIndex((c) => c.id === conversation.id);
      if (idx === -1) return { conversations: [conversation, ...state.conversations] };
      const next = [...state.conversations];
      next[idx] = conversation;
      return { conversations: next };
    }),

  messagesByConversation: {},
  setMessages: (conversationId, messages) =>
    set((state) => ({
      messagesByConversation: { ...state.messagesByConversation, [conversationId]: messages },
    })),
  appendMessage: (conversationId, message) =>
    set((state) => {
      const existing = state.messagesByConversation[conversationId] ?? [];
      return {
        messagesByConversation: {
          ...state.messagesByConversation,
          [conversationId]: [...existing, message],
        },
      };
    }),
  updateMessage: (conversationId, messageId, patch) =>
    set((state) => {
      const existing = state.messagesByConversation[conversationId] ?? [];
      return {
        messagesByConversation: {
          ...state.messagesByConversation,
          [conversationId]: existing.map((m) => (m.id === messageId ? { ...m, ...patch } : m)),
        },
      };
    }),

  activeConversationId: null,
  setActiveConversationId: (id) => set({ activeConversationId: id }),
}));
