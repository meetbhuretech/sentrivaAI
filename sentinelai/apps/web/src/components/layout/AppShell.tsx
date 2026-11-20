"use client";

import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/components/AuthProvider";
import { Sidebar } from "@/components/layout/Sidebar";

export function AppShell({ children }: { children: React.ReactNode }) {
  const { user, loading, logout } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (!loading && !user && pathname !== "/login") {
      router.replace("/login");
    }
  }, [loading, user, pathname, router]);

  if (pathname === "/login") {
    return <>{children}</>;
  }

  if (loading || !user) {
    return (
      <div className="relative z-10 flex min-h-screen items-center justify-center text-muted">
        Loading control plane…
      </div>
    );
  }

  return (
    <div className="relative z-10 flex min-h-screen">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between border-b border-[var(--border)] bg-[var(--bg-elevated)]/60 px-6 py-3 backdrop-blur">
          <div className="text-sm text-muted">
            Environment <span className="text-[var(--text)]">local</span>
          </div>
          <div className="flex items-center gap-4 text-sm">
            <div className="text-right">
              <div className="font-medium">{user.full_name}</div>
              <div className="text-xs uppercase tracking-wide text-muted">
                {user.role}
              </div>
            </div>
            <button
              type="button"
              onClick={() => {
                logout();
                router.replace("/login");
              }}
              className="rounded-lg border border-[var(--border)] px-3 py-1.5 text-xs text-muted hover:border-[var(--border-strong)] hover:text-[var(--text)]"
            >
              Sign out
            </button>
          </div>
        </header>
        <main className="flex-1 overflow-auto p-6">{children}</main>
      </div>
    </div>
  );
}
