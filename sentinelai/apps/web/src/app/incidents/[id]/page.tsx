"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { PageHeader } from "@/components/PageHeader";
import { SeverityBadge } from "@/components/ui/SeverityBadge";
import { StatusPill } from "@/components/ui/StatusPill";
import { useAuth } from "@/components/AuthProvider";
import { api } from "@/lib/api";
import type { Incident, Investigation } from "@/lib/types";

type TimelineEvent = {
  type: string;
  timestamp: string;
  title: string;
  severity?: string;
  rule_id?: string;
  service_name?: string;
};

export default function IncidentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const router = useRouter();
  const [incident, setIncident] = useState<Incident | null>(null);
  const [events, setEvents] = useState<TimelineEvent[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void (async () => {
      try {
        const [inc, tl] = await Promise.all([
          api<Incident>(`/incidents/${id}`),
          api<{ events: TimelineEvent[] }>(`/incidents/${id}/timeline`),
        ]);
        setIncident(inc);
        setEvents(tl.events);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load incident");
      }
    })();
  }, [id]);

  async function investigate() {
    setBusy(true);
    setError(null);
    try {
      const inv = await api<Investigation>(`/incidents/${id}/investigate`, {
        method: "POST",
        body: JSON.stringify({ provider: "deterministic", model: "rules-v1" }),
      });
      router.push(`/investigations/${inv.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Investigation failed");
    } finally {
      setBusy(false);
    }
  }

  const canEngineer = user?.role === "engineer" || user?.role === "admin";

  if (!incident && !error) {
    return <div className="text-muted">Loading incident…</div>;
  }

  return (
    <div>
      <PageHeader
        title={incident?.title || "Incident"}
        description={incident?.summary || "Incident detail and alert timeline"}
        actions={
          canEngineer ? (
            <button
              type="button"
              disabled={busy}
              onClick={() => void investigate()}
              className="rounded-lg bg-[var(--accent)] px-3 py-2 text-sm font-medium text-[#04241c] disabled:opacity-60"
            >
              {busy ? "Investigating…" : "Start AI investigation"}
            </button>
          ) : null
        }
      />
      {error ? (
        <div className="mb-4 text-sm text-[var(--critical)]">{error}</div>
      ) : null}
      {incident ? (
        <div className="mb-6 flex flex-wrap gap-3">
          <SeverityBadge severity={incident.severity} />
          <StatusPill status={incident.status} />
          <span className="rounded-md border border-[var(--border)] px-2 py-0.5 text-xs text-muted">
            {incident.service_names.join(", ")}
          </span>
          <Link href="/incidents" className="text-xs text-[var(--accent)] self-center">
            ← Back
          </Link>
        </div>
      ) : null}

      <div className="panel p-4">
        <h2 className="mb-4 text-sm font-medium">Realtime incident timeline</h2>
        <ol className="relative space-y-4 border-l border-[var(--border)] pl-5">
          {events.map((ev, idx) => (
            <li key={`${ev.timestamp}-${idx}`} className="relative">
              <span className="absolute -left-[1.4rem] top-1 h-2.5 w-2.5 rounded-full bg-[var(--accent)]" />
              <div className="text-xs text-muted">
                {new Date(ev.timestamp).toLocaleString()} · {ev.type}
              </div>
              <div className="text-sm">{ev.title}</div>
              {ev.service_name ? (
                <div className="font-mono text-xs text-muted">{ev.service_name}</div>
              ) : null}
            </li>
          ))}
          {events.length === 0 ? (
            <li className="text-sm text-muted">No timeline events yet.</li>
          ) : null}
        </ol>
      </div>
    </div>
  );
}
