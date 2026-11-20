"use client";

import { useCallback, useEffect, useState } from "react";
import { ApprovalModal } from "@/components/ApprovalModal";
import { PageHeader } from "@/components/PageHeader";
import { StatusPill } from "@/components/ui/StatusPill";
import { useAuth } from "@/components/AuthProvider";
import { api } from "@/lib/api";
import type { Paginated, RemediationPlan } from "@/lib/types";

export default function RemediationPage() {
  const { user } = useAuth();
  const [items, setItems] = useState<RemediationPlan[]>([]);
  const [selected, setSelected] = useState<RemediationPlan | null>(null);
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const load = useCallback(async () => {
    const page = await api<Paginated<RemediationPlan>>("/remediations");
    setItems(page.items);
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const canEngineer = user?.role === "engineer" || user?.role === "admin";

  async function approve() {
    if (!selected) return;
    setBusy(true);
    try {
      await api(`/remediations/${selected.id}/approve`, {
        method: "POST",
        body: JSON.stringify({ reason: "Approved from UI" }),
      });
      setMessage("Remediation approved and executed in sandbox.");
      setOpen(false);
      await load();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Approve failed");
    } finally {
      setBusy(false);
    }
  }

  async function reject() {
    if (!selected) return;
    setBusy(true);
    try {
      await api(`/remediations/${selected.id}/reject`, {
        method: "POST",
        body: JSON.stringify({ reason: "Rejected from UI" }),
      });
      setMessage("Remediation rejected.");
      setOpen(false);
      await load();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Reject failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <PageHeader
        title="Remediation Center"
        description="Proposed fixes require explicit human approval. Execution is simulator-sandbox only."
      />
      {message ? <div className="mb-4 text-sm text-muted">{message}</div> : null}
      <div className="space-y-3">
        {items.map((plan) => (
          <div key={plan.id} className="panel p-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <div className="font-medium">{plan.problem_summary}</div>
                <div className="mt-1 text-sm text-muted">{plan.rationale}</div>
                <div className="mt-2 text-xs text-muted">{plan.expected_impact}</div>
              </div>
              <div className="flex items-center gap-2">
                <StatusPill status={plan.status} />
                {canEngineer && plan.status === "proposed" ? (
                  <button
                    type="button"
                    onClick={() => {
                      setSelected(plan);
                      setOpen(true);
                    }}
                    className="rounded-lg bg-[var(--accent)] px-3 py-1.5 text-xs font-medium text-[#04241c]"
                  >
                    Review
                  </button>
                ) : null}
              </div>
            </div>
            <ul className="mt-3 space-y-1 font-mono text-[11px] text-muted">
              {plan.actions.map((a, i) => (
                <li key={i}>
                  {String(a.action_type)} — {String(a.command_preview || "")}
                </li>
              ))}
            </ul>
          </div>
        ))}
        {items.length === 0 ? (
          <div className="text-sm text-muted">
            No remediation plans. Complete an investigation first.
          </div>
        ) : null}
      </div>
      <ApprovalModal
        plan={selected}
        open={open}
        busy={busy}
        onClose={() => setOpen(false)}
        onApprove={() => void approve()}
        onReject={() => void reject()}
      />
    </div>
  );
}
