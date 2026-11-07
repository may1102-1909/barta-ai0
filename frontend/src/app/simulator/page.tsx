"use client";

import React, { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { PhoneCall, PhoneOff, Send, Bot, Wrench, CheckCircle2, ExternalLink } from "lucide-react";
import { api } from "@/lib/api";
import type { SimulationStartInput, TranscriptTurn } from "@/lib/types";
import { humanize } from "@/lib/utils";
import { Card } from "@/components/ui/Card";
import { LiveDot, StatusChip } from "@/components/ui/Status";
import { ErrorBanner } from "@/components/ui/Feedback";
import { Button, buttonClass } from "@/components/ui/Button";
import { PageHeader } from "@/components/ui/PageHeader";
import { Field, Input, Select } from "@/components/ui/Form";
import { TranscriptThread } from "@/components/TranscriptThread";

const LANGUAGES = [
  ["hinglish", "Hinglish"],
  ["hindi", "Hindi"],
  ["english", "English"],
];

const EMPTY_CONTACT: SimulationStartInput = {
  contact_name: "",
  contact_phone: "",
  contact_email: "",
  preferred_language: "hinglish",
};

export default function SimulatorPage() {
  const [contact, setContact] = useState<SimulationStartInput>(EMPTY_CONTACT);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [callId, setCallId] = useState<string | null>(null);
  const [transcript, setTranscript] = useState<TranscriptTurn[]>([]);
  const [input, setInput] = useState("");
  const [starting, setStarting] = useState(false);
  const [sending, setSending] = useState(false);
  const [lastTool, setLastTool] = useState<string | null>(null);
  const [outcome, setOutcome] = useState<string | null>(null);
  const [ended, setEnded] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const endRef = useRef<HTMLDivElement>(null);

  const active = !!sessionId;
  const canSpeak = active && !ended && !sending;

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [transcript, sending]);

  const update = <K extends keyof SimulationStartInput>(key: K, value: SimulationStartInput[K]) =>
    setContact((c) => ({ ...c, [key]: value }));

  const start = async () => {
    setStarting(true);
    setError(null);
    setEnded(false);
    setOutcome(null);
    setLastTool(null);
    try {
      const res = await api.startSimulation(contact);
      setSessionId(res.session_id);
      setCallId(res.call_id);
      setTranscript(res.transcript ?? []);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not start simulation");
    } finally {
      setStarting(false);
    }
  };

  const send = async () => {
    const text = input.trim();
    if (!text || !sessionId || !canSpeak) return;
    setInput("");
    setSending(true);
    setError(null);
    setTranscript((prev) => [...prev, { speaker: "user", text, timestamp: new Date().toISOString() }]);
    try {
      const res = await api.sendSimTurn(sessionId, text);
      if (res.tool_called) setLastTool(res.tool_called);
      if (res.outcome) setOutcome(res.outcome);
      if (res.call_ended) setEnded(true);
      if (res.transcript) setTranscript(res.transcript);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Turn failed");
    } finally {
      setSending(false);
    }
  };

  const hangUp = () => {
    setEnded(true);
    setSessionId(null);
  };

  return (
    <div className="space-y-6 pb-12">
      <PageHeader
        title="Simulator"
        meta={active && <StatusChip tone={ended ? "neutral" : "live"} label={ended ? "Ended" : "Connected"} />}
        actions={
          callId && (
            <Link href={`/calls?call_id=${callId}`} className={buttonClass("secondary", "sm")}>
              View call <ExternalLink className="h-3.5 w-3.5" />
            </Link>
          )
        }
      />

      <ErrorBanner message={error} />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-12 lg:gap-6">
        <div className="space-y-4 lg:col-span-4">
          <Card className="space-y-4 p-5">
            <div className="space-y-3">
              <Field label="Customer">
                <Input value={contact.contact_name} disabled={active} onChange={(e) => update("contact_name", e.target.value)} placeholder="Name" />
              </Field>
              <Field label="Phone">
                <Input
                  value={contact.contact_phone}
                  disabled={active}
                  onChange={(e) => update("contact_phone", e.target.value)}
                  placeholder="+91…"
                  className="font-mono"
                  inputMode="tel"
                />
              </Field>
              <Field label="Email">
                <Input
                  type="email"
                  value={contact.contact_email}
                  disabled={active}
                  onChange={(e) => update("contact_email", e.target.value)}
                  placeholder="Optional"
                />
              </Field>
              <Field label="Language">
                <Select value={contact.preferred_language} disabled={active} onChange={(e) => update("preferred_language", e.target.value)}>
                  {LANGUAGES.map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </Select>
              </Field>
            </div>

            {!active ? (
              <Button
                size="lg"
                className="w-full"
                disabled={starting || !contact.contact_name.trim() || !contact.contact_phone.trim()}
                icon={<PhoneCall className="h-4 w-4" />}
                onClick={start}
              >
                {starting ? "Dialing…" : "Start call"}
              </Button>
            ) : (
              <Button size="lg" variant="danger" className="w-full" icon={<PhoneOff className="h-4 w-4" />} onClick={hangUp}>
                Hang up
              </Button>
            )}
          </Card>

          {(lastTool || outcome) && (
            <Card className="space-y-2 p-4 text-xs">
              {lastTool && (
                <div className="flex items-center gap-2 rounded-lg border border-slate-200/80 bg-white px-3 py-2 font-semibold text-navy-900">
                  <Wrench className="h-3.5 w-3.5 text-slate-400" />
                  <code className="font-mono">{lastTool}</code>
                </div>
              )}
              {outcome && (
                <div className="flex items-center gap-2 rounded-lg bg-navy-900 px-3 py-2 font-semibold uppercase tracking-wider text-white">
                  <CheckCircle2 className="h-3.5 w-3.5" />
                  {humanize(outcome)}
                </div>
              )}
            </Card>
          )}
        </div>

        <Card className="flex h-[70vh] min-h-[480px] flex-col overflow-hidden lg:col-span-8 lg:h-[680px]">
          <div className="flex items-center justify-between border-b border-slate-200/80 bg-white px-4 py-3">
            <span className="flex items-center gap-2 text-xs font-semibold text-navy-900">
              <LiveDot tone={active && !ended ? "live" : "neutral"} />
              Dialogue
            </span>
            {callId && <span className="hidden font-mono text-[11px] text-slate-400 sm:block">{callId}</span>}
          </div>

          <div className="flex-1 space-y-4 overflow-y-auto p-4 sm:p-6">
            {transcript.length === 0 ? (
              <div className="flex h-full flex-col items-center justify-center gap-3 text-center text-slate-400">
                <Bot className="h-10 w-10 text-slate-300" />
                <p className="text-xs font-medium">Start a call to begin.</p>
              </div>
            ) : (
              <TranscriptThread turns={transcript} contactName={contact.contact_name} />
            )}
            {sending && (
              <div className="flex items-center gap-1.5 text-xs text-slate-400">
                <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-navy-900" />
                <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-navy-900 [animation-delay:0.15s]" />
                <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-navy-900 [animation-delay:0.3s]" />
              </div>
            )}
            <div ref={endRef} />
          </div>

          <div className="flex items-center gap-2 border-t border-slate-200/80 bg-white p-3 sm:p-4">
            <Input
              value={input}
              disabled={!canSpeak}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && send()}
              placeholder={!active ? "Start a call to speak" : ended ? "Call ended" : "What the customer says…"}
              className="h-10 flex-1 rounded-xl"
            />
            <Button disabled={!canSpeak || !input.trim()} onClick={send} className="h-10 rounded-xl" icon={<Send className="h-3.5 w-3.5" />}>
              <span className="hidden sm:inline">Send</span>
            </Button>
          </div>
        </Card>
      </div>
    </div>
  );
}
