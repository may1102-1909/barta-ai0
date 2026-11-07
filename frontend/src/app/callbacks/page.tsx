"use client";

import React, { useState } from "react";
import { CalendarClock, Clock } from "lucide-react";
import { api } from "@/lib/api";
import { usePolling } from "@/lib/hooks";
import { Card } from "@/components/ui/Card";
import { StatusChip } from "@/components/ui/Status";
import { EmptyState, ErrorBanner, Skeleton } from "@/components/ui/Feedback";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { PageHeader } from "@/components/ui/PageHeader";
import { Field, FilterSelect, Input } from "@/components/ui/Form";

const STATUSES = [
  ["", "All callbacks"],
  ["pending", "Pending"],
  ["in_progress", "In progress"],
  ["done", "Completed"],
  ["cancelled", "Cancelled"],
];

export default function CallbacksPage() {
  const [status, setStatus] = useState("");
  const [rescheduleId, setRescheduleId] = useState<string | null>(null);
  const [newDateTime, setNewDateTime] = useState("");
  const [actionError, setActionError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const { data, loading, error, refresh } = usePolling(() => api.getCallbacks({ status: status || undefined }), [status], {
    intervalMs: 8000,
  });
  const callbacks = data ?? [];

  const handleReschedule = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!rescheduleId || !newDateTime) return;
    setSaving(true);
    setActionError(null);
    try {
      await api.rescheduleCallback(rescheduleId, new Date(newDateTime).toISOString());
      setRescheduleId(null);
      refresh();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Could not reschedule");
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = async (id: string) => {
    if (!confirm("Cancel this callback?")) return;
    try {
      await api.cancelCallback(id);
      refresh();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Could not cancel");
    }
  };

  return (
    <div className="space-y-6 pb-12">
      <PageHeader
        title="Callbacks"
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

      <ErrorBanner message={error || actionError} />

      {loading ? (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {[0, 1, 2].map((i) => (
            <Card key={i} className="space-y-3 p-5">
              <Skeleton className="h-4 w-32" />
              <Skeleton className="h-3 w-24" />
              <Skeleton className="h-14" />
            </Card>
          ))}
        </div>
      ) : callbacks.length === 0 ? (
        <EmptyState icon={<CalendarClock className="h-6 w-6" />} title="No callbacks scheduled" />
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {callbacks.map((cb) => (
            <Card key={cb.id} className="flex flex-col justify-between p-5">
              <div>
                <div className="flex items-center justify-between gap-2">
                  <h3 className="truncate text-sm font-semibold text-navy-900">{cb.contact_name}</h3>
                  <StatusChip status={cb.status} />
                </div>
                <div className="mt-0.5 font-mono text-[11px] text-slate-400">{cb.contact_phone}</div>
                {cb.reason && (
                  <p className="mt-4 rounded-xl border border-slate-200/80 bg-white p-3 text-xs italic leading-relaxed text-slate-600">
                    “{cb.reason}”
                  </p>
                )}
              </div>
              <div className="mt-4 flex items-center justify-between border-t border-slate-200/80 pt-3 text-xs">
                <span className="flex items-center gap-1.5 font-medium text-slate-500">
                  <Clock className="h-3.5 w-3.5" />
                  {cb.due_at_ist || "—"}
                </span>
                {cb.status === "pending" && (
                  <div className="flex items-center gap-1">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => {
                        setRescheduleId(cb.id);
                        setNewDateTime("");
                      }}
                    >
                      Reschedule
                    </Button>
                    <Button variant="ghost" size="sm" className="text-red-600 hover:bg-red-50 hover:text-red-700" onClick={() => handleCancel(cb.id)}>
                      Cancel
                    </Button>
                  </div>
                )}
              </div>
            </Card>
          ))}
        </div>
      )}

      <Modal open={!!rescheduleId} onClose={() => setRescheduleId(null)} title="Reschedule callback" className="max-w-sm">
        <form onSubmit={handleReschedule} className="space-y-4">
          <Field label="New time (IST)">
            <Input type="datetime-local" required value={newDateTime} onChange={(e) => setNewDateTime(e.target.value)} />
          </Field>
          <div className="flex justify-end gap-2">
            <Button type="button" variant="secondary" onClick={() => setRescheduleId(null)}>
              Cancel
            </Button>
            <Button type="submit" disabled={saving}>
              {saving ? "Saving…" : "Save"}
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
