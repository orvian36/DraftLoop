import type { ReactElement } from "react";
import type { Citation } from "../types/draft";

export interface CitationChipProps {
  citation: Citation;
  onResolve: (chunkId: string) => void;
  onRemove?: (chunkId: string) => void;
  active?: boolean;
}

export function CitationChip({
  citation,
  onResolve,
  onRemove,
  active,
}: CitationChipProps): ReactElement {
  const cls = active
    ? "border-sky-500 bg-sky-50 text-sky-900"
    : "border-slate-300 bg-slate-100 text-slate-700 hover:bg-slate-200";
  return (
    <span
      role="button"
      tabIndex={0}
      onClick={() => onResolve(citation.chunk_id)}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") onResolve(citation.chunk_id);
      }}
      className={`inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-xs font-mono cursor-pointer ${cls}`}
      data-chunk-id={citation.chunk_id}
    >
      <span aria-hidden className="text-slate-500">¶</span>
      {citation.chunk_id}
      {onRemove ? (
        <button
          type="button"
          aria-label={`remove citation ${citation.chunk_id}`}
          onClick={(e) => {
            e.stopPropagation();
            onRemove(citation.chunk_id);
          }}
          className="ml-1 text-slate-500 hover:text-rose-600"
        >
          ×
        </button>
      ) : null}
    </span>
  );
}
