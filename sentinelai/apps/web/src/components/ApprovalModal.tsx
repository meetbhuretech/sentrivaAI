"use client";

import type { RemediationPlan } from "@/lib/types";

export function ApprovalModal({
  plan,
  open,
  busy,
  onClose,
  onApprove,
  onReject,
}: {
  plan: RemediationPlan | null;
  open: boolean;
  busy?: boolean;
  onClose: () => void;
  onApprove: () => void;
  onReject: () => void;
}) {
  if (!open || !plan) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm">
      <div className="panel w-full max-w-lg p-6 shadow-2xl shadow-black/40">
        <h2 className="font-[family-name:var(--font-display)] text-xl font-semibold">
          Approve remediation?
        </h2>
        <p className="mt-2 text-sm text-muted">
          Execution is sandboxed against the local simulator only. No production
          infrastructure is touched.
        </p>
        <div className="mt-4 space-y-3 text-sm">
          <div>
            <div className="text-xs uppercase tracking-wide text-muted">Problem</div>
            <div>{plan.problem_summary}</div>
          </div>
          <div>
            <div className="text-xs uppercase tracking-wide text-muted">Rationale</div>
            <div>{plan.rationale}</div>
          </div>
          <div>
            <div className="text-xs uppercase tracking-wide text-muted">Actions</div>
            <ul className="mt-1 space-y-1 font-mono text-xs">
              {plan.actions.map((a, i) => (
                <li key={i} className="rounded-md bg-black/30 px-2 py-1">
                  {String(a.action_type)} — {String(a.command_preview || "")}
                </li>
              ))}
            </ul>
          </div>
          <div>
            <div className="text-xs uppercase tracking-wide text-muted">Risks</div>
            <div>{plan.risks}</div>
          </div>
          <div>
            <div className="text-xs uppercase tracking-wide text-muted">
              Expected impact (estimate)
            </div>
            <div>{plan.expected_impact}</div>
          </div>
        </div>
        <div className="mt-6 flex justify-end gap-2">
          <button
            type="button"
            disabled={busy}
            onClick={onClose}
            className="rounded-lg border border-[var(--border)] px-3 py-2 text-sm text-muted"
          >
            Cancel
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={onReject}
            className="rounded-lg border border-[var(--critical)]/40 px-3 py-2 text-sm text-[var(--critical)]"
          >
            Reject
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={onApprove}
            className="rounded-lg bg-[var(--accent)] px-3 py-2 text-sm font-medium text-[#04241c]"
          >
            {busy ? "Executing…" : "Approve & execute"}
          </button>
        </div>
      </div>
    </div>
  );
}
