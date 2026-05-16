import type { EditEvent } from "@draftloop/ui";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export async function postEdits(
  matterId: string,
  draftId: string,
  edits: EditEvent[],
): Promise<void> {
  const res = await fetch(
    `${API_BASE}/api/matters/${matterId}/drafts/${draftId}/edits`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ edits }),
    },
  );
  if (!res.ok) {
    throw new Error(`postEdits failed: ${res.status}`);
  }
}
