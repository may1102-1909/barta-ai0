import React from "react";
import { cn } from "@/lib/utils";

export function Card({ className, children, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("rounded-2xl border border-slate-200/80 bg-slate-50 shadow-card", className)}
      {...props}
    >
      {children}
    </div>
  );
}

export function CardHeader({
  title,
  action,
  className,
}: {
  title: React.ReactNode;
  action?: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("flex items-center justify-between gap-3 px-5 pt-5 pb-3 sm:px-6", className)}>
      <h3 className="text-sm font-semibold tracking-tight text-navy-900">{title}</h3>
      {action}
    </div>
  );
}

export function StatCard({
  label,
  value,
  hint,
  icon,
  loading,
}: {
  label: string;
  value: React.ReactNode;
  hint?: React.ReactNode;
  icon?: React.ReactNode;
  loading?: boolean;
}) {
  return (
    <Card className="p-5">
      <div className="mb-3 flex items-center justify-between text-slate-500">
        <span className="text-[11px] font-semibold uppercase tracking-[0.14em]">{label}</span>
        {icon && <span className="text-navy-900/70">{icon}</span>}
      </div>
      {loading ? (
        <div className="h-8 w-20 animate-pulse rounded-md bg-slate-200/80" />
      ) : (
        <div className="text-2xl font-bold tabular-nums tracking-tight text-navy-900">{value}</div>
      )}
      {hint && <p className="mt-1 text-[11px] font-medium text-slate-500">{hint}</p>}
    </Card>
  );
}
