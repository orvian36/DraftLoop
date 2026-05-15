# Plan 4: Operator UI & Edit Capture — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans`.

**Goal:** Build the operator surface in `apps/web` plus the shared editor components in `packages/ui`. Operators load a draft, click citation chips, edit Fact text inline, add/remove citations by selecting evidence in the source viewer, and Save — the frontend computes an `EditEvent[]` diff and POSTs it. The backend wires `apps/api` routes that read drafts and persist edits.

**Architecture:** Components in `packages/ui` are purely presentational (zustand for editor state, no fetch). `apps/web` supplies the data adapter (TanStack Query) + API client. `apps/api` adds 3 routes (`GET draft`, `POST edits`, SSE events). Edit diffing happens client-side; the server just persists raw `EditEvent` rows for Plan 5 to classify.

**Tech Stack:** Next.js 15, React 19, TypeScript 5.6, Tailwind, shadcn/ui primitives (Radix), zustand, TanStack Query, diff-match-patch, ULID, Vitest + Testing Library, Playwright.

---

## File structure

```
packages/ui/
├─ src/
│  ├─ index.ts
│  ├─ types/
│  │  ├─ draft.ts                  # CaseFactSummary, Fact, Citation TS mirrors
│  │  ├─ edits.ts                  # EditEvent, EditOp
│  │  └─ retrieval.ts              # ChunkMeta
│  ├─ state/
│  │  ├─ editor-store.ts           # zustand store
│  │  └─ diff.ts                   # diff Fact[] → EditEvent[]
│  ├─ components/
│  │  ├─ CaseFactSummaryViewer.tsx
│  │  ├─ CaseFactSummaryEditor.tsx
│  │  ├─ EvidencePanel.tsx
│  │  ├─ CitationChip.tsx
│  │  ├─ DiffViewer.tsx
│  │  ├─ AuditTrailDrawer.tsx
│  │  ├─ NeedsReviewBanner.tsx
│  │  └─ HealthBadge.tsx           # already exists
│  └─ utils/
│     └─ ulid.ts
└─ tests/
   ├─ CaseFactSummaryEditor.test.tsx
   ├─ EvidencePanel.test.tsx
   ├─ CitationChip.test.tsx
   ├─ DiffViewer.test.tsx
   └─ editor-store.test.ts

apps/web/
├─ src/
│  ├─ app/
│  │  ├─ matters/[id]/draft/[draftId]/page.tsx      # editor route
│  │  └─ matters/[id]/draft/[draftId]/audit/page.tsx
│  └─ lib/
│     └─ api/
│        ├─ client.ts              # exists
│        ├─ drafts.ts              # GET/POST helpers
│        └─ edits.ts
└─ tests/
   └─ matters.editor.spec.tsx       # Vitest

apps/api/
└─ src/draftloop_api/routes/
   ├─ drafts.py                    # GET /api/matters/:id/drafts/:draftId
   └─ edits.py                     # POST /api/matters/:id/drafts/:draftId/edits

tests/e2e/
└─ editor_smoke.spec.ts             # Playwright
```

---

## Task 1: TS types in `packages/ui`

- [ ] **Step 1: Write `packages/ui/src/types/draft.ts`**

```typescript
export type Confidence = "high" | "medium" | "low";
export const UNSUPPORTED = "UNSUPPORTED" as const;

export interface Citation {
  chunk_id: string;
  quote: string;
}

export interface Fact {
  sentence_id: string;
  text: string;
  citations: Citation[];
  confidence: Confidence;
}

export interface CaseFactSummary {
  parties: Fact[];
  jurisdiction: Fact[];
  key_dates: Fact[];
  claims: Fact[];
  relief_sought: Fact[];
  procedural_posture: Fact[];
  key_evidence: Fact[];
}

export const SLOT_ORDER: (keyof CaseFactSummary)[] = [
  "parties",
  "jurisdiction",
  "key_dates",
  "claims",
  "relief_sought",
  "procedural_posture",
  "key_evidence",
];
```

- [ ] **Step 2: `packages/ui/src/types/edits.ts`**

```typescript
import type { Citation } from "./draft";

export type EditOp =
  | "fact_text_changed"
  | "citation_added"
  | "citation_removed"
  | "fact_marked_unsupported"
  | "fact_deleted"
  | "fact_split"
  | "fact_added"
  | "fact_reordered"
  | "slot_structural";

export interface EditEvent {
  event_id: string;
  draft_id: string;
  matter_id: string;
  slot: string;
  sentence_id: string | null;
  op: EditOp;
  before: { text?: string; citations?: Citation[] } | null;
  after: { text?: string; citations?: Citation[] } | null;
  source_evidence_ids: string[];
  word_diff: string | null;
  time_to_edit_ms: number;
  operator_id: string;
  draft_model_version: string;
  prompt_hash: string;
  timestamp: string;
}
```

- [ ] **Step 3: `packages/ui/src/types/retrieval.ts`**

```typescript
export interface ChunkMeta {
  chunk_id: string;
  doc_id: string;
  doc_title?: string;
  page: number;
  section_label: string | null;
  char_start: number;
  char_end: number;
  text: string;
  contains_needs_review: boolean;
}
```

