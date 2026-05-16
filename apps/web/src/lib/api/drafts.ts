import type { CaseFactSummary, ChunkMeta } from "@draftloop/ui";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export interface DraftPayload {
  draft: { matter_id: string; draft_id: string; summary: CaseFactSummary };
  sourceDocs: { doc_id: string; doc_title: string; markdown: string }[];
  chunks: ChunkMeta[];
  audit_trail: Record<string, unknown> | null;
  etag: string;
}

export async function fetchDraft(
  matterId: string,
  draftId: string,
): Promise<DraftPayload> {
  const res = await fetch(
    `${API_BASE}/api/matters/${matterId}/drafts/${draftId}`,
    { cache: "no-store" },
  );
  if (!res.ok) {
    throw new Error(`fetchDraft ${matterId}/${draftId} failed: ${res.status}`);
  }
  return (await res.json()) as DraftPayload;
}
