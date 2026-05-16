import type { ReactElement } from "react";
import type { CaseFactSummary } from "../types/draft";
import { SLOT_ORDER } from "../types/draft";
import { CitationChip } from "./CitationChip";

export interface CaseFactSummaryViewerProps {
  summary: CaseFactSummary;
  onResolveCitation: (chunkId: string) => void;
}

export function CaseFactSummaryViewer({
  summary,
  onResolveCitation,
}: CaseFactSummaryViewerProps): ReactElement {
  return (
    <div className="space-y-6">
      {SLOT_ORDER.map((slot) => (
        <section key={slot} aria-labelledby={`slot-${slot}`}>
          <h2
            id={`slot-${slot}`}
            className="text-sm uppercase tracking-wide text-slate-500 mb-2"
          >
            {slot.replace("_", " ")}
          </h2>
          <ul className="space-y-2">
            {summary[slot].map((f) => (
              <li
                key={f.sentence_id}
                className="rounded-md border border-slate-200 bg-white p-3"
              >
                <p className="text-slate-900">{f.text}</p>
                <div className="mt-2 flex flex-wrap gap-1">
                  {f.citations.map((c) => (
                    <CitationChip
                      key={c.chunk_id}
                      citation={c}
                      onResolve={onResolveCitation}
                    />
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
