"use client";

import { useEffect, useState } from "react";
import { PageHeader } from "@/components/PageHeader";
import { StatusPill } from "@/components/ui/StatusPill";
import { api } from "@/lib/api";
import type { Paginated, Service } from "@/lib/types";

type Dep = {
  id: string;
  source_name?: string | null;
  target_name?: string | null;
  dependency_type: string;
};

export default function ServicesPage() {
  const [services, setServices] = useState<Service[]>([]);
  const [deps, setDeps] = useState<Dep[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void (async () => {
      try {
        const [svc, d] = await Promise.all([
          api<Paginated<Service>>("/services"),
          api<Dep[]>("/services/dependencies"),
        ]);
        setServices(svc.items.filter((s) => s.base_url));
        setDeps(d);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load services");
      }
    })();
  }, []);

  return (
    <div>
      <PageHeader
        title="Services"
        description="Simulated microservices and their dependency map."
      />
      {error ? (
        <div className="mb-4 text-sm text-[var(--critical)]">{error}</div>
      ) : null}
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        {services.map((s) => (
          <div key={s.id} className="panel p-4">
            <div className="flex items-start justify-between gap-2">
              <div>
                <div className="font-medium">{s.display_name}</div>
                <div className="font-mono text-xs text-muted">{s.name}</div>
              </div>
              <StatusPill status={s.status} />
            </div>
            <div className="mt-3 text-xs text-muted">{s.base_url}</div>
          </div>
        ))}
      </div>

      <div className="panel mt-6 p-4">
        <h2 className="mb-3 text-sm font-medium">Dependency map</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="text-xs uppercase tracking-wide text-muted">
              <tr>
                <th className="pb-2">Source</th>
                <th className="pb-2">Target</th>
                <th className="pb-2">Type</th>
              </tr>
            </thead>
            <tbody>
              {deps.map((d) => (
                <tr key={d.id} className="border-t border-[var(--border)]">
                  <td className="py-2 font-mono text-xs">{d.source_name}</td>
                  <td className="py-2 font-mono text-xs">{d.target_name}</td>
                  <td className="py-2 text-muted">{d.dependency_type}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
