"use client";

import { useEffect, useState } from "react";
import { PageHeader } from "@/components/PageHeader";
import { useAuth } from "@/components/AuthProvider";
import { api } from "@/lib/api";
import type { Paginated } from "@/lib/types";

type AuditEvent = {
  id: string;
  action: string;
  resource_type?: string | null;
  resource_id?: string | null;
  actor_user_id?: string | null;
  created_at: string;
  details?: Record<string, unknown>;
};

export default function AuditPage() {
  const { user } = useAuth();
  const [items, setItems] = useState<AuditEvent[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (user?.role !== "admin") {
      setError("Admin role required to view audit logs.");
      return;
    }
    void api<Paginated<AuditEvent>>("/audit")
      .then((p) => setItems(p.items))
      .catch((err) => setError(err instanceof Error ? err.message : "Failed"));
  }, [user]);

  return (
    <div>
      <PageHeader
        title="Audit Logs"
        description="Privileged actions with redacted details."
      />
      {error ? (
        <div className="text-sm text-[var(--critical)]">{error}</div>
      ) : (
        <div className="panel overflow-hidden">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-[var(--border)] text-xs uppercase text-muted">
              <tr>
                <th className="px-4 py-3">Time</th>
                <th className="px-4 py-3">Action</th>
                <th className="px-4 py-3">Resource</th>
                <th className="px-4 py-3">Actor</th>
              </tr>
            </thead>
            <tbody>
              {items.map((e) => (
                <tr key={e.id} className="border-b border-[var(--border)]/70">
                  <td className="px-4 py-3 text-xs text-muted">
                    {new Date(e.created_at).toLocaleString()}
                  </td>
                  <td className="px-4 py-3 font-mono text-xs">{e.action}</td>
                  <td className="px-4 py-3 text-xs text-muted">
                    {e.resource_type}/{e.resource_id}
                  </td>
                  <td className="px-4 py-3 font-mono text-xs text-muted">
                    {e.actor_user_id?.slice(0, 8) || "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
