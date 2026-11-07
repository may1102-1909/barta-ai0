"use client";

import React, { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { CheckCircle2, AlertCircle, Banknote, CreditCard } from "lucide-react";
import { api } from "@/lib/api";
import type { OrderForm, OrderFormSubmission } from "@/lib/types";
import { cn, formatCurrency } from "@/lib/utils";
import { Button } from "@/components/ui/Button";
import { ErrorBanner, Skeleton } from "@/components/ui/Feedback";
import { Field, Input, Textarea } from "@/components/ui/Form";

const STORE_URL = process.env.NEXT_PUBLIC_STORE_URL;

const PAYMENTS: { value: OrderFormSubmission["payment_method"]; label: string; icon: React.ReactNode }[] = [
  { value: "cod", label: "Cash on delivery", icon: <Banknote className="h-5 w-5" /> },
  { value: "razorpay", label: "Pay online", icon: <CreditCard className="h-5 w-5" /> },
];

function Shell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-white px-4 py-10">
      <div className="w-full max-w-xl rounded-3xl border border-slate-200/80 bg-slate-50 p-6 shadow-card sm:p-8">{children}</div>
    </div>
  );
}

function StoreLink({ label }: { label: string }) {
  if (!STORE_URL) return null;
  return (
    <a href={STORE_URL} target="_blank" rel="noreferrer" className="block text-xs font-semibold text-slate-500 hover:text-navy-900">
      {label}
    </a>
  );
}

export default function PublicOrderFormPage() {
  const params = useParams<{ token: string }>();
  const token = params?.token;

  const [order, setOrder] = useState<OrderForm | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);

  const [form, setForm] = useState<OrderFormSubmission>({
    customer_name: "",
    address: "",
    city: "",
    state: "",
    pincode: "",
    payment_method: "cod",
  });
  const update = <K extends keyof OrderFormSubmission>(key: K, value: OrderFormSubmission[K]) =>
    setForm((f) => ({ ...f, [key]: value }));

  useEffect(() => {
    if (!token) return;
    api
      .getOrderForm(token)
      .then((data) => {
        setOrder(data);
        if (data.customer_name) update("customer_name", data.customer_name);
      })
      .catch((err) => setLoadError(err instanceof Error ? err.message : "Invalid or expired link"))
      .finally(() => setLoading(false));
  }, [token]);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (form.pincode.length !== 6) {
      setSubmitError("Enter a valid 6-digit PIN code.");
      return;
    }
    setSubmitting(true);
    setSubmitError(null);
    try {
      await api.submitOrderForm(token, form);
      setDone(true);
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : "Could not submit details");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <Shell>
        <div className="space-y-4">
          <Skeleton className="h-5 w-40" />
          <Skeleton className="h-16" />
          <Skeleton className="h-10" />
          <Skeleton className="h-10" />
        </div>
      </Shell>
    );
  }

  if (loadError || !order) {
    return (
      <Shell>
        <div className="space-y-4 text-center">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full border border-red-200 bg-red-50 text-red-500">
            <AlertCircle className="h-6 w-6" />
          </div>
          <h2 className="text-lg font-bold tracking-tight text-navy-900">Link unavailable</h2>
          <p className="text-xs text-slate-500">{loadError}</p>
          <StoreLink label="Visit store" />
        </div>
      </Shell>
    );
  }

  if (done) {
    return (
      <Shell>
        <div className="animate-fade-in space-y-5 text-center">
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-navy-900 text-white">
            <CheckCircle2 className="h-7 w-7" />
          </div>
          <h2 className="text-xl font-bold tracking-tight text-navy-900">Order confirmed</h2>
          <div className="space-y-2 rounded-2xl border border-slate-200/80 bg-white p-4 text-left text-xs">
            {[
              ["Item", order.product_name],
              ["Total", formatCurrency(order.price)],
              ["Payment", form.payment_method === "cod" ? "Cash on delivery" : "Online"],
              ["Deliver to", `${form.address}, ${form.city} ${form.pincode}`],
            ].map(([k, v]) => (
              <div key={k} className="flex justify-between gap-4 text-slate-500">
                <span>{k}</span>
                <span className="truncate text-right font-semibold text-navy-900">{v}</span>
              </div>
            ))}
          </div>
          <StoreLink label="Continue to store" />
        </div>
      </Shell>
    );
  }

  return (
    <Shell>
      <div className="space-y-6">
        <div className="border-b border-slate-200/80 pb-4">
          <h2 className="text-xl font-bold tracking-tight text-navy-900">Delivery details</h2>
        </div>

        <div className="flex items-center justify-between rounded-2xl border border-slate-200/80 bg-white p-4">
          <div>
            <div className="text-sm font-bold text-navy-900">{order.product_name}</div>
            <div className="text-[11px] text-slate-500">× {order.quantity}</div>
          </div>
          <div className="font-mono text-base font-bold text-navy-900">{formatCurrency(order.price)}</div>
        </div>

        <form onSubmit={submit} className="space-y-4">
          <Field label="Full name">
            <Input required value={form.customer_name} onChange={(e) => update("customer_name", e.target.value)} autoComplete="name" />
          </Field>
          <Field label="Address">
            <Textarea rows={2} required value={form.address} onChange={(e) => update("address", e.target.value)} autoComplete="street-address" />
          </Field>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <Field label="City">
              <Input required value={form.city} onChange={(e) => update("city", e.target.value)} autoComplete="address-level2" />
            </Field>
            <Field label="State">
              <Input required value={form.state} onChange={(e) => update("state", e.target.value)} autoComplete="address-level1" />
            </Field>
            <Field label="PIN code">
              <Input
                required
                inputMode="numeric"
                maxLength={6}
                value={form.pincode}
                onChange={(e) => update("pincode", e.target.value.replace(/\D/g, ""))}
                autoComplete="postal-code"
                className="font-mono"
              />
            </Field>
          </div>

          <div className="space-y-2">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">Payment</span>
            <div className="grid grid-cols-2 gap-3">
              {PAYMENTS.map((p) => {
                const selected = form.payment_method === p.value;
                return (
                  <label
                    key={p.value}
                    className={cn(
                      "flex cursor-pointer items-center gap-3 rounded-xl border bg-white p-3.5 transition",
                      selected ? "border-navy-900 ring-2 ring-navy-900/10" : "border-slate-200/80 hover:border-slate-300"
                    )}
                  >
                    <input type="radio" name="payment" className="sr-only" checked={selected} onChange={() => update("payment_method", p.value)} />
                    <span className={selected ? "text-navy-900" : "text-slate-400"}>{p.icon}</span>
                    <span className="text-xs font-semibold text-navy-900">{p.label}</span>
                  </label>
                );
              })}
            </div>
          </div>

          <ErrorBanner message={submitError} />

          <Button type="submit" size="lg" className="w-full rounded-xl" disabled={submitting}>
            {submitting ? "Confirming…" : "Confirm order"}
          </Button>
        </form>
      </div>
    </Shell>
  );
}
