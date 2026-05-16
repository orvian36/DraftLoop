import { create } from "zustand";
import type { CaseFactSummary, Citation, Fact } from "../types/draft";
import { ulid } from "../utils/ulid";

export interface EditorState {
  draftId: string;
  matterId: string;
  baseline: CaseFactSummary | null;
  current: CaseFactSummary | null;
  dirty: Set<string>;
  factTimers: Map<string, number>;
  reset: (matterId: string, draftId: string, summary: CaseFactSummary) => void;
  beginEdit: (sentenceId: string) => void;
  updateFactText: (slot: keyof CaseFactSummary, sentenceId: string, text: string) => void;
  addCitation: (slot: keyof CaseFactSummary, sentenceId: string, citation: Citation) => void;
  removeCitation: (slot: keyof CaseFactSummary, sentenceId: string, chunkId: string) => void;
  markUnsupported: (slot: keyof CaseFactSummary, sentenceId: string) => void;
  deleteFact: (slot: keyof CaseFactSummary, sentenceId: string) => void;
  addFact: (slot: keyof CaseFactSummary, fact: Fact) => void;
}

function mutateFact(
  s: EditorState,
  slot: keyof CaseFactSummary,
  sentenceId: string,
  mut: (f: Fact) => Fact,
): Partial<EditorState> {
  if (!s.current) return s;
  const next = structuredClone(s.current);
  next[slot] = next[slot].map((f) => (f.sentence_id === sentenceId ? mut(f) : f));
  const dirty = new Set(s.dirty);
  dirty.add(sentenceId);
  return { current: next, dirty };
}

export const useEditorStore = create<EditorState>((set) => ({
  draftId: "",
  matterId: "",
  baseline: null,
  current: null,
  dirty: new Set(),
  factTimers: new Map(),

  reset(matterId, draftId, summary) {
    set({
      matterId,
      draftId,
      baseline: structuredClone(summary),
      current: structuredClone(summary),
      dirty: new Set(),
      factTimers: new Map(),
    });
  },

  beginEdit(sentenceId) {
    set((s) => {
      if (!s.factTimers.has(sentenceId)) {
        const map = new Map(s.factTimers);
        map.set(sentenceId, Date.now());
        return { factTimers: map };
      }
      return s;
    });
  },

  updateFactText(slot, sentenceId, text) {
    set((s) => mutateFact(s, slot, sentenceId, (f) => ({ ...f, text })));
  },

  addCitation(slot, sentenceId, citation) {
    set((s) =>
      mutateFact(s, slot, sentenceId, (f) => ({
        ...f,
        citations: [
          ...f.citations.filter((c) => c.chunk_id !== citation.chunk_id),
          citation,
        ],
      })),
    );
  },

  removeCitation(slot, sentenceId, chunkId) {
    set((s) =>
      mutateFact(s, slot, sentenceId, (f) => ({
        ...f,
        citations: f.citations.filter((c) => c.chunk_id !== chunkId),
      })),
    );
  },

  markUnsupported(slot, sentenceId) {
    set((s) =>
      mutateFact(s, slot, sentenceId, (f) => ({
        ...f,
        text: "UNSUPPORTED",
        citations: [],
        confidence: "low",
      })),
    );
  },

  deleteFact(slot, sentenceId) {
    set((s) => {
      if (!s.current) return s;
      const next = structuredClone(s.current);
      next[slot] = next[slot].filter((f) => f.sentence_id !== sentenceId);
      const dirty = new Set(s.dirty);
      dirty.add(sentenceId);
      return { current: next, dirty };
    });
  },

  addFact(slot, fact) {
    set((s) => {
      if (!s.current) return s;
      const next = structuredClone(s.current);
      const id = fact.sentence_id || `s_${ulid().slice(-8)}`;
      next[slot] = [...next[slot], { ...fact, sentence_id: id }];
      const dirty = new Set(s.dirty);
      dirty.add(id);
      return { current: next, dirty };
    });
  },
}));