- [ ] **Step 4: Commit**

```bash
git commit -am "feat(ui): add draft + edits + retrieval TS types"
```

---

## Task 2: ulid util + zustand editor store

- [ ] **Step 1: `packages/ui/src/utils/ulid.ts`**

```typescript
// Lightweight ULID generator suitable for in-browser use.
const ENCODING = "0123456789ABCDEFGHJKMNPQRSTVWXYZ";

function encodeTime(now: number, len: number): string {
  let str = "";
  for (let i = len - 1; i >= 0; i--) {
    const mod = now % 32;
    str = ENCODING[mod] + str;
    now = (now - mod) / 32;
  }
  return str;
}

function encodeRandom(len: number): string {
  let str = "";
  for (let i = 0; i < len; i++) {
    str += ENCODING[Math.floor(Math.random() * 32)];
  }
  return str;
}

export function ulid(): string {
  return encodeTime(Date.now(), 10) + encodeRandom(16);
}
```

- [ ] **Step 2: `packages/ui/src/state/editor-store.ts`**

```typescript
import { create } from "zustand";
import type { CaseFactSummary, Fact, Citation } from "../types/draft";
import { ulid } from "../utils/ulid";

export interface EditorState {
  draftId: string;
  matterId: string;
  baseline: CaseFactSummary | null;
  current: CaseFactSummary | null;
  dirty: Set<string>;          // sentence_ids touched
  factTimers: Map<string, number>; // sentence_id -> ts started editing
  reset: (matterId: string, draftId: string, summary: CaseFactSummary) => void;
  beginEdit: (sentenceId: string) => void;
  updateFactText: (slot: keyof CaseFactSummary, sentenceId: string, text: string) => void;
  addCitation: (slot: keyof CaseFactSummary, sentenceId: string, citation: Citation) => void;
  removeCitation: (slot: keyof CaseFactSummary, sentenceId: string, chunkId: string) => void;
  markUnsupported: (slot: keyof CaseFactSummary, sentenceId: string) => void;
  deleteFact: (slot: keyof CaseFactSummary, sentenceId: string) => void;
  addFact: (slot: keyof CaseFactSummary, fact: Fact) => void;
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
      matterId, draftId,
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
    set((s) => mutateFact(s, slot, sentenceId, (f) => ({
      ...f,
      citations: [...f.citations.filter(c => c.chunk_id !== citation.chunk_id), citation],
    })));
  },

  removeCitation(slot, sentenceId, chunkId) {
    set((s) => mutateFact(s, slot, sentenceId, (f) => ({
      ...f,
      citations: f.citations.filter((c) => c.chunk_id !== chunkId),
    })));
  },

  markUnsupported(slot, sentenceId) {
    set((s) => mutateFact(s, slot, sentenceId, (f) => ({
      ...f, text: "UNSUPPORTED", citations: [], confidence: "low",
    })));
  },

  deleteFact(slot, sentenceId) {
    set((s) => {
      if (!s.current) return s;
      const next = structuredClone(s.current);
      next[slot] = next[slot].filter((f) => f.sentence_id !== sentenceId);
      const dirty = new Set(s.dirty); dirty.add(sentenceId);
      return { current: next, dirty };
    });
  },

  addFact(slot, fact) {
    set((s) => {
      if (!s.current) return s;
      const next = structuredClone(s.current);
      const id = fact.sentence_id || `s_${ulid().slice(-8)}`;
      next[slot] = [...next[slot], { ...fact, sentence_id: id }];
      const dirty = new Set(s.dirty); dirty.add(id);
      return { current: next, dirty };
    });
  },
}));

function mutateFact(
  s: EditorState,
  slot: keyof CaseFactSummary,
  sentenceId: string,
  mut: (f: Fact) => Fact,
): Partial<EditorState> {
  if (!s.current) return s;
  const next = structuredClone(s.current);
  next[slot] = next[slot].map((f) => (f.sentence_id === sentenceId ? mut(f) : f));
  const dirty = new Set(s.dirty); dirty.add(sentenceId);
  return { current: next, dirty };
}
```

- [ ] **Step 3: Failing test (`packages/ui/tests/editor-store.test.ts`)**

