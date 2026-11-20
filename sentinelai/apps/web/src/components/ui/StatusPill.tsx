import { cn } from "@/lib/cn";

export function StatusPill({
  status,
  className,
}: {
  status: string;
  className?: string;
}) {
  const tone =
    status.includes("healthy") ||
    status === "succeeded" ||
    status === "resolved" ||
    status === "completed"
      ? "text-[var(--accent)] border-[var(--accent)]/30 bg-[var(--accent)]/10"
      : status.includes("fail") ||
          status === "critical" ||
          status === "unhealthy" ||
          status === "rejected"
        ? "text-[var(--critical)] border-[var(--critical)]/30 bg-[var(--critical)]/10"
        : "text-[var(--high)] border-[var(--high)]/30 bg-[var(--high)]/10";

  return (
    <span
      className={cn(
        "inline-flex rounded-md border px-2 py-0.5 text-[11px] font-medium uppercase tracking-wide",
        tone,
        className,
      )}
    >
      {status.replaceAll("_", " ")}
    </span>
  );
}
