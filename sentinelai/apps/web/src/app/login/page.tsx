"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { Shield } from "lucide-react";
import { useAuth } from "@/components/AuthProvider";

export default function LoginPage() {
  const { login } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("admin@example.com");
  const [password, setPassword] = useState("ChangeMeAdmin123!");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await login(email, password);
      router.replace("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="relative z-10 flex min-h-screen items-center justify-center p-6">
      <div className="w-full max-w-md">
        <div className="mb-8 text-center">
          <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-[var(--accent)]/15 text-[var(--accent)]">
            <Shield className="h-7 w-7" />
          </div>
          <h1 className="font-[family-name:var(--font-display)] text-3xl font-semibold tracking-tight">
            SENTINELAI
          </h1>
          <p className="mt-2 text-sm text-muted">
            Sign in to the operations control plane
          </p>
        </div>
        <form onSubmit={onSubmit} className="panel space-y-4 p-6">
          <label className="block text-sm">
            <span className="text-muted">Email</span>
            <input
              className="mt-1 w-full rounded-lg border border-[var(--border)] bg-black/30 px-3 py-2 focus-ring"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              type="email"
              required
            />
          </label>
          <label className="block text-sm">
            <span className="text-muted">Password</span>
            <input
              className="mt-1 w-full rounded-lg border border-[var(--border)] bg-black/30 px-3 py-2 focus-ring"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              type="password"
              required
              minLength={8}
            />
          </label>
          {error ? (
            <div className="rounded-lg border border-[var(--critical)]/30 bg-[var(--critical)]/10 px-3 py-2 text-sm text-[var(--critical)]">
              {error}
            </div>
          ) : null}
          <button
            type="submit"
            disabled={busy}
            className="w-full rounded-lg bg-[var(--accent)] py-2.5 text-sm font-semibold text-[#04241c] disabled:opacity-60"
          >
            {busy ? "Signing in…" : "Sign in"}
          </button>
        </form>
      </div>
    </div>
  );
}