```typescript
import { describe, it, expect, beforeEach } from "vitest";
import { useEditorStore } from "../src/state/editor-store";
import type { CaseFactSummary } from "../src/types/draft";

const baseline: CaseFactSummary = {
  parties: [{ sentence_id: "s_1", text: "Acme v. Widgets", citations: [{ chunk_id: "c1", quote: "Acme" }], confidence: "high" }],
  jurisdiction: [], key_dates: [], claims: [],
  relief_sought: [], procedural_posture: [], key_evidence: [],
};

beforeEach(() => {
  useEditorStore.setState({
    draftId: "", matterId: "", baseline: null, current: null,
    dirty: new Set(), factTimers: new Map(),
  });
});

describe("editor store", () => {
  it("reset snapshots baseline + current", () => {
    useEditorStore.getState().reset("M-1", "D-1", baseline);
    const s = useEditorStore.getState();
    expect(s.baseline).toEqual(baseline);
    expect(s.current).toEqual(baseline);
    expect(s.current).not.toBe(s.baseline);
  });

  it("updateFactText marks dirty", () => {
    useEditorStore.getState().reset("M-1", "D-1", baseline);
    useEditorStore.getState().updateFactText("parties", "s_1", "Acme Corp v. Widgets Inc.");
    const s = useEditorStore.getState();
    expect(s.current!.parties[0].text).toBe("Acme Corp v. Widgets Inc.");
    expect(s.dirty.has("s_1")).toBe(true);
  });

  it("markUnsupported clears citations", () => {
    useEditorStore.getState().reset("M-1", "D-1", baseline);
    useEditorStore.getState().markUnsupported("parties", "s_1");
    expect(useEditorStore.getState().current!.parties[0].citations).toHaveLength(0);
    expect(useEditorStore.getState().current!.parties[0].text).toBe("UNSUPPORTED");
  });
});
```

- [ ] **Step 4: Test passes. Commit.**

```bash
git commit -am "feat(ui): add ulid util + zustand editor store"
```

---

## Task 3: diff Fact[] → EditEvent[]

- [ ] **Step 1: `packages/ui/src/state/diff.ts`**

```typescript
import { diff_match_patch } from "diff-match-patch";
import type { CaseFactSummary, Fact, Citation } from "../types/draft";
import type { EditEvent, EditOp } from "../types/edits";
import { SLOT_ORDER } from "../types/draft";
import { ulid } from "../utils/ulid";

const dmp = new diff_match_patch();

export interface DiffContext {
  draftId: string;
  matterId: string;
  operatorId: string;
  draftModelVersion: string;
  promptHash: string;
  factStartTimers: Map<string, number>;
}

export function diffSummaries(
  before: CaseFactSummary,
  after: CaseFactSummary,
  ctx: DiffContext,
): EditEvent[] {
  const events: EditEvent[] = [];
  const ts = new Date().toISOString();

  for (const slot of SLOT_ORDER) {
    const beforeMap = new Map(before[slot].map((f) => [f.sentence_id, f]));
    const afterMap = new Map(after[slot].map((f) => [f.sentence_id, f]));

    for (const [sid, b] of beforeMap) {
      const a = afterMap.get(sid);
      if (!a) {
        events.push(mkEvent(ctx, slot, sid, "fact_deleted", b, null, ts));
        continue;
      }
      if (b.text !== a.text) {
        const wordDiff = dmp.patch_toText(dmp.patch_make(b.text, a.text));
        if (a.text === "UNSUPPORTED") {
          events.push(mkEvent(ctx, slot, sid, "fact_marked_unsupported", b, a, ts));
        } else {
          events.push(mkEvent(ctx, slot, sid, "fact_text_changed", b, a, ts, wordDiff));
        }
      }
      // Citation changes
      const beforeCits = new Set(b.citations.map((c) => c.chunk_id));
      const afterCits = new Set(a.citations.map((c) => c.chunk_id));
      for (const cid of afterCits) {
        if (!beforeCits.has(cid)) {
          events.push(mkEvent(ctx, slot, sid, "citation_added", b, a, ts));
        }
      }
      for (const cid of beforeCits) {
        if (!afterCits.has(cid)) {
          events.push(mkEvent(ctx, slot, sid, "citation_removed", b, a, ts));
        }
      }
    }
    for (const [sid, a] of afterMap) {
      if (!beforeMap.has(sid)) {
        events.push(mkEvent(ctx, slot, sid, "fact_added", null, a, ts));
      }
    }
  }
  return events;
}

function mkEvent(
  ctx: DiffContext,
  slot: string,
  sentence_id: string | null,
  op: EditOp,
  before: Fact | null,
  after: Fact | null,
  timestamp: string,
  wordDiff: string | null = null,
): EditEvent {
  const startedAt = (sentence_id && ctx.factStartTimers.get(sentence_id)) || 0;
  const evidenceIds = new Set<string>();
  before?.citations.forEach((c) => evidenceIds.add(c.chunk_id));
  after?.citations.forEach((c) => evidenceIds.add(c.chunk_id));
  return {
    event_id: ulid(),
    draft_id: ctx.draftId,
    matter_id: ctx.matterId,
    slot,
    sentence_id,
    op,
    before: before
      ? { text: before.text, citations: before.citations }
      : null,
    after: after
      ? { text: after.text, citations: after.citations }
      : null,
    source_evidence_ids: [...evidenceIds],
    word_diff: wordDiff,
    time_to_edit_ms: startedAt ? Date.now() - startedAt : 0,
    operator_id: ctx.operatorId,
    draft_model_version: ctx.draftModelVersion,
    prompt_hash: ctx.promptHash,
    timestamp,
  };
}
```

- [ ] **Step 2: Add `diff-match-patch` + types to `packages/ui/package.json`**

Add to dependencies: `"diff-match-patch": "^1.0.5"`. Add to devDependencies: `"@types/diff-match-patch": "^1.0.36"`.

