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
          op === 1
            ? "bg-emerald-100 text-emerald-900"
            : op === -1
              ? "bg-rose-100 text-rose-900 line-through"
              : "";
        return (
          <span key={i} className={cls}>
            {text}
          </span>
        );
      })}
    </div>
  );
}
