import { cn } from "@/lib/cn";
import type { Severity } from "@/lib/types";

const styles: Record<string, string> = {
  critical: "bg-[var(--critical)]/15 text-[var(--critical)] border-[var(--critical)]/30",
  high: "bg-[var(--high)]/15 text-[var(--high)] border-[var(--high)]/30",
  medium: "bg-[var(--medium)]/15 text-[var(--medium)] border-[var(--medium)]/30",
  low: "bg-[var(--low)]/15 text-[var(--low)] border-[var(--low)]/30",
  info: "bg-[var(--info)]/15 text-[var(--info)] border-[var(--info)]/30",
};

export function SeverityBadge({
  severity,
  className,
}: {
  severity: Severity | string;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-md border px-2 py-0.5 text-[11px] font-medium uppercase tracking-wide",
        styles[severity] || styles.info,
        className,
      )}
    >
      {severity}
    </span>
  );
}