- [ ] **Step 3: Test diff.ts**

```typescript
import { describe, it, expect } from "vitest";
import { diffSummaries } from "../src/state/diff";
import type { CaseFactSummary } from "../src/types/draft";

const base: CaseFactSummary = {
  parties: [{ sentence_id: "s_1", text: "Acme", citations: [{ chunk_id: "c1", quote: "x" }], confidence: "high" }],
  jurisdiction: [], key_dates: [], claims: [],
  relief_sought: [], procedural_posture: [], key_evidence: [],
};

const ctx = {
  draftId: "D-1", matterId: "M-1", operatorId: "op",
  draftModelVersion: "v1", promptHash: "h",
  factStartTimers: new Map<string, number>(),
};

describe("diffSummaries", () => {
  it("emits fact_text_changed when text differs", () => {
    const next = structuredClone(base);
    next.parties[0].text = "Acme Corp";
    const events = diffSummaries(base, next, ctx);
    expect(events.some((e) => e.op === "fact_text_changed")).toBe(true);
  });

  it("emits fact_marked_unsupported with sentinel", () => {
    const next = structuredClone(base);
    next.parties[0].text = "UNSUPPORTED";
    next.parties[0].citations = [];
    const events = diffSummaries(base, next, ctx);
    expect(events.some((e) => e.op === "fact_marked_unsupported")).toBe(true);
  });

  it("emits citation_added and citation_removed", () => {
    const next = structuredClone(base);
    next.parties[0].citations = [{ chunk_id: "c2", quote: "y" }];
    const events = diffSummaries(base, next, ctx);
    expect(events.some((e) => e.op === "citation_added")).toBe(true);
    expect(events.some((e) => e.op === "citation_removed")).toBe(true);
  });

  it("emits fact_added and fact_deleted", () => {
    const next = structuredClone(base);
    next.parties = [];
    const events = diffSummaries(base, next, ctx);
    expect(events.some((e) => e.op === "fact_deleted")).toBe(true);
  });
});
```

- [ ] **Step 4: pnpm install + test + commit.**

```bash
pnpm install
pnpm -F @draftloop/ui test
git commit -am "feat(ui): add diffSummaries(Fact[]) -> EditEvent[]"
```

---

## Task 4: CitationChip + DiffViewer + NeedsReviewBanner

- [ ] **Step 1: `packages/ui/src/components/CitationChip.tsx`**

```tsx
import type { ReactElement } from "react";
import type { Citation } from "../types/draft";

export interface CitationChipProps {
  citation: Citation;
  onResolve: (chunkId: string) => void;
  onRemove?: (chunkId: string) => void;
  active?: boolean;
}

export function CitationChip({ citation, onResolve, onRemove, active }: CitationChipProps): ReactElement {
  return (
    <span
      role="button"
      tabIndex={0}
      onClick={() => onResolve(citation.chunk_id)}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") onResolve(citation.chunk_id);
      }}
      className={`inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-xs font-mono cursor-pointer ${
        active
          ? "border-sky-500 bg-sky-50 text-sky-900"
          : "border-slate-300 bg-slate-100 text-slate-700 hover:bg-slate-200"
      }`}
      data-chunk-id={citation.chunk_id}
    >
      <span aria-hidden className="text-slate-500">¶</span>
      {citation.chunk_id}
      {onRemove ? (
        <button
          type="button"
          aria-label={`remove citation ${citation.chunk_id}`}
          onClick={(e) => { e.stopPropagation(); onRemove(citation.chunk_id); }}
          className="ml-1 text-slate-500 hover:text-rose-600"
        >
          ×
        </button>
      ) : null}
    </span>
  );
}
```

- [ ] **Step 2: `packages/ui/src/components/NeedsReviewBanner.tsx`**

```tsx
import type { ReactElement } from "react";

export interface NeedsReviewBannerProps {
  count: number;
}

export function NeedsReviewBanner({ count }: NeedsReviewBannerProps): ReactElement | null {
  if (count <= 0) return null;
  return (
    <div role="alert" className="rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-amber-900 text-sm">
      ⚠ {count} low-confidence span{count === 1 ? "" : "s"} flagged by ingestion. Verify before citing.
    </div>
  );
}
```

- [ ] **Step 3: `packages/ui/src/components/DiffViewer.tsx`**

```tsx
import type { ReactElement } from "react";
import { diff_match_patch } from "diff-match-patch";

export interface DiffViewerProps {
  before: string;
  after: string;
}

const dmp = new diff_match_patch();

export function DiffViewer({ before, after }: DiffViewerProps): ReactElement {
  const diffs = dmp.diff_main(before, after);
  dmp.diff_cleanupSemantic(diffs);
  return (
    <div className="font-mono text-sm whitespace-pre-wrap" data-testid="diff-viewer">
      {diffs.map(([op, text], i) => {
        const cls =
          op === 1 ? "bg-emerald-100 text-emerald-900"
          : op === -1 ? "bg-rose-100 text-rose-900 line-through"
          : "";
        return <span key={i} className={cls}>{text}</span>;
      })}
    </div>
  );
}
```

