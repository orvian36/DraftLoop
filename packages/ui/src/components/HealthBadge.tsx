import type { ReactElement } from "react";

export interface HealthBadgeProps {
  ok: boolean;
  label: string;
}

export function HealthBadge({ ok, label }: HealthBadgeProps): ReactElement {
  const cls = ok
    ? "bg-emerald-100 text-emerald-800"
    : "bg-rose-100 text-rose-800";
  return (
    <span
      role="status"
      aria-live="polite"
      className={`inline-flex items-center gap-2 rounded-full px-3 py-1 text-sm font-medium ${cls}`}
    >
      <span
        aria-hidden="true"
        className={`h-2 w-2 rounded-full ${ok ? "bg-emerald-500" : "bg-rose-500"}`}
      />
      {label}
    </span>
  );
}
