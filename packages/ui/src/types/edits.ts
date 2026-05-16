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
