import React from "react";
import { cn, humanize } from "@/lib/utils";

export type Tone = "live" | "navy" | "neutral" | "warn" | "danger";

const dotTone: Record<Tone, string> = {
  live: "bg-emerald-500 animate-glow",
  navy: "bg-navy-900",
  neutral: "bg-slate-400",
  warn: "bg-amber-500",
  danger: "bg-red-500",
};

export function LiveDot({ tone = "live", className }: { tone?: Tone; className?: string }) {
  return <span className={cn("inline-block h-1.5 w-1.5 shrink-0 rounded-full", dotTone[tone], className)} />;
}

const TONES: Record<string, Tone> = {
  active: "live",
  in_progress: "live",
  connected: "live",
  order_confirmed: "navy",
  paid: "navy",
  cod: "navy",
  done: "navy",
  completed: "navy",
  details_received: "navy",
  interested: "navy",
  paused: "warn",
  pending: "warn",
  callback_requested: "warn",
  awaiting_details: "warn",
  no_answer: "warn",
  do_not_call: "danger",
  cancelled: "danger",
  stopped: "danger",
  error: "danger",
  offline: "danger",
};

export function toneFor(status?: string | null): Tone {
  return (status && TONES[status]) || "neutral";
}

export function StatusChip({
  status,
  label,
  tone,
  className,
}: {
  status?: string | null;
  label?: string;
  tone?: Tone;
  className?: string;
}) {
  const resolved = tone ?? toneFor(status);
  const filled = resolved === "navy";
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 whitespace-nowrap rounded-md border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider",
        filled ? "border-navy-900 bg-navy-900 text-white" : "border-slate-200/80 bg-white text-navy-900",
        className
      )}
    >
      <LiveDot tone={resolved} className={filled ? "bg-white" : undefined} />
      {label ?? humanize(status, "in progress")}
    </span>
  );
}
