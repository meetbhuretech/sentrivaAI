"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  Bot,
  ClipboardList,
  Gauge,
  GitBranch,
  Radio,
  Settings,
  Shield,
  Siren,
  Wrench,
} from "lucide-react";
import { cn } from "@/lib/cn";

const nav = [
  { href: "/", label: "Overview", icon: Gauge },
  { href: "/services", label: "Services", icon: GitBranch },
  { href: "/incidents", label: "Incidents", icon: Siren },
  { href: "/investigations", label: "AI Investigations", icon: Bot },
  { href: "/telemetry", label: "Telemetry", icon: Radio },
  { href: "/remediation", label: "Remediation", icon: Wrench },
  { href: "/evaluation", label: "Model Evaluation", icon: Activity },
  { href: "/audit", label: "Audit Logs", icon: ClipboardList },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="relative z-10 flex w-60 shrink-0 flex-col border-r border-[var(--border)] bg-[var(--bg-elevated)]/80 backdrop-blur-md">
      <div className="flex items-center gap-3 border-b border-[var(--border)] px-5 py-5">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-[var(--accent)]/15 text-[var(--accent)]">
          <Shield className="h-5 w-5" />
        </div>
        <div>
          <div className="font-[family-name:var(--font-display)] text-lg font-semibold tracking-tight">
            SENTINELAI
          </div>
          <div className="text-[10px] uppercase tracking-[0.18em] text-muted">
            Ops Intelligence
          </div>
        </div>
      </div>
      <nav className="flex-1 space-y-1 p-3">
        {nav.map((item) => {
          const active =
            item.href === "/"
              ? pathname === "/"
              : pathname.startsWith(item.href);
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors",
                active
                  ? "bg-[var(--accent)]/12 text-[var(--accent)]"
                  : "text-muted hover:bg-white/5 hover:text-[var(--text)]",
              )}
            >
              <Icon className="h-4 w-4 shrink-0" />
              {item.label}
            </Link>
          );
        })}
      </nav>
      <div className="border-t border-[var(--border)] p-4 text-xs text-muted">
        Evidence-linked investigations
        <br />
        Human approval required
      </div>
    </aside>
  );
}
