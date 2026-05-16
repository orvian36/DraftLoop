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
          <h2
            id={`slot-${slot}`}
            className="text-sm uppercase tracking-wide text-slate-500 mb-2"
          >
            {slot.replace("_", " ")}
          </h2>
          <ul className="space-y-2">
            {store.current[slot].map((f) => (
              <li
                key={f.sentence_id}
                className="rounded-md border border-slate-200 bg-white p-3"
              >
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
