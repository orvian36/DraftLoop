import type { ReactElement } from "react";

export interface AuditTrailDrawerProps {
  data: Record<string, unknown> | null;
  open: boolean;
  onClose: () => void;
}

export function AuditTrailDrawer({
  data,
  open,
  onClose,
}: AuditTrailDrawerProps): ReactElement | null {
  if (!open) return null;
  return (
    <aside
      role="dialog"
      aria-label="Audit trail"
      className="fixed right-0 top-0 h-full w-[420px] bg-white shadow-xl border-l border-slate-200 p-4 overflow-y-auto"
    >
      <div className="flex justify-between items-center mb-3">
        <h3 className="font-semibold">Audit trail</h3>
        <button
          type="button"
          onClick={onClose}
          className="text-sm text-slate-500 hover:text-slate-900"
        >
          Close
        </button>
      </div>
      <pre className="text-xs whitespace-pre-wrap font-mono text-slate-800">
        {data ? JSON.stringify(data, null, 2) : "(no audit data)"}
      </pre>
    </aside>
  );
}
