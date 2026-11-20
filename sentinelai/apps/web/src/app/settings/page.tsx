"use client";

import { PageHeader } from "@/components/PageHeader";
import { useAuth } from "@/components/AuthProvider";
import { API_URL } from "@/lib/api";

export default function SettingsPage() {
  const { user } = useAuth();

  return (
    <div>
      <PageHeader
        title="Settings"
        description="Local demo configuration. Secrets stay in environment variables."
      />
      <div className="grid gap-4 md:grid-cols-2">
        <div className="panel p-4 text-sm">
          <h2 className="mb-3 font-medium">Session</h2>
          <dl className="space-y-2 text-muted">
            <div className="flex justify-between gap-4">
              <dt>User</dt>
              <dd className="text-[var(--text)]">{user?.email}</dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt>Role</dt>
              <dd className="text-[var(--text)]">{user?.role}</dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt>API</dt>
              <dd className="font-mono text-xs text-[var(--text)]">{API_URL}</dd>
            </div>
          </dl>
        </div>
        <div className="panel p-4 text-sm">
          <h2 className="mb-3 font-medium">Safety defaults</h2>
          <ul className="space-y-2 text-muted">
            <li>Remediation executes in simulator sandbox only</li>
            <li>LLM providers optional — deterministic fallback always available</li>
            <li>Evaluation scores are measured, never fabricated</li>
            <li>Dangerous actions require engineer/admin approval</li>
          </ul>
        </div>
        <div className="panel p-4 text-sm md:col-span-2">
          <h2 className="mb-3 font-medium">Demo walkthrough</h2>
          <ol className="list-decimal space-y-1 pl-5 text-muted">
            <li>Open Incidents → Run detection (or wait for scheduler)</li>
            <li>Open an incident → Start AI investigation</li>
            <li>Review Agent Execution evidence + RCA</li>
            <li>Remediation Center → Approve sandboxed fix</li>
            <li>Model Evaluation → Run deterministic dataset</li>
          </ol>
        </div>
      </div>
    </div>
  );
}