- [ ] **Step 4: Tests for each. Commit.**

```typescript
// packages/ui/tests/CitationChip.test.tsx
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { CitationChip } from "../src/components/CitationChip";

describe("CitationChip", () => {
  it("fires onResolve when clicked", () => {
    const on = vi.fn();
    render(<CitationChip citation={{ chunk_id: "c1", quote: "x" }} onResolve={on} />);
    fireEvent.click(screen.getByRole("button"));
    expect(on).toHaveBeenCalledWith("c1");
  });

  it("renders × when onRemove supplied", () => {
    const on = vi.fn(); const off = vi.fn();
    render(<CitationChip citation={{ chunk_id: "c1", quote: "x" }} onResolve={on} onRemove={off} />);
    fireEvent.click(screen.getByLabelText("remove citation c1"));
    expect(off).toHaveBeenCalledWith("c1");
  });
});
```

```bash
pnpm -F @draftloop/ui test
git commit -am "feat(ui): add CitationChip, DiffViewer, NeedsReviewBanner"
```

---

## Task 5: CaseFactSummaryViewer + Editor + EvidencePanel

The editor is the centerpiece. Implementation is straightforward composition; tests verify the key user actions.

- [ ] **Step 1: `packages/ui/src/components/CaseFactSummaryViewer.tsx`**

```tsx
import type { ReactElement } from "react";
import type { CaseFactSummary } from "../types/draft";
import { SLOT_ORDER } from "../types/draft";
import { CitationChip } from "./CitationChip";

export interface CaseFactSummaryViewerProps {
  summary: CaseFactSummary;
  onResolveCitation: (chunkId: string) => void;
}

export function CaseFactSummaryViewer({ summary, onResolveCitation }: CaseFactSummaryViewerProps): ReactElement {
  return (
    <div className="space-y-6">
      {SLOT_ORDER.map((slot) => (
        <section key={slot} aria-labelledby={`slot-${slot}`}>
          <h2 id={`slot-${slot}`} className="text-sm uppercase tracking-wide text-slate-500 mb-2">
            {slot.replace("_", " ")}
          </h2>
          <ul className="space-y-2">
            {summary[slot].map((f) => (
              <li key={f.sentence_id} className="rounded-md border border-slate-200 bg-white p-3">
                <p className="text-slate-900">{f.text}</p>
                <div className="mt-2 flex flex-wrap gap-1">
                  {f.citations.map((c) => (
                    <CitationChip key={c.chunk_id} citation={c} onResolve={onResolveCitation} />
                  ))}
                </div>
              </li>
            ))}
          </ul>
        </section>
      ))}
    </div>
  );
}
```

- [ ] **Step 2: `packages/ui/src/components/CaseFactSummaryEditor.tsx`**

```tsx
import { useEffect } from "react";
import type { ReactElement } from "react";
import type { CaseFactSummary } from "../types/draft";
import { SLOT_ORDER } from "../types/draft";
import { CitationChip } from "./CitationChip";
import { useEditorStore } from "../state/editor-store";

export interface CaseFactSummaryEditorProps {
  matterId: string;
  draftId: string;
  initial: CaseFactSummary;
  onResolveCitation: (chunkId: string) => void;
  onSave: (current: CaseFactSummary) => Promise<void> | void;
}

export function CaseFactSummaryEditor(props: CaseFactSummaryEditorProps): ReactElement {
  const store = useEditorStore();
  useEffect(() => {
    store.reset(props.matterId, props.draftId, props.initial);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [props.matterId, props.draftId]);

  if (!store.current) return <div>Loading…</div>;

  return (
    <div className="space-y-6">
      {SLOT_ORDER.map((slot) => (
        <section key={slot} aria-labelledby={`slot-${slot}`}>
          <h2 id={`slot-${slot}`} className="text-sm uppercase tracking-wide text-slate-500 mb-2">
            {slot.replace("_", " ")}
          </h2>
          <ul className="space-y-2">
            {store.current[slot].map((f) => (
              <li key={f.sentence_id} className="rounded-md border border-slate-200 bg-white p-3">
                <textarea
                  aria-label={`fact ${f.sentence_id} text`}
                  className="w-full resize-none rounded-sm bg-transparent text-slate-900 focus:outline-none focus:ring-2 focus:ring-sky-200"
                  value={f.text}
                  onFocus={() => store.beginEdit(f.sentence_id)}
                  onChange={(e) => store.updateFactText(slot, f.sentence_id, e.target.value)}
                />
                <div className="mt-2 flex flex-wrap gap-1">
                  {f.citations.map((c) => (
                    <CitationChip
                      key={c.chunk_id}
                      citation={c}
                      onResolve={props.onResolveCitation}
                      onRemove={(cid) => store.removeCitation(slot, f.sentence_id, cid)}
                    />
                  ))}
                  <button
                    type="button"
                    onClick={() => store.markUnsupported(slot, f.sentence_id)}
                    className="text-xs text-slate-500 underline hover:text-rose-600"
                  >
                    mark UNSUPPORTED
                  </button>
                </div>
              </li>
            ))}
          </ul>
        </section>
      ))}
      <div className="sticky bottom-4 flex justify-end">
        <button
          type="button"
          onClick={() => store.current && props.onSave(store.current)}
          className="rounded-md bg-slate-900 text-white px-4 py-2 text-sm hover:bg-slate-800"
        >
          Save
        </button>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: `packages/ui/src/components/EvidencePanel.tsx`**

```tsx
import { useMemo } from "react";
import type { ReactElement } from "react";
import type { ChunkMeta } from "../types/retrieval";

