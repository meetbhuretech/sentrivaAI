"use client";

import { useCallback, useEffect, useState } from "react";
import { PageHeader } from "@/components/PageHeader";
import { StatusPill } from "@/components/ui/StatusPill";
import { useAuth } from "@/components/AuthProvider";
import { api } from "@/lib/api";
import type { EvaluationRun, Paginated } from "@/lib/types";

export default function EvaluationPage() {
  const { user } = useAuth();
  const [runs, setRuns] = useState<EvaluationRun[]>([]);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [comparisons, setComparisons] = useState<Record<string, unknown>>({});

  const load = useCallback(async () => {
    const [page, cmp] = await Promise.all([
      api<Paginated<EvaluationRun>>("/evaluation/runs"),
      api<{ datasets: Record<string, unknown> }>("/evaluation/comparisons"),
    ]);
    setRuns(page.items);
    setComparisons(cmp.datasets);
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const canEngineer = user?.role === "engineer" || user?.role === "admin";

  async function startRun() {
    setBusy(true);
    setMessage(null);
    try {
      const run = await api<EvaluationRun>("/evaluation/runs", {
        method: "POST",
        body: JSON.stringify({
          dataset_version: "v1",
          provider: "deterministic",
          model: "rules-v1",
        }),
      });
      setMessage(
        `Run ${run.id.slice(0, 8)}… completed with pass_rate=${String(
          (run.metrics as Record<string, unknown> | null)?.pass_rate ?? "n/a",
        )}`,
      );
      await load();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Evaluation failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <PageHeader
        title="Model Evaluation"
        description="Measured scores only. remediation_quality stays null until human review."
        actions={
          canEngineer ? (
            <button
              type="button"
              disabled={busy}
              onClick={() => void startRun()}
              className="rounded-lg bg-[var(--accent)] px-3 py-2 text-sm font-medium text-[#04241c] disabled:opacity-60"
            >
              {busy ? "Running…" : "Run v1 deterministic eval"}
            </button>
          ) : null
        }
      />
      {message ? <div className="mb-4 text-sm text-muted">{message}</div> : null}

      <div className="panel overflow-hidden">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-[var(--border)] text-xs uppercase text-muted">
            <tr>
              <th className="px-4 py-3">Run</th>
              <th className="px-4 py-3">Model</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Pass rate</th>
              <th className="px-4 py-3">Root cause acc.</th>
              <th className="px-4 py-3">Created</th>
            </tr>
          </thead>
          <tbody>
            {runs.map((run) => {
              const m = (run.metrics || {}) as Record<string, unknown>;
              return (
                <tr key={run.id} className="border-b border-[var(--border)]/70">
                  <td className="px-4 py-3 font-mono text-xs">{run.id.slice(0, 8)}…</td>
                  <td className="px-4 py-3 text-xs">
                    {run.provider}/{run.model}
                  </td>
                  <td className="px-4 py-3">
                    <StatusPill status={run.status} />
                  </td>
                  <td className="px-4 py-3 tabular-nums">{String(m.pass_rate ?? "—")}</td>
                  <td className="px-4 py-3 tabular-nums">
                    {String(m.root_cause_accuracy ?? "—")}
                  </td>
                  <td className="px-4 py-3 text-xs text-muted">
                    {new Date(run.created_at).toLocaleString()}
                  </td>
                </tr>
              );
            })}
            {runs.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-muted">
                  No evaluation runs yet.
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>

      <div className="panel mt-4 p-4">
        <h2 className="mb-2 text-sm font-medium">Comparisons by dataset</h2>
        <pre className="overflow-auto rounded-md bg-black/30 p-3 font-mono text-[11px] text-muted">
          {JSON.stringify(comparisons, null, 2)}
        </pre>
      </div>
    </div>
  );
}
