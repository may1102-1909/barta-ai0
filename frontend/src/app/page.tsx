"use client";

import React, { useCallback } from "react";
import Link from "next/link";
import { PhoneCall, PhoneForwarded, CheckCircle2, CalendarClock, Clock, ArrowRight, Play, Pause, Megaphone } from "lucide-react";
import { api } from "@/lib/api";
import { usePolling } from "@/lib/hooks";
import { EMPTY_STATS, type Campaign, type CampaignStats } from "@/lib/types";
import { formatCurrency, formatDateTime, formatSeconds, percent } from "@/lib/utils";
import { Card, CardHeader, StatCard } from "@/components/ui/Card";
import { StatusChip } from "@/components/ui/Status";
import { EmptyState, ErrorBanner, TableSkeleton } from "@/components/ui/Feedback";
import { Button, buttonClass } from "@/components/ui/Button";
import { PageHeader } from "@/components/ui/PageHeader";

function aggregate(stats: CampaignStats[]): CampaignStats {
  if (stats.length === 0) return EMPTY_STATS;
  const total = stats.reduce<CampaignStats>(
    (acc, s) => ({
      funnel: {
        contacts: acc.funnel.contacts + s.funnel.contacts,
        called: acc.funnel.called + s.funnel.called,
        connected: acc.funnel.connected + s.funnel.connected,
        interested: acc.funnel.interested + s.funnel.interested,
        order_confirmed: acc.funnel.order_confirmed + s.funnel.order_confirmed,
      },
      counters: {
        total_calls: acc.counters.total_calls + s.counters.total_calls,
        connected_calls: acc.counters.connected_calls + s.counters.connected_calls,
        orders_confirmed: acc.counters.orders_confirmed + s.counters.orders_confirmed,
        callbacks_pending: acc.counters.callbacks_pending + s.counters.callbacks_pending,
        // weighted by connected calls so the average stays meaningful across campaigns
        avg_duration_sec: acc.counters.avg_duration_sec + s.counters.avg_duration_sec * s.counters.connected_calls,
      },
    }),
    EMPTY_STATS
  );
  total.counters.avg_duration_sec = total.counters.connected_calls
    ? total.counters.avg_duration_sec / total.counters.connected_calls
    : 0;
  return total;
}

const FUNNEL_STEPS: { key: keyof CampaignStats["funnel"]; label: string }[] = [
  { key: "contacts", label: "Contacts" },
  { key: "called", label: "Called" },
  { key: "connected", label: "Connected" },
  { key: "interested", label: "Interested" },
  { key: "order_confirmed", label: "Confirmed" },
];

