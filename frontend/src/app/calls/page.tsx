"use client";

import React, { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { PhoneCall, X } from "lucide-react";
import { api } from "@/lib/api";
import { usePolling } from "@/lib/hooks";
import type { CallDetail } from "@/lib/types";
import { cn, formatDateTime, formatSeconds } from "@/lib/utils";
import { Card } from "@/components/ui/Card";
import { StatusChip } from "@/components/ui/Status";
import { EmptyState, ErrorBanner, Skeleton, TableSkeleton } from "@/components/ui/Feedback";
import { PageHeader } from "@/components/ui/PageHeader";
import { FilterSelect } from "@/components/ui/Form";
import { TranscriptThread } from "@/components/TranscriptThread";

const OUTCOMES = [
  ["", "All outcomes"],
  ["order_confirmed", "Order confirmed"],
  ["interested", "Interested"],
  ["callback_requested", "Callback requested"],
  ["not_interested", "Not interested"],
  ["do_not_call", "Do not call"],
  ["no_answer", "No answer"],
];

function CallsView() {
  const searchParams = useSearchParams();
  const [outcome, setOutcome] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(searchParams.get("call_id"));
  const [detail, setDetail] = useState<CallDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);

  const { data, loading, error } = usePolling(() => api.getCalls({ outcome: outcome || undefined, limit: 100 }), [outcome], {
    intervalMs: 8000,
  });
  const calls = data ?? [];

  useEffect(() => {
    if (!selectedId) {
      setDetail(null);
      return;
    }
    let cancelled = false;
    setDetailLoading(true);
    setDetailError(null);
    api
      .getCallDetail(selectedId)
      .then((d) => !cancelled && setDetail(d))
      .catch((e) => !cancelled && setDetailError(e instanceof Error ? e.message : "Could not load call"))
      .finally(() => !cancelled && setDetailLoading(false));
    return () => {
      cancelled = true;
    };
  }, [selectedId]);

  return (
    <div className="space-y-6 pb-12">
      <PageHeader
        title="Calls"
        actions={
          <FilterSelect value={outcome} onChange={(e) => setOutcome(e.target.value)} aria-label="Filter by outcome">
            {OUTCOMES.map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </FilterSelect>
        }
      />

      <ErrorBanner message={error} />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-12 lg:gap-6">
        <Card className={cn("overflow-hidden", selectedId ? "lg:col-span-6" : "lg:col-span-12")}>
          {loading ? (
            <TableSkeleton rows={6} cols={4} />
          ) : calls.length === 0 ? (
            <div className="p-5">
              <EmptyState icon={<PhoneCall className="h-6 w-6" />} title="No calls match this filter" />
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[560px] text-left text-xs">
                <thead className="border-b border-slate-200/80 bg-white text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                  <tr>
                    <th className="px-5 py-2.5">Contact</th>
                    <th className="px-4 py-2.5">Outcome</th>
                    <th className="px-4 py-2.5">Duration</th>
                    <th className="px-4 py-2.5">Started</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 bg-white text-slate-700">
                  {calls.map((c) => (
                    <tr
                      key={c.id}
                      onClick={() => setSelectedId(c.id)}
                      className={cn("cursor-pointer transition hover:bg-slate-50", selectedId === c.id && "bg-slate-50")}
                    >
                      <td className="px-5 py-3">
                        <div className="font-semibold text-navy-900">{c.contact_name}</div>
                        <div className="font-mono text-[11px] text-slate-400">{c.contact_phone}</div>
                      </td>
                      <td className="px-4 py-3">
                        <StatusChip status={c.outcome} />
                      </td>
                      <td className="px-4 py-3 font-mono tabular-nums">{formatSeconds(c.duration_sec)}</td>
                      <td className="px-4 py-3 text-slate-500">{formatDateTime(c.started_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>

        {selectedId && (
          <Card className="animate-fade-in p-5 lg:col-span-6 sm:p-6">
            <div className="mb-4 flex items-center justify-between border-b border-slate-200/80 pb-3">
              <div className="min-w-0">
                <h3 className="text-sm font-bold tracking-tight text-navy-900">Transcript</h3>
                <p className="truncate font-mono text-[11px] text-slate-400">{selectedId}</p>
              </div>
              <button
                onClick={() => setSelectedId(null)}
                aria-label="Close transcript"
                className="rounded-md p-1 text-slate-400 hover:bg-slate-100 hover:text-navy-900"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <ErrorBanner message={detailError} className="mb-3" />

            {detailLoading ? (
              <div className="space-y-3">
                <Skeleton className="h-20" />
                <Skeleton className="h-10 w-3/4" />
                <Skeleton className="ml-auto h-10 w-2/3" />
                <Skeleton className="h-10 w-3/4" />
              </div>
            ) : detail ? (
              <div className="space-y-4">
                <div className="space-y-2 rounded-xl border border-slate-200/80 bg-white p-4 text-xs">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-sm font-semibold text-navy-900">{detail.contact_name}</span>
                    <StatusChip status={detail.outcome} />
                  </div>
                  <div className="flex flex-wrap gap-x-3 gap-y-1 text-[11px] text-slate-500">
                    <span className="font-mono">{detail.contact_phone}</span>
                    {detail.language_preferred && <span className="capitalize">{detail.language_preferred}</span>}
                    <span>{formatSeconds(detail.duration_sec)}</span>
                  </div>
                  {detail.summary && (
                    <p className="border-t border-slate-100 pt-2 leading-relaxed text-slate-700">{detail.summary}</p>
                  )}
                </div>
                <div className="max-h-[480px] overflow-y-auto pr-1">
                  <TranscriptThread turns={detail.transcript ?? []} contactName={detail.contact_name} dense />
                </div>
              </div>
            ) : null}
          </Card>
        )}
      </div>
    </div>
  );
}

export default function CallsPage() {
  return (
    <Suspense fallback={<TableSkeleton rows={6} cols={4} />}>
      <CallsView />
    </Suspense>
  );
}