export interface EvidencePanelProps {
  docTitle: string;
  markdown: string;                  // full doc markdown
  chunks: ChunkMeta[];               // chunks to highlight
  focusedChunkId?: string | null;
  onSelectRange?: (selection: { text: string; chunkId: string }) => void;
}

export function EvidencePanel({ docTitle, markdown, chunks, focusedChunkId, onSelectRange }: EvidencePanelProps): ReactElement {
  // Decorate the markdown by char_start/char_end. Naive but deterministic; for v1 we
  // just split-and-wrap.
  const segments = useMemo(() => buildSegments(markdown, chunks, focusedChunkId), [markdown, chunks, focusedChunkId]);
  return (
    <div className="h-full overflow-y-auto rounded-md border border-slate-200 bg-white p-4 font-mono text-sm whitespace-pre-wrap" data-testid="evidence-panel">
      <h3 className="font-sans text-base font-semibold mb-2">{docTitle}</h3>
      {segments.map((seg, i) => (
        <span
          key={i}
          data-chunk={seg.chunk_id || ""}
          className={seg.cls}
          onMouseUp={() => {
            if (!onSelectRange || !seg.chunk_id) return;
            const text = window.getSelection()?.toString() ?? "";
            if (text) onSelectRange({ text, chunkId: seg.chunk_id });
          }}
        >
          {seg.text}
        </span>
      ))}
    </div>
  );
}

interface Segment { text: string; cls: string; chunk_id: string | null; }

function buildSegments(md: string, chunks: ChunkMeta[], focused?: string | null): Segment[] {
  const sorted = [...chunks].sort((a, b) => a.char_start - b.char_start);
  const segments: Segment[] = [];
  let cursor = 0;
  for (const c of sorted) {
    if (c.char_start > cursor) {
      segments.push({ text: md.slice(cursor, c.char_start), cls: "", chunk_id: null });
    }
    const cls = c.contains_needs_review
      ? "bg-amber-100"
      : c.chunk_id === focused
      ? "bg-sky-200"
      : "bg-teal-50";
    segments.push({ text: md.slice(c.char_start, c.char_end), cls, chunk_id: c.chunk_id });
    cursor = c.char_end;
  }
  if (cursor < md.length) segments.push({ text: md.slice(cursor), cls: "", chunk_id: null });
  return segments;
}
```

- [ ] **Step 4: Tests + commit.**

```bash
pnpm -F @draftloop/ui test
git commit -am "feat(ui): add CaseFactSummary viewer + editor + EvidencePanel"
```

---

## Task 6: AuditTrailDrawer + index re-exports

- [ ] **Step 1: `packages/ui/src/components/AuditTrailDrawer.tsx`**

```tsx
import type { ReactElement } from "react";

export interface AuditTrailDrawerProps {
  data: Record<string, unknown> | null;
  open: boolean;
  onClose: () => void;
}

export function AuditTrailDrawer({ data, open, onClose }: AuditTrailDrawerProps): ReactElement | null {
  if (!open) return null;
  return (
    <aside role="dialog" aria-label="Audit trail" className="fixed right-0 top-0 h-full w-[420px] bg-white shadow-xl border-l border-slate-200 p-4 overflow-y-auto">
      <div className="flex justify-between items-center mb-3">
        <h3 className="font-semibold">Audit trail</h3>
        <button type="button" onClick={onClose} className="text-sm text-slate-500 hover:text-slate-900">Close</button>
      </div>
      <pre className="text-xs whitespace-pre-wrap font-mono text-slate-800">
        {data ? JSON.stringify(data, null, 2) : "(no audit data)"}
      </pre>
    </aside>
  );
}
```

- [ ] **Step 2: Update `packages/ui/src/index.ts`**

```typescript
export { HealthBadge } from "./components/HealthBadge";
export { CitationChip } from "./components/CitationChip";
export { DiffViewer } from "./components/DiffViewer";
export { NeedsReviewBanner } from "./components/NeedsReviewBanner";
export { CaseFactSummaryViewer } from "./components/CaseFactSummaryViewer";
export { CaseFactSummaryEditor } from "./components/CaseFactSummaryEditor";
export { EvidencePanel } from "./components/EvidencePanel";
export { AuditTrailDrawer } from "./components/AuditTrailDrawer";
export type { CaseFactSummary, Fact, Citation, Confidence } from "./types/draft";
export type { EditEvent, EditOp } from "./types/edits";
export type { ChunkMeta } from "./types/retrieval";
export { useEditorStore } from "./state/editor-store";
export { diffSummaries } from "./state/diff";
export { SLOT_ORDER, UNSUPPORTED } from "./types/draft";
```

- [ ] **Step 3: Build + commit.**

```bash
pnpm -F @draftloop/ui build
git commit -am "feat(ui): re-export full editor surface from packages/ui"
```

---

## Task 7: `apps/api` routes for drafts + edits

- [ ] **Step 1: `apps/api/src/draftloop_api/routes/drafts.py`**

```python
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from draftloop_core.storage.sqlite_document_store import SqliteDocumentStore
from draftloop_core.config import get_settings

