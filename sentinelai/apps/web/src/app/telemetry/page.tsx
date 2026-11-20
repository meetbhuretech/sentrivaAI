"use client";

import { useState } from "react";
import { PageHeader } from "@/components/PageHeader";
import { api } from "@/lib/api";
import type { Paginated } from "@/lib/types";

type LogRow = {
  id: string;
  timestamp: string;
  service_name: string;
  level: string;
  message: string;
  trace_id?: string | null;
};

type MetricRow = {
  id: string;
  timestamp: string;
  service_name: string;
  metric_name: string;
  value: number;
};

export default function TelemetryPage() {
  const [tab, setTab] = useState<"logs" | "metrics" | "traces">("logs");
  const [service, setService] = useState("");
  const [q, setQ] = useState("");
  const [logs, setLogs] = useState<LogRow[]>([]);
  const [metrics, setMetrics] = useState<MetricRow[]>([]);
  const [traces, setTraces] = useState<Array<Record<string, unknown>>>([]);
  const [error, setError] = useState<string | null>(null);

  async function search() {
    setError(null);
    try {
      const params = new URLSearchParams();
      if (service) params.set("service", service);
      if (tab === "logs" && q) params.set("q", q);
      params.set("page_size", "50");
      if (tab === "logs") {
        const page = await api<Paginated<LogRow>>(`/telemetry/logs?${params}`);
        setLogs(page.items);
      } else if (tab === "metrics") {
        const page = await api<Paginated<MetricRow>>(`/telemetry/metrics?${params}`);
        setMetrics(page.items);
      } else {
        const page = await api<Paginated<Record<string, unknown>>>(
          `/telemetry/traces?${params}`,
        );
        setTraces(page.items);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search failed");
    }
  }

  return (
    <div>
      <PageHeader
        title="Telemetry Explorer"
        description="Search persisted logs, metrics, and traces with filters."
      />
      <div className="mb-4 flex flex-wrap gap-2">
        {(["logs", "metrics", "traces"] as const).map((t) => (
          <button
            key={t}
            type="button"
            onClick={() => setTab(t)}
            className={`rounded-lg px-3 py-1.5 text-sm ${
              tab === t
                ? "bg-[var(--accent)]/15 text-[var(--accent)]"
                : "border border-[var(--border)] text-muted"
            }`}
          >
            {t}
          </button>
        ))}
        <input
          className="rounded-lg border border-[var(--border)] bg-black/30 px-3 py-1.5 text-sm"
          placeholder="service"
          value={service}
          onChange={(e) => setService(e.target.value)}
        />
        {tab === "logs" ? (
          <input
            className="min-w-[200px] rounded-lg border border-[var(--border)] bg-black/30 px-3 py-1.5 text-sm"
            placeholder="message contains…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
        ) : null}
        <button
          type="button"
          onClick={() => void search()}
          className="rounded-lg bg-[var(--accent)] px-3 py-1.5 text-sm font-medium text-[#04241c]"
        >
          Search
        </button>
      </div>
      {error ? <div className="mb-3 text-sm text-[var(--critical)]">{error}</div> : null}
      <div className="panel overflow-auto">
        {tab === "logs" ? (
          <table className="w-full text-left text-sm">
            <thead className="text-xs uppercase text-muted">
              <tr>
                <th className="px-3 py-2">Time</th>
                <th className="px-3 py-2">Service</th>
                <th className="px-3 py-2">Level</th>
                <th className="px-3 py-2">Message</th>
              </tr>
            </thead>
            <tbody>
              {logs.map((l) => (
                <tr key={l.id} className="border-t border-[var(--border)]">
                  <td className="px-3 py-2 text-xs text-muted">
                    {new Date(l.timestamp).toLocaleString()}
                  </td>
                  <td className="px-3 py-2 font-mono text-xs">{l.service_name}</td>
                  <td className="px-3 py-2">{l.level}</td>
                  <td className="px-3 py-2">{l.message}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : null}
        {tab === "metrics" ? (
          <table className="w-full text-left text-sm">
            <thead className="text-xs uppercase text-muted">
              <tr>
                <th className="px-3 py-2">Time</th>
                <th className="px-3 py-2">Service</th>
                <th className="px-3 py-2">Metric</th>
                <th className="px-3 py-2">Value</th>
              </tr>
            </thead>
            <tbody>
              {metrics.map((m) => (
                <tr key={m.id} className="border-t border-[var(--border)]">
                  <td className="px-3 py-2 text-xs text-muted">
                    {new Date(m.timestamp).toLocaleString()}
                  </td>
                  <td className="px-3 py-2 font-mono text-xs">{m.service_name}</td>
                  <td className="px-3 py-2 font-mono text-xs">{m.metric_name}</td>
                  <td className="px-3 py-2 tabular-nums">{m.value}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : null}
        {tab === "traces" ? (
          <table className="w-full text-left text-sm">
            <thead className="text-xs uppercase text-muted">
              <tr>
                <th className="px-3 py-2">Trace</th>
                <th className="px-3 py-2">Service</th>
                <th className="px-3 py-2">Status</th>
                <th className="px-3 py-2">Duration</th>
              </tr>
            </thead>
            <tbody>
              {traces.map((t) => (
                <tr key={String(t.id)} className="border-t border-[var(--border)]">
                  <td className="px-3 py-2 font-mono text-xs">{String(t.trace_id)}</td>
                  <td className="px-3 py-2 font-mono text-xs">{String(t.service_name)}</td>
                  <td className="px-3 py-2">{String(t.status)}</td>
                  <td className="px-3 py-2 tabular-nums">{String(t.duration_ms ?? "—")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : null}
      </div>
    </div>
  );
}
