export { HealthBadge } from "./components/HealthBadge";
export type { HealthBadgeProps } from "./components/HealthBadge";

export { CitationChip } from "./components/CitationChip";
export type { CitationChipProps } from "./components/CitationChip";

export { DiffViewer } from "./components/DiffViewer";
export type { DiffViewerProps } from "./components/DiffViewer";

export { NeedsReviewBanner } from "./components/NeedsReviewBanner";
export type { NeedsReviewBannerProps } from "./components/NeedsReviewBanner";

export { CaseFactSummaryViewer } from "./components/CaseFactSummaryViewer";
export type { CaseFactSummaryViewerProps } from "./components/CaseFactSummaryViewer";

export { CaseFactSummaryEditor } from "./components/CaseFactSummaryEditor";
export type { CaseFactSummaryEditorProps } from "./components/CaseFactSummaryEditor";

export { EvidencePanel } from "./components/EvidencePanel";
export type { EvidencePanelProps } from "./components/EvidencePanel";

export { AuditTrailDrawer } from "./components/AuditTrailDrawer";
export type { AuditTrailDrawerProps } from "./components/AuditTrailDrawer";

export type {
  CaseFactSummary,
  Fact,
  Citation,
  Confidence,
} from "./types/draft";
export { SLOT_ORDER, UNSUPPORTED } from "./types/draft";

export type { EditEvent, EditOp } from "./types/edits";
export type { ChunkMeta } from "./types/retrieval";

export { useEditorStore } from "./state/editor-store";
export type { EditorState } from "./state/editor-store";
export { diffSummaries } from "./state/diff";
export type { DiffContext } from "./state/diff";

export { ulid } from "./utils/ulid";