export default function OverviewPage() {
  const load = useCallback(async () => {
    const [campaigns, calls, orders] = await Promise.all([
      api.getCampaigns(),
      api.getCalls({ limit: 6 }),
      api.getOrders({ limit: 5 }),
    ]);
    const stats = await Promise.all(campaigns.map((c) => api.getCampaignStats(c.id)));
    return { campaigns, calls, orders, stats: aggregate(stats) };
  }, []);

  const { data, loading, error, refresh } = usePolling(load, [], { intervalMs: 6000 });
  const campaigns = data?.campaigns ?? [];
  const calls = data?.calls ?? [];
  const orders = data?.orders ?? [];
  const { funnel, counters } = data?.stats ?? EMPTY_STATS;

  const toggle = async (camp: Campaign) => {
    if (camp.status === "active") await api.pauseCampaign(camp.id);
    else await api.startCampaign(camp.id);
    refresh();
  };

  return (
    <div className="space-y-6 pb-12">
      <PageHeader
        title="Overview"
        actions={
          <>
            <Link href="/campaigns" className={buttonClass("secondary", "sm")}>
              Campaigns
            </Link>
            <Link href="/simulator" className={buttonClass("primary", "sm")}>
              Run simulator
            </Link>
          </>
        }
      />

      <ErrorBanner message={error} />

      <div className="grid grid-cols-2 gap-3 sm:gap-4 md:grid-cols-3 xl:grid-cols-5">
        <StatCard label="Calls" value={counters.total_calls} icon={<PhoneCall className="h-4 w-4" />} loading={loading} />
        <StatCard
          label="Connected"
          value={counters.connected_calls}
          hint={`${percent(counters.connected_calls, counters.total_calls)}% reach`}
          icon={<PhoneForwarded className="h-4 w-4" />}
          loading={loading}
        />
        <StatCard label="Orders" value={counters.orders_confirmed} icon={<CheckCircle2 className="h-4 w-4" />} loading={loading} />
        <StatCard label="Callbacks" value={counters.callbacks_pending} hint="Pending" icon={<CalendarClock className="h-4 w-4" />} loading={loading} />
        <StatCard
          label="Avg duration"
          value={formatSeconds(counters.avg_duration_sec)}
          icon={<Clock className="h-4 w-4" />}
          loading={loading}
        />
      </div>

      <Card>
        <CardHeader title="Funnel" />
        <div className="grid grid-cols-2 gap-3 px-5 pb-5 sm:grid-cols-3 sm:px-6 lg:grid-cols-5">
          {FUNNEL_STEPS.map((step, idx) => {
            const count = funnel[step.key];
            const pct = idx === 0 ? (funnel.contacts ? 100 : 0) : percent(count, funnel.contacts);
            return (
              <div key={step.key} className="rounded-xl border border-slate-200/80 bg-white p-4">
                <div className="flex items-center justify-between text-[11px] font-semibold uppercase tracking-wider text-slate-500">
                  <span>{step.label}</span>
                  <span className="tabular-nums text-navy-900">{pct}%</span>
                </div>
                <div className="mt-1 text-xl font-bold tabular-nums text-navy-900">{count}</div>
                <div className="mt-3 h-1 w-full overflow-hidden rounded-full bg-slate-100">
                  <div className="h-full rounded-full bg-navy-900 transition-all" style={{ width: `${pct}%` }} />
                </div>
              </div>
            );
          })}
        </div>
      </Card>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3 lg:gap-6">
        <Card className="lg:col-span-2">
          <CardHeader
            title="Campaigns"
            action={
              <Link href="/campaigns" className="flex items-center gap-1 text-xs font-semibold text-slate-500 hover:text-navy-900">
                All <ArrowRight className="h-3.5 w-3.5" />
              </Link>
            }
          />
          <div className="px-5 pb-5 sm:px-6">
            {loading ? (
              <TableSkeleton rows={3} cols={3} />
            ) : campaigns.length === 0 ? (
              <EmptyState
                icon={<Megaphone className="h-6 w-6" />}
                title="No campaigns yet"
                action={
                  <Link href="/campaigns" className={buttonClass("primary", "sm")}>
                    Create campaign
                  </Link>
                }
              />
            ) : (
              <div className="space-y-2.5">
                {campaigns.slice(0, 3).map((camp) => (
                  <div
                    key={camp.id}
                    className="flex flex-col gap-3 rounded-xl border border-slate-200/80 bg-white p-4 sm:flex-row sm:items-center sm:justify-between"
                  >
                    <div className="min-w-0 space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="truncate text-sm font-semibold text-navy-900">{camp.name}</span>
                        <StatusChip status={camp.status} />
                      </div>
                      <div className="flex flex-wrap gap-x-3 gap-y-1 text-[11px] font-medium text-slate-500">
                        <span>
                          {camp.window_start}–{camp.window_end} IST
                        </span>
                        <span>×{camp.max_concurrent} concurrent</span>
                        <span>{camp.total_contacts ?? 0} contacts</span>
                      </div>
                    </div>
                    <Button
                      size="sm"
                      variant={camp.status === "active" ? "secondary" : "primary"}
                      onClick={() => toggle(camp)}
                      icon={camp.status === "active" ? <Pause className="h-3.5 w-3.5" /> : <Play className="h-3.5 w-3.5 fill-current" />}
                    >
                      {camp.status === "active" ? "Pause" : "Start"}
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </Card>

        <Card>
          <CardHeader
            title="Recent orders"
            action={
              <Link href="/orders" className="flex items-center gap-1 text-xs font-semibold text-slate-500 hover:text-navy-900">
                All <ArrowRight className="h-3.5 w-3.5" />
              </Link>
            }
          />
          <div className="px-5 pb-5 sm:px-6">
            {loading ? (
              <TableSkeleton rows={3} cols={2} />
            ) : orders.length === 0 ? (
              <EmptyState title="No orders yet" />
            ) : (
              <div className="space-y-2.5">
                {orders.map((ord) => (
                  <div key={ord.id} className="flex items-center justify-between gap-3 rounded-xl border border-slate-200/80 bg-white p-3">
                    <div className="min-w-0">
                      <div className="truncate text-xs font-semibold text-navy-900">{ord.customer_name}</div>
                      <div className="truncate text-[11px] text-slate-500">
                        {formatCurrency(ord.total_price)} · {ord.product_name}
                      </div>
                    </div>
                    <StatusChip status={ord.status} />
                  </div>
                ))}
              </div>
            )}
          </div>
        </Card>
      </div>

      <Card className="overflow-hidden">
        <CardHeader
          title="Recent calls"
          action={
            <Link href="/calls" className="flex items-center gap-1 text-xs font-semibold text-slate-500 hover:text-navy-900">
              All <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          }
        />
        {loading ? (
          <TableSkeleton rows={4} cols={5} />
        ) : calls.length === 0 ? (
          <div className="px-5 pb-5 sm:px-6">
            <EmptyState title="No calls yet" />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[640px] text-left text-xs">
              <thead className="border-y border-slate-200/80 bg-white text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                <tr>
                  <th className="px-5 py-2.5 sm:px-6">Contact</th>
                  <th className="px-4 py-2.5">Outcome</th>
                  <th className="px-4 py-2.5">Duration</th>
                  <th className="px-4 py-2.5">Started</th>
                  <th className="px-4 py-2.5">Summary</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 bg-white text-slate-700">
                {calls.map((c) => (
                  <tr key={c.id} className="transition hover:bg-slate-50">
                    <td className="px-5 py-3 sm:px-6">
                      <div className="font-semibold text-navy-900">{c.contact_name}</div>
                      <div className="font-mono text-[11px] text-slate-400">{c.contact_phone}</div>
                    </td>
                    <td className="px-4 py-3">
                      <StatusChip status={c.outcome} />
                    </td>
                    <td className="px-4 py-3 font-mono tabular-nums">{formatSeconds(c.duration_sec)}</td>
                    <td className="px-4 py-3 text-slate-500">{formatDateTime(c.started_at)}</td>
                    <td className="max-w-xs truncate px-4 py-3 text-slate-600">{c.summary || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
