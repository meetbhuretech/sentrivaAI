"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { PageHeader } from "@/components/PageHeader";
import { StatusPill } from "@/components/ui/StatusPill";
import { api } from "@/lib/api";
import { openSSE } from "@/lib/sse";
import type { Investigation } from "@/lib/types";

type Evidence = {
  findings: Array<{
    agent_name: string;
    summary: string;
    source: string;
    evidence_refs: Array<{ kind: string; id: string; label?: string }>;
  }>;
  hypotheses: Array<{
    statement: string;
    confidence: number;
    grounded?: boolean | null;
    evaluation_notes?: string | null;
    evidence_refs: unknown[];
  }>;
  tool_calls: Array<{ tool: string; result_summary?: string; at?: string }>;
};

export default function InvestigationDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [inv, setInv] = useState<Investigation | null>(null);
  const [timeline, setTimeline] = useState<Array<{ step: string; timestamp: string }>>([]);
  const [evidence, setEvidence] = useState<Evidence | null>(null);

  useEffect(() => {
    void (async () => {
      const e = await api<Evidence>(`/investigations/${id}/evidence`);
      setEvidence(e);
    })();
    const close = openSSE(`/investigations/${id}/stream`, (event, data) => {
      if (event !== "investigation") return;
      const payload = data as {
        investigation: Investigation;
        events: Array<{ step: string; timestamp: string }>;
      };
      setInv(payload.investigation);
      setTimeline(payload.events);
      void api<Evidence>(`/investigations/${id}/evidence`).then(setEvidence);
    });
    return close;
  }, [id]);

  const rca = (inv?.rca || {}) as Record<string, unknown>;

  return (
    <div>
      <PageHeader
        title="Agent Execution"
        description="Checkpointed investigation steps, findings, and evidence viewer."
      />
      {inv ? (
        <div className="mb-4 flex flex-wrap gap-2">
          <StatusPill status={inv.status} />
          <span className="rounded-md border border-[var(--border)] px-2 py-0.5 text-xs text-muted">
            {inv.provider}/{inv.model}
          </span>
          <span className="rounded-md border border-[var(--border)] px-2 py-0.5 font-mono text-xs text-muted">
            {inv.current_step}
          </span>
        </div>
      ) : (
        <div className="text-muted">Loading…</div>
      )}

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="panel p-4">
          <h2 className="mb-3 text-sm font-medium">Agent execution timeline</h2>
          <ol className="space-y-3 border-l border-[var(--border)] pl-4">
            {timeline.map((ev, i) => (
              <li key={`${ev.step}-${i}`}>
                <div className="text-xs text-muted">
                  {new Date(ev.timestamp).toLocaleTimeString()}
                </div>
                <div className="font-mono text-sm">{ev.step}</div>
              </li>
            ))}
          </ol>
        </div>

        <div className="panel p-4">
          <h2 className="mb-3 text-sm font-medium">Root cause analysis</h2>
          {rca.probable_root_cause ? (
            <div className="space-y-3 text-sm">
              <div>
                <div className="text-xs uppercase tracking-wide text-muted">Probable cause</div>
                <div>{String(rca.probable_root_cause)}</div>
              </div>
              <div>
                <div className="text-xs uppercase tracking-wide text-muted">Confidence</div>
                <div className="tabular-nums">
                  {Number(rca.confidence ?? 0).toFixed(3)}
                </div>
                <pre className="mt-1 overflow-auto rounded-md bg-black/30 p-2 font-mono text-[11px] text-muted">
                  {JSON.stringify(rca.confidence_components || {}, null, 2)}
                </pre>
              </div>
              <div>
                <div className="text-xs uppercase tracking-wide text-muted">
                  Business impact (estimate)
                </div>
                <div>{String(rca.business_impact_estimate || "")}</div>
              </div>
              <div>
                <div className="text-xs uppercase tracking-wide text-muted">
                  Supporting evidence
                </div>
                <ul className="mt-1 space-y-1 font-mono text-[11px]">
                  {((rca.supporting_evidence as Array<Record<string, string>>) || []).map(
                    (ref, idx) => (
                      <li key={idx} className="rounded bg-black/25 px-2 py-1">
                        {ref.kind}:{ref.id.slice(0, 8)}… {ref.label || ""}
                      </li>
                    ),
                  )}
                </ul>
              </div>
            </div>
          ) : (
            <div className="text-sm text-muted">RCA not available yet.</div>
          )}
        </div>
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <div className="panel p-4">
          <h2 className="mb-3 text-sm font-medium">Evidence viewer — agent findings</h2>
          <div className="space-y-3">
            {evidence?.findings.map((f, i) => (
              <div key={i} className="rounded-lg border border-[var(--border)] bg-black/20 p-3">
                <div className="flex items-center justify-between gap-2">
                  <div className="text-sm font-medium">{f.agent_name}</div>
                  <span className="text-[10px] uppercase text-muted">{f.source}</span>
                </div>
                <div className="mt-1 text-sm text-muted">{f.summary}</div>
                <div className="mt-2 font-mono text-[11px] text-muted">
                  {f.evidence_refs.length} evidence refs
                </div>
              </div>
            ))}
          </div>
        </div>
        <div className="panel p-4">
          <h2 className="mb-3 text-sm font-medium">Tool calls</h2>
          <ul className="space-y-2 font-mono text-xs">
            {evidence?.tool_calls.map((t, i) => (
              <li key={i} className="rounded-md bg-black/25 px-2 py-1.5">
                {t.tool} — {t.result_summary}
              </li>
            ))}
          </ul>
          <h2 className="mb-2 mt-5 text-sm font-medium">Hypotheses</h2>
          <ul className="space-y-2 text-sm">
            {evidence?.hypotheses.map((h, i) => (
              <li key={i} className="rounded-lg border border-[var(--border)] p-2">
                <div>{h.statement}</div>
                <div className="text-xs text-muted">
                  conf {h.confidence.toFixed(2)} · grounded {String(h.grounded)} ·{" "}
                  {h.evaluation_notes}
                </div>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
