"use client";

import { useEffect, useState } from "react";
import {
  AuditTrailDrawer,
  CaseFactSummaryEditor,
  EvidencePanel,
  NeedsReviewBanner,
  diffSummaries,
  useEditorStore,
} from "@draftloop/ui";
import type { CaseFactSummary } from "@draftloop/ui";
import { fetchDraft, type DraftPayload } from "@/lib/api/drafts";
import { postEdits } from "@/lib/api/edits";

export default function EditorPage({
  params,
}: {
  params: { id: string; draftId: string };
}) {
  const [payload, setPayload] = useState<DraftPayload | null>(null);
  const [focusedChunkId, setFocusedChunkId] = useState<string | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [status, setStatus] = useState<"idle" | "saving" | "saved" | "error">("idle");

  useEffect(() => {
    fetchDraft(params.id, params.draftId)
      .then(setPayload)
      .catch((e) => console.error(e));
  }, [params.id, params.draftId]);

  if (!payload) {
    return <main className="p-8">Loading…</main>;
  }

  const onSave = async (current: CaseFactSummary) => {
    setStatus("saving");
    const baseline = useEditorStore.getState().baseline!;
    const events = diffSummaries(baseline, current, {
      draftId: params.draftId,
      matterId: params.id,
      operatorId: "op_local",
      draftModelVersion: "v1",
      promptHash: payload.draft.draft_id,
      factStartTimers: useEditorStore.getState().factTimers,
    });
    try {
      await postEdits(params.id, params.draftId, events);
      setStatus("saved");
    } catch {
      setStatus("error");
    }
  };

  const needsReviewCount = payload.chunks.filter((c) => c.contains_needs_review).length;

  return (
    <main className="grid grid-cols-[55%_45%] gap-4 p-4 min-h-screen">
      <section className="overflow-y-auto pr-2">
        <header className="mb-4 flex items-center justify-between">
          <h1 className="text-xl font-semibold">
            Matter {params.id} — Draft {params.draftId}
          </h1>
          <div className="flex items-center gap-3 text-sm">
            <span aria-live="polite">
              {status === "saving" ? "Saving…" : status === "saved" ? "Saved." : ""}
            </span>
            <button
              type="button"
              onClick={() => setDrawerOpen(true)}
              className="underline text-slate-600 hover:text-slate-900"
            >
              audit
            </button>
          </div>
        </header>
        <NeedsReviewBanner count={needsReviewCount} />
        <div className="mt-4">
          <CaseFactSummaryEditor
            matterId={params.id}
            draftId={params.draftId}
            initial={payload.draft.summary}
            onResolveCitation={(cid: string) => setFocusedChunkId(cid)}
            onSave={onSave}
          />
        </div>
      </section>
      <aside className="overflow-y-auto space-y-3">
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
      <AuditTrailDrawer
        data={payload.audit_trail}
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
      />
    </main>
  );
}