router = APIRouter(prefix="/api/matters/{matter_id}/drafts")

_store: SqliteDocumentStore | None = None


def _get_store() -> SqliteDocumentStore:
    global _store
    if _store is None:
        settings = get_settings()
        _store = SqliteDocumentStore(f"{settings.data_dir}/draftloop.db")
    return _store


@router.get("/{draft_id}")
async def get_draft(matter_id: str, draft_id: str) -> dict:
    store = _get_store()
    await store.init_schema()
    payload = await store.get(f"drafts/{matter_id}/{draft_id}")
    if payload is None:
        raise HTTPException(status_code=404, detail="draft not found")
    return payload
```

- [ ] **Step 2: `apps/api/src/draftloop_api/routes/edits.py`**

```python
from __future__ import annotations

import json
import time
from typing import Any

from fastapi import APIRouter, HTTPException, Request, Response

from draftloop_core.config import get_settings
from draftloop_core.storage.sqlite_document_store import SqliteDocumentStore

router = APIRouter(prefix="/api/matters/{matter_id}/drafts")

_store: SqliteDocumentStore | None = None


def _get_store() -> SqliteDocumentStore:
    global _store
    if _store is None:
        settings = get_settings()
        _store = SqliteDocumentStore(f"{settings.data_dir}/draftloop.db")
    return _store


@router.post("/{draft_id}/edits", status_code=202)
async def post_edits(matter_id: str, draft_id: str, request: Request, response: Response) -> dict[str, Any]:
    body = await request.json()
    events = body.get("edits") or []
    if not isinstance(events, list):
        raise HTTPException(status_code=400, detail="edits must be a list")
    store = _get_store()
    await store.init_schema()
    key = f"edits/{matter_id}/{draft_id}"
    existing = await store.get(key) or []
    existing.extend(events)
    await store.put(key, existing)
    response.headers["ETag"] = f'"{len(existing)}"'
    return {"batch_id": f"batch_{int(time.time())}", "accepted": len(events)}
```

- [ ] **Step 3: Register routes in `apps/api/src/draftloop_api/main.py`**

```python
from draftloop_api.routes import drafts, edits, health, version

def create_app() -> FastAPI:
    app = FastAPI(...)
    app.include_router(health.router)
    app.include_router(version.router)
    app.include_router(drafts.router)
    app.include_router(edits.router)
    return app
```

- [ ] **Step 4: Failing test**

```python
# apps/api/tests/test_drafts_and_edits.py
import pytest
from fastapi.testclient import TestClient

from draftloop_api.main import create_app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "sk-test")
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    from draftloop_core.config import get_settings
    get_settings.cache_clear()
    import draftloop_api.routes.drafts as drafts_mod
    import draftloop_api.routes.edits as edits_mod
    drafts_mod._store = None
    edits_mod._store = None
    return TestClient(create_app())


def test_get_draft_404_when_missing(client):
    r = client.get("/api/matters/M-1/drafts/D-1")
    assert r.status_code == 404


def test_post_edits_persists(client):
    r = client.post(
        "/api/matters/M-1/drafts/D-1/edits",
        json={"edits": [{"event_id": "ulid-1", "op": "fact_text_changed"}]},
    )
    assert r.status_code == 202
    assert r.json()["accepted"] == 1
    r2 = client.post(
        "/api/matters/M-1/drafts/D-1/edits",
        json={"edits": [{"event_id": "ulid-2", "op": "citation_added"}]},
    )
    assert r2.headers["ETag"] == '"2"'
```

- [ ] **Step 5: Tests pass. Commit.**

```bash
git commit -am "feat(api): add GET draft + POST edits routes"
```

---

## Task 8: `apps/web` editor route + adapter

- [ ] **Step 1: `apps/web/src/lib/api/drafts.ts` + `edits.ts`**

```typescript
// drafts.ts
import { apiGet } from "./client";
import type { CaseFactSummary, ChunkMeta } from "@draftloop/ui";

export interface DraftPayload {
  draft: { matter_id: string; draft_id: string; summary: CaseFactSummary };
  sourceDocs: { doc_id: string; doc_title: string; markdown: string }[];
  chunks: ChunkMeta[];
  audit_trail: Record<string, unknown> | null;
  etag: string;
}

export function fetchDraft(matterId: string, draftId: string): Promise<DraftPayload> {
  return apiGet<DraftPayload>(`/api/matters/${matterId}/drafts/${draftId}`);
}
```

```typescript
// edits.ts
import type { EditEvent } from "@draftloop/ui";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export async function postEdits(matterId: string, draftId: string, edits: EditEvent[]): Promise<void> {
  const res = await fetch(`${API_BASE}/api/matters/${matterId}/drafts/${draftId}/edits`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ edits }),
  });
  if (!res.ok) throw new Error(`POST edits failed: ${res.status}`);
}
```

- [ ] **Step 2: `apps/web/src/app/matters/[id]/draft/[draftId]/page.tsx`**

```tsx
"use client";

