"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { PageHeader } from "@/components/PageHeader";
import { StatusPill } from "@/components/ui/StatusPill";
import { api } from "@/lib/api";
import type { Investigation, Paginated } from "@/lib/types";

export default function InvestigationsPage() {
  const [items, setItems] = useState<Investigation[]>([]);

  useEffect(() => {
    void api<Paginated<Investigation>>("/investigations").then((p) => setItems(p.items));
  }, []);

  return (
    <div>
      <PageHeader
        title="AI Investigations"
        description="Multi-agent investigation runs with checkpoints and evidence-linked RCA."
      />
      <div className="panel overflow-hidden">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-[var(--border)] text-xs uppercase tracking-wide text-muted">
            <tr>
              <th className="px-4 py-3">Investigation</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Provider</th>
              <th className="px-4 py-3">Step</th>
              <th className="px-4 py-3">Started</th>
            </tr>
          </thead>
          <tbody>
            {items.map((inv) => (
              <tr key={inv.id} className="border-b border-[var(--border)]/70">
                <td className="px-4 py-3">
                  <Link
                    href={`/investigations/${inv.id}`}
                    className="font-mono text-xs hover:text-[var(--accent)]"
                  >
                    {inv.id.slice(0, 8)}…
                  </Link>
                </td>
                <td className="px-4 py-3">
                  <StatusPill status={inv.status} />
                </td>
                <td className="px-4 py-3 text-xs">
                  {inv.provider}/{inv.model}
                </td>
                <td className="px-4 py-3 font-mono text-xs text-muted">
                  {inv.current_step}
                </td>
                <td className="px-4 py-3 text-xs text-muted">
                  {new Date(inv.started_at).toLocaleString()}
                </td>
              </tr>
            ))}
            {items.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-muted">
                  No investigations yet.
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </div>
  );
}
