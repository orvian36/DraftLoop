import type { ReactElement } from "react";

export interface NeedsReviewBannerProps {
  count: number;
}

export function NeedsReviewBanner({ count }: NeedsReviewBannerProps): ReactElement | null {
  if (count <= 0) return null;
  return (
    <div
      role="alert"
      className="rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-amber-900 text-sm"
    >
      ⚠ {count} low-confidence span{count === 1 ? "" : "s"} flagged by ingestion. Verify before citing.
    </div>
  );
}