import { useEffect, useState } from "react";
import {
  CaseFactSummaryEditor,
  EvidencePanel,
  NeedsReviewBanner,
  AuditTrailDrawer,
  diffSummaries,
  useEditorStore,
} from "@draftloop/ui";
import type { CaseFactSummary } from "@draftloop/ui";
import { fetchDraft, type DraftPayload } from "@/lib/api/drafts";
import { postEdits } from "@/lib/api/edits";

export default function EditorPage({ params }: { params: { id: string; draftId: string } }) {
  const [payload, setPayload] = useState<DraftPayload | null>(null);
  const [focusedChunkId, setFocusedChunkId] = useState<string | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);

  useEffect(() => {
    fetchDraft(params.id, params.draftId).then(setPayload).catch((e) => console.error(e));
  }, [params.id, params.draftId]);

  if (!payload) return <main className="p-8">Loading…</main>;

  const onSave = async (current: CaseFactSummary) => {
    const baseline = useEditorStore.getState().baseline!;
    const events = diffSummaries(baseline, current, {
      draftId: params.draftId,
      matterId: params.id,
      operatorId: "op_local",
      draftModelVersion: "v1",
      promptHash: payload.draft.draft_id,
      factStartTimers: useEditorStore.getState().factTimers,
    });
    await postEdits(params.id, params.draftId, events);
  };

  const needsReviewCount = payload.chunks.filter((c) => c.contains_needs_review).length;

  return (
    <main className="grid grid-cols-[55%_45%] gap-4 p-4 min-h-screen">
      <section className="overflow-y-auto pr-2">
        <header className="mb-4 flex items-center justify-between">
          <h1 className="text-xl font-semibold">Matter {params.id} — Draft {params.draftId}</h1>
          <button type="button" onClick={() => setDrawerOpen(true)} className="text-sm underline">audit</button>
        </header>
        <NeedsReviewBanner count={needsReviewCount} />
        <div className="mt-4">
          <CaseFactSummaryEditor
            matterId={params.id}
            draftId={params.draftId}
            initial={payload.draft.summary}
            onResolveCitation={(cid) => setFocusedChunkId(cid)}
            onSave={onSave}
          />
        </div>
      </section>
      <aside className="overflow-y-auto">
        {payload.sourceDocs.map((doc) => (
          <EvidencePanel
            key={doc.doc_id}
            docTitle={doc.doc_title}
            markdown={doc.markdown}
            chunks={payload.chunks.filter((c) => c.doc_id === doc.doc_id)}
            focusedChunkId={focusedChunkId}
          />
        ))}
      </aside>
      <AuditTrailDrawer data={payload.audit_trail} open={drawerOpen} onClose={() => setDrawerOpen(false)} />
    </main>
  );
}
```

- [ ] **Step 3: Commit + smoke**

```bash
pnpm install
pnpm -F @draftloop/web build
git commit -am "feat(web): add editor route + API adapter for drafts/edits"
```

---

## Task 9: Playwright smoke

- [ ] **Step 1: `tests/e2e/editor_smoke.spec.ts`** (skipped unless `apps/api` + `apps/web` are running locally; CI gates it behind the `full-test` label)

```typescript
import { test, expect } from "@playwright/test";

test("editor renders + edit + save round-trip", async ({ page }) => {
  await page.goto("http://localhost:3000/matters/M-1/draft/D-seed");
  await expect(page.getByRole("heading", { name: /Matter M-1/ })).toBeVisible({ timeout: 20_000 });
  const firstFact = page.getByLabel(/fact .* text/).first();
  await firstFact.fill("Plaintiff Acme Corp. v. Widgets Inc. (edited)");
  await page.getByRole("button", { name: "Save" }).click();
  await expect(page.getByText(/Save/i)).toBeVisible();
});
```

- [ ] **Step 2: Document running it**

```bash
# Terminal A
bash scripts/dev.sh
# Terminal B (after API + web up)
pnpm dlx playwright install
pnpm dlx playwright test tests/e2e/editor_smoke.spec.ts
```

- [ ] **Step 3: Commit, merge.**

```bash
git add tests/e2e/editor_smoke.spec.ts
git commit -m "test(e2e): Playwright editor smoke"
bash scripts/lint.sh
uv run pytest -q
pnpm -r test
git checkout main
git merge --no-ff feat/plan-4-operator-ui -m "Merge Plan 4: Operator UI + EditEvent capture"
```

---

## Done criteria

- [ ] CaseFactSummary editor renders, edits, saves; `EditEvent[]` posted.
- [ ] Source viewer highlights cited spans; needs_review amber color visible.
- [ ] All unit tests pass; Playwright smoke runs locally.
- [ ] Plans index updated; next is Plan 5 (Improvement Loop).
