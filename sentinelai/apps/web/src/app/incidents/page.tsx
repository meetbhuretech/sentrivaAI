"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { PageHeader } from "@/components/PageHeader";
import { SeverityBadge } from "@/components/ui/SeverityBadge";
import { StatusPill } from "@/components/ui/StatusPill";
import { useAuth } from "@/components/AuthProvider";
import { api } from "@/lib/api";
import type { Incident, Paginated } from "@/lib/types";

export default function IncidentsPage() {
  const { user } = useAuth();
  const [items, setItems] = useState<Incident[]>([]);
  const [status, setStatus] = useState("");
  const [message, setMessage] = useState<string | null>(null);

  const load = useCallback(async () => {
    const q = status ? `?status=${status}` : "";
    const page = await api<Paginated<Incident>>(`/incidents${q}`);
    setItems(page.items);
  }, [status]);

  useEffect(() => {
    void load();
  }, [load]);

  async function runDetection() {
    setMessage(null);
    try {
      const result = await api<{
        candidates: number;
        incidents_created: number;
        incidents_updated: number;
      }>("/alerts/evaluate", { method: "POST" });
      setMessage(
        `Detection: ${result.candidates} candidates, ${result.incidents_created} created, ${result.incidents_updated} updated`,
      );
      await load();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Detection failed");
    }
  }

  const canEngineer = user?.role === "engineer" || user?.role === "admin";

  return (
    <div>
      <PageHeader
        title="Incidents"
        description="Grouped alerts with severity and lifecycle state."
        actions={
          <>
            <select
              className="rounded-lg border border-[var(--border)] bg-black/30 px-3 py-2 text-sm"
              value={status}
              onChange={(e) => setStatus(e.target.value)}
            >
              <option value="">All statuses</option>
              <option value="open">open</option>
              <option value="investigating">investigating</option>
              <option value="resolved">resolved</option>
            </select>
            {canEngineer ? (
              <button
                type="button"
                onClick={() => void runDetection()}
                className="rounded-lg bg-[var(--accent)] px-3 py-2 text-sm font-medium text-[#04241c]"
              >
                Run detection
              </button>
            ) : null}
          </>
        }
      />
      {message ? <div className="mb-4 text-sm text-muted">{message}</div> : null}
      <div className="panel overflow-hidden">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-[var(--border)] text-xs uppercase tracking-wide text-muted">
            <tr>
              <th className="px-4 py-3">Incident</th>
              <th className="px-4 py-3">Severity</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Services</th>
              <th className="px-4 py-3">Detected</th>
            </tr>
          </thead>
          <tbody>
            {items.map((inc) => (
              <tr key={inc.id} className="border-b border-[var(--border)]/70 hover:bg-white/[0.02]">
                <td className="px-4 py-3">
                  <Link href={`/incidents/${inc.id}`} className="font-medium hover:text-[var(--accent)]">
                    {inc.title}
                  </Link>
                </td>
                <td className="px-4 py-3">
                  <SeverityBadge severity={inc.severity} />
                </td>
                <td className="px-4 py-3">
                  <StatusPill status={inc.status} />
                </td>
                <td className="px-4 py-3 font-mono text-xs text-muted">
                  {inc.service_names.join(", ")}
                </td>
                <td className="px-4 py-3 text-xs text-muted">
                  {new Date(inc.detected_at).toLocaleString()}
                </td>
              </tr>
            ))}
            {items.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-muted">
                  No incidents. Trigger a simulator scenario, then run detection.
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </div>
  );
}
