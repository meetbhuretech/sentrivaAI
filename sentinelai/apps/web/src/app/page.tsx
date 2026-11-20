"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { PageHeader } from "@/components/PageHeader";
import { api } from "@/lib/api";
import { openSSE } from "@/lib/sse";
import type { Incident, OverviewResponse, Paginated } from "@/lib/types";
import { SeverityBadge } from "@/components/ui/SeverityBadge";
import Link from "next/link";

function Stat({
  label,
  value,
  hint,
}: {
  label: string;
  value: string;
  hint?: string;
}) {
  return (
    <div className="panel p-4">
      <div className="text-xs uppercase tracking-wide text-muted">{label}</div>
      <div className="mt-2 font-[family-name:var(--font-display)] text-2xl font-semibold tabular-nums">
        {value}
      </div>
      {hint ? <div className="mt-1 text-xs text-muted">{hint}</div> : null}
    </div>
  );
}

export default function OverviewPage() {
  const [overview, setOverview] = useState<OverviewResponse | null>(null);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [serviceFilter, setServiceFilter] = useState("");

  const loadIncidents = useCallback(async () => {
    try {
      const inc = await api<Paginated<Incident>>("/incidents?page_size=5");
      setIncidents(inc.items);
    } catch {
      /* overview SSE carries primary state */
    }
  }, []);

  useEffect(() => {
    void loadIncidents();
    const q = serviceFilter ? `?service=${encodeURIComponent(serviceFilter)}` : "";
    const close = openSSE(
      `/overview/stream${q}`,
      (event, data) => {
        if (event === "overview") {
          setOverview(data as OverviewResponse);
          setError(null);
          void loadIncidents();
        }
      },
      () => setError("Live stream disconnected — retrying…"),
    );
    return close;
  }, [serviceFilter, loadIncidents]);

  const severityData = overview
    ? Object.entries(overview.severity_distribution).map(([name, value]) => ({
        name,
        value,
      }))
    : [];

  return (
    <div>
      <PageHeader
        title="Operations Overview"
        description="Live aggregates from persisted telemetry and incident state — not hardcoded demo numbers."
        actions={
          <select
            className="rounded-lg border border-[var(--border)] bg-black/30 px-3 py-2 text-sm"
            value={serviceFilter}
            onChange={(e) => setServiceFilter(e.target.value)}
          >
            <option value="">All services</option>
            <option value="api-gateway">api-gateway</option>
            <option value="user-service">user-service</option>
            <option value="order-service">order-service</option>
            <option value="payment-service">payment-service</option>
          </select>
        }
      />

      {error ? (
        <div className="mb-4 rounded-lg border border-[var(--critical)]/30 bg-[var(--critical)]/10 px-3 py-2 text-sm text-[var(--critical)]">
          {error}
        </div>
      ) : null}

      {overview ? (
        <>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <Stat
              label="Services healthy"
              value={`${overview.healthy_services}/${overview.total_services}`}
            />
            <Stat label="Active incidents" value={String(overview.active_incidents)} />
            <Stat
              label="Error rate"
              value={`${(overview.error_rate * 100).toFixed(2)}%`}
              hint={`RPS ${overview.request_rate.toFixed(1)}`}
            />
            <Stat
              label="Latency p95"
              value={`${overview.latency.p95_ms.toFixed(0)} ms`}
              hint={`p50 ${overview.latency.p50_ms.toFixed(0)} · p99 ${overview.latency.p99_ms.toFixed(0)}`}
            />
            <Stat
              label="CPU / Memory"
              value={`${overview.resource_utilization.cpu_percent.toFixed(0)}% / ${overview.resource_utilization.memory_percent.toFixed(0)}%`}
            />
            <Stat
              label="MTTR"
              value={
                overview.mttr_seconds != null
                  ? `${Math.round(overview.mttr_seconds)}s`
                  : "—"
              }
            />
            <Stat
              label="AI investigations"
              value={`${overview.ai_investigations.active} active`}
              hint={`${overview.ai_investigations.completed} completed · ${overview.ai_investigations.failed} failed`}
            />
            <Stat
              label="Last refresh"
              value={
                overview.generated_at
                  ? new Date(overview.generated_at).toLocaleTimeString()
                  : "—"
              }
              hint="Polls every 5s"
            />
          </div>

          <div className="mt-6 grid gap-4 lg:grid-cols-2">
            <div className="panel p-4">
              <h2 className="mb-3 text-sm font-medium">Severity distribution</h2>
              <div className="h-56">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={severityData}>
                    <CartesianGrid stroke="#1e2a38" vertical={false} />
                    <XAxis dataKey="name" stroke="#8b9bb0" fontSize={12} />
                    <YAxis allowDecimals={false} stroke="#8b9bb0" fontSize={12} />
                    <Tooltip
                      contentStyle={{
                        background: "#121a24",
                        border: "1px solid #1e2a38",
                        borderRadius: 8,
                      }}
                    />
                    <Bar dataKey="value" fill="#3ddeb5" radius={[6, 6, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="panel p-4">
              <div className="mb-3 flex items-center justify-between">
                <h2 className="text-sm font-medium">Recent incidents</h2>
                <Link href="/incidents" className="text-xs text-[var(--accent)]">
                  View all
                </Link>
              </div>
              <div className="space-y-2">
                {incidents.length === 0 ? (
                  <div className="text-sm text-muted">No incidents yet.</div>
                ) : (
                  incidents.map((inc) => (
                    <Link
                      key={inc.id}
                      href={`/incidents/${inc.id}`}
                      className="flex items-start justify-between gap-3 rounded-lg border border-[var(--border)] bg-black/20 px-3 py-2 hover:border-[var(--border-strong)]"
                    >
                      <div className="min-w-0">
                        <div className="truncate text-sm font-medium">{inc.title}</div>
                        <div className="text-xs text-muted">
                          {inc.service_names.join(", ")} · {inc.status}
                        </div>
                      </div>
                      <SeverityBadge severity={inc.severity} />
                    </Link>
                  ))
                )}
              </div>
            </div>
          </div>
        </>
      ) : (
        <div className="text-muted">Loading overview…</div>
      )}
    </div>
  );
}
