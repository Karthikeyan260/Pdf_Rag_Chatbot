import { create } from "zustand";
import type { DocumentRead } from "@/lib/types";

interface DocumentState {
  documents: DocumentRead[];
  setDocuments: (documents: DocumentRead[]) => void;
  upsertDocument: (document: DocumentRead) => void;
  removeDocument: (id: string) => void;
  selectedDocumentIds: string[];
  setSelectedDocumentIds: (ids: string[]) => void;
  toggleSelectedDocumentId: (id: string) => void;
}

export const useDocumentStore = create<DocumentState>()((set, get) => ({
  documents: [],
  setDocuments: (documents) => set({ documents }),
  upsertDocument: (document) =>
    set((state) => {
      const idx = state.documents.findIndex((d) => d.id === document.id);
      if (idx === -1) {
        return { documents: [document, ...state.documents] };
      }
      const next = [...state.documents];
      next[idx] = document;
      return { documents: next };
    }),
  removeDocument: (id) =>
    set((state) => ({ documents: state.documents.filter((d) => d.id !== id) })),
  selectedDocumentIds: [],
  setSelectedDocumentIds: (ids) => set({ selectedDocumentIds: ids }),
  toggleSelectedDocumentId: (id) => {
    const current = get().selectedDocumentIds;
    if (current.includes(id)) {
      set({ selectedDocumentIds: current.filter((d) => d !== id) });
    } else {
      set({ selectedDocumentIds: [...current, id] });
    }
  },
}));
