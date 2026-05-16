import { useMemo } from "react";
import type { ReactElement } from "react";
import type { ChunkMeta } from "../types/retrieval";

export interface EvidencePanelProps {
  docTitle: string;
  markdown: string;
  chunks: ChunkMeta[];
  focusedChunkId?: string | null;
  onSelectRange?: (selection: { text: string; chunkId: string }) => void;
}

interface Segment {
  text: string;
  cls: string;
  chunk_id: string | null;
}

function buildSegments(
  md: string,
  chunks: ChunkMeta[],
  focused: string | null | undefined,
): Segment[] {
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
    segments.push({
      text: md.slice(c.char_start, c.char_end),
      cls,
      chunk_id: c.chunk_id,
    });
    cursor = c.char_end;
  }
  if (cursor < md.length) {
    segments.push({ text: md.slice(cursor), cls: "", chunk_id: null });
  }
  return segments;
}

export function EvidencePanel({
  docTitle,
  markdown,
  chunks,
  focusedChunkId,
  onSelectRange,
}: EvidencePanelProps): ReactElement {
  const segments = useMemo(
    () => buildSegments(markdown, chunks, focusedChunkId),
    [markdown, chunks, focusedChunkId],
  );
  return (
    <div
      className="h-full overflow-y-auto rounded-md border border-slate-200 bg-white p-4 font-mono text-sm whitespace-pre-wrap"
      data-testid="evidence-panel"
    >
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
