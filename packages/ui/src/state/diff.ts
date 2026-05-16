import { diff_match_patch } from "diff-match-patch";
import type { CaseFactSummary, Citation, Fact } from "../types/draft";
import { SLOT_ORDER } from "../types/draft";
import type { EditEvent, EditOp } from "../types/edits";
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
  before?.citations.forEach((c: Citation) => evidenceIds.add(c.chunk_id));
  after?.citations.forEach((c: Citation) => evidenceIds.add(c.chunk_id));
  return {
    event_id: ulid(),
    draft_id: ctx.draftId,
    matter_id: ctx.matterId,
    slot,
    sentence_id,
    op,
    before: before ? { text: before.text, citations: before.citations } : null,
    after: after ? { text: after.text, citations: after.citations } : null,
    source_evidence_ids: [...evidenceIds],
    word_diff: wordDiff,
    time_to_edit_ms: startedAt ? Date.now() - startedAt : 0,
    operator_id: ctx.operatorId,
    draft_model_version: ctx.draftModelVersion,
    prompt_hash: ctx.promptHash,
    timestamp,
  };
}
