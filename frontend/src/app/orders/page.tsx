"use client";

import React, { useState } from "react";
import { ShoppingBag, ExternalLink, MapPin, Copy, Check } from "lucide-react";
import { api } from "@/lib/api";
import { usePolling } from "@/lib/hooks";
import { formatCurrency } from "@/lib/utils";
import { Card } from "@/components/ui/Card";
import { StatusChip } from "@/components/ui/Status";
import { EmptyState, ErrorBanner, TableSkeleton } from "@/components/ui/Feedback";
import { PageHeader } from "@/components/ui/PageHeader";
import { FilterSelect } from "@/components/ui/Form";

const STATUSES = [
  ["", "All statuses"],
  ["awaiting_details", "Awaiting details"],
  ["details_received", "Details received"],
  ["cod", "Cash on delivery"],
  ["paid", "Paid"],
];

export default function OrdersPage() {
  const [status, setStatus] = useState("");
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const { data, loading, error } = usePolling(() => api.getOrders({ status: status || undefined }), [status], { intervalMs: 5000 });
  const orders = data ?? [];

  const copy = async (url: string, id: string) => {
    await navigator.clipboard.writeText(url);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 1500);
  };

  return (
    <div className="space-y-6 pb-12">
      <PageHeader
        title="Orders"
        actions={
          <FilterSelect value={status} onChange={(e) => setStatus(e.target.value)} aria-label="Filter by status">
            {STATUSES.map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </FilterSelect>
        }
      />

      <ErrorBanner message={error} />

      <Card className="overflow-hidden">
        {loading ? (
          <TableSkeleton rows={5} cols={5} />
        ) : orders.length === 0 ? (
          <div className="p-5">
            <EmptyState icon={<ShoppingBag className="h-6 w-6" />} title="No orders yet" />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[720px] text-left text-xs">
              <thead className="border-b border-slate-200/80 bg-white text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                <tr>
                  <th className="px-5 py-2.5">Customer</th>
                  <th className="px-4 py-2.5">Product</th>
                  <th className="px-4 py-2.5">Total</th>
                  <th className="px-4 py-2.5">Status</th>
                  <th className="px-4 py-2.5">Address</th>
                  <th className="px-4 py-2.5 text-right">Form</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 bg-white text-slate-700">
                {orders.map((ord) => (
                  <tr key={ord.id} className="transition hover:bg-slate-50">
                    <td className="px-5 py-3">
                      <div className="font-semibold text-navy-900">{ord.customer_name}</div>
                      <div className="text-[11px] text-slate-400">{ord.customer_email || ord.customer_phone || "—"}</div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="font-medium text-navy-900">{ord.product_name}</div>
                      <div className="text-[11px] text-slate-400">× {ord.quantity}</div>
                    </td>
                    <td className="px-4 py-3 font-mono font-semibold tabular-nums text-navy-900">{formatCurrency(ord.total_price)}</td>
                    <td className="px-4 py-3">
                      <StatusChip status={ord.status} />
                    </td>
                    <td className="max-w-xs px-4 py-3 text-slate-600">
                      {ord.delivery_address ? (
                        <span className="flex items-start gap-1">
                          <MapPin className="mt-0.5 h-3.5 w-3.5 shrink-0 text-slate-400" />
                          <span className="line-clamp-2">{ord.delivery_address}</span>
                        </span>
                      ) : (
                        <span className="text-[11px] text-slate-400">Pending</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      {ord.form_url ? (
                        <div className="flex items-center justify-end gap-1">
                          <a
                            href={ord.form_url}
                            target="_blank"
                            rel="noreferrer"
                            className="inline-flex items-center gap-1 rounded-md border border-slate-200/80 bg-white px-2 py-1 font-semibold text-navy-900 hover:bg-slate-50"
                          >
                            Open <ExternalLink className="h-3 w-3" />
                          </a>
                          <button
                            onClick={() => copy(ord.form_url!, ord.id)}
                            title="Copy link"
                            aria-label="Copy form link"
                            className="rounded-md p-1.5 text-slate-400 hover:bg-slate-100 hover:text-navy-900"
                          >
                            {copiedId === ord.id ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
                          </button>
                        </div>
                      ) : (
                        <span className="block text-right text-slate-400">—</span>
                      )}
                    </td>
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
