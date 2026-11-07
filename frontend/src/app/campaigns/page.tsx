"use client";

import React, { useRef, useState } from "react";
import {
  Plus,
  Play,
  Pause,
  Square,
  Upload,
  Download,
  CheckCircle2,
  AlertCircle,
  Megaphone,
  Sparkles,
  FileText,
  ArrowRight,
  ArrowLeft,
  Check,
  Languages,
  Loader2,
  Globe,
} from "lucide-react";
import { api } from "@/lib/api";
import { usePolling } from "@/lib/hooks";
import type { Campaign, CampaignCreateInput, ImportResult } from "@/lib/types";
import { Card } from "@/components/ui/Card";
import { StatusChip } from "@/components/ui/Status";
import { EmptyState, ErrorBanner, Skeleton } from "@/components/ui/Feedback";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { PageHeader } from "@/components/ui/PageHeader";
import { Field, Input, Select, Textarea } from "@/components/ui/Form";
import { cn } from "@/lib/utils";

const CSV_HEADERS = "name,phone,language,email,notes";

type ScriptChoice = "upload" | "ai" | null;
type ScriptLanguage = "hindi" | "english" | "hinglish";

function checkValidUrl(raw: string): boolean {
  if (!raw || !raw.trim()) return false;
  const trimmed = raw.trim();
  const urlCandidate =
    trimmed.startsWith("http://") || trimmed.startsWith("https://")
      ? trimmed
      : `https://${trimmed}`;
  try {
    const parsed = new URL(urlCandidate);
    return Boolean(
      (parsed.protocol === "http:" || parsed.protocol === "https:") &&
        parsed.hostname &&
        parsed.hostname.includes(".")
    );
  } catch {
    return false;
  }
}

function countWords(str: string): number {
  if (!str || !str.trim()) return 0;
  return str.trim().split(/\s+/).filter(Boolean).length;
}

function downloadCsvTemplate() {
  const blob = new Blob([`${CSV_HEADERS}\n`], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "contacts_template.csv";
  link.click();
  URL.revokeObjectURL(url);
}

export default function CampaignsPage() {
  const { data, loading, error, refresh } = usePolling(() => api.getCampaigns(), [], { intervalMs: 8000 });
  const campaigns = data ?? [];

  // Modal Workflow State
  const [showCreate, setShowCreate] = useState(false);
  const [step, setStep] = useState<1 | 2>(1);

  // STEP 1 State
  const [name, setName] = useState("");
  const [goal, setGoal] = useState("");
  const [productUrl, setProductUrl] = useState("");
  const [urlTouched, setUrlTouched] = useState(false);
  const [retryLimit, setRetryLimit] = useState(2);
  const [maxConcurrent, setMaxConcurrent] = useState(1);

  // STEP 2 State
  const [scriptChoice, setScriptChoice] = useState<ScriptChoice>(null);
  const [scriptLang, setScriptLang] = useState<ScriptLanguage>("hinglish");
  const [scriptContent, setScriptContent] = useState("");
  const [uploadedFile, setUploadedFile] = useState<{ name: string; size: number } | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isParsingDoc, setIsParsingDoc] = useState(false);
  const [dragOver, setDragOver] = useState(false);

  // Submission State
  const [saving, setSaving] = useState(false);
  const [modalError, setModalError] = useState<string | null>(null);

  // Contact CSV Import State
  const [importTarget, setImportTarget] = useState<Campaign | null>(null);
  const [importResult, setImportResult] = useState<ImportResult | null>(null);
  const [importing, setImporting] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const docxInputRef = useRef<HTMLInputElement>(null);

  // URL Validation
  const isUrlValid = checkValidUrl(productUrl);
  const showUrlError = (urlTouched || productUrl.length > 0) && !isUrlValid;
  const isStep1Valid = Boolean(name.trim() && goal.trim() && isUrlValid);

  const resetModal = () => {
    setStep(1);
    setName("");
    setGoal("");
    setProductUrl("");
    setUrlTouched(false);
    setRetryLimit(2);
    setMaxConcurrent(1);
    setScriptChoice(null);
    setScriptLang("hinglish");
    setScriptContent("");
    setUploadedFile(null);
    setIsGenerating(false);
    setIsParsingDoc(false);
    setModalError(null);
  };

  const handleOpenModal = () => {
    resetModal();
    setShowCreate(true);
  };

  const handleCloseModal = () => {
    setShowCreate(false);
    resetModal();
  };

  // Step 1 -> Step 2 Instant Transition
  const handleNextStep = (e: React.FormEvent) => {
    e.preventDefault();
    setUrlTouched(true);
    if (!isStep1Valid) return;
    setModalError(null);
    setStep(2);
  };

  // AI Script Generation
  const handleGenerateScript = async (targetLang?: ScriptLanguage) => {
    const lang = targetLang || scriptLang;
    setIsGenerating(true);
    setModalError(null);
    try {
      const normalizedUrl = productUrl.trim().startsWith("http")
        ? productUrl.trim()
        : `https://${productUrl.trim()}`;
      const res = await api.generateScript({
        goal: goal.trim(),
        product_url: normalizedUrl,
        language: lang,
      });
      setScriptContent(res.script);
    } catch (err) {
      setModalError(err instanceof Error ? err.message : "Failed to generate script with AI");
    } finally {
      setIsGenerating(false);
    }
  };

  // Word Document (.docx) Upload & Parsing
  const handleDocxFile = async (file: File) => {
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".docx")) {
      setModalError("Please upload a Microsoft Word document (.docx).");
      return;
    }
    if (file.size > 50 * 1024 * 1024) {
      setModalError("File size exceeds 50MB limit. Please upload a smaller document.");
      return;
    }

    setIsParsingDoc(true);
    setModalError(null);
    try {
      const res = await api.parseScriptDoc(file);
      setScriptContent(res.script);
      setUploadedFile({ name: file.name, size: file.size });
    } catch (err) {
      setModalError(err instanceof Error ? err.message : "Could not extract script from .docx file");
    } finally {
      setIsParsingDoc(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files?.[0];
    if (file) handleDocxFile(file);
  };

  // Final Action: Run Campaign & Start Calling
  const handleRunCampaign = async () => {
    setSaving(true);
    setModalError(null);
    try {
      const normalizedUrl = productUrl.trim().startsWith("http")
        ? productUrl.trim()
        : `https://${productUrl.trim()}`;

      // 1. Create the Campaign
      const created = await api.createCampaign({
        name: name.trim(),
        goal: goal.trim(),
        product_url: normalizedUrl,
        max_concurrent: maxConcurrent,
        retry_limit: retryLimit,
        script: scriptContent.trim() || undefined,
        language: scriptLang,
        window_start: "00:00",
        window_end: "23:59",
      });

      // 2. Start calling dispatcher with Twilio number
      await api.startCampaign(created.id);

      handleCloseModal();
      refresh();
    } catch (err) {
      setModalError(err instanceof Error ? err.message : "Failed to run campaign");
    } finally {
      setSaving(false);
    }
  };

  // Import Contacts CSV
  const handleFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !importTarget) return;
    setImporting(true);
    setImportResult(null);
    try {
      setImportResult(await api.importContactsCsv(importTarget.id, file));
      refresh();
    } catch (err) {
      setImportResult({ status: "error", error: err instanceof Error ? err.message : "Import failed" });
    } finally {
      setImporting(false);
      e.target.value = "";
    }
  };

  const act = async (fn: () => Promise<unknown>) => {
    await fn();
    refresh();
  };

  const wordCount = countWords(scriptContent);
  const estimatedMin = Math.max(1, Math.round(wordCount / 140));

  return (
    <div className="space-y-6 pb-12">
      <PageHeader
        title="Campaigns"
        actions={
          <>
            <Button
              variant="secondary"
              size="sm"
              icon={<Download className="h-3.5 w-3.5" />}
              onClick={downloadCsvTemplate}
            >
              CSV template
            </Button>
            <Button
              size="sm"
              icon={<Plus className="h-3.5 w-3.5" />}
              onClick={handleOpenModal}
              className="bg-[#0F172A] text-white hover:bg-slate-800"
            >
              New campaign
            </Button>
          </>
        }
      />

      <ErrorBanner message={error} />

      {loading ? (
        <div className="space-y-4">
          {[0, 1].map((i) => (
            <Card key={i} className="space-y-4 p-6 bg-[#F8FAFC]">
              <Skeleton className="h-4 w-48" />
              <Skeleton className="h-3 w-full max-w-xl" />
              <div className="grid grid-cols-3 gap-3">
                <Skeleton className="h-14" />
                <Skeleton className="h-14" />
                <Skeleton className="h-14" />
              </div>
            </Card>
          ))}
        </div>
      ) : campaigns.length === 0 ? (
        <EmptyState
          icon={<Megaphone className="h-6 w-6 text-[#0F172A]" />}
          title="No campaigns yet"
          action={
            <Button
              size="sm"
              icon={<Plus className="h-3.5 w-3.5" />}
              onClick={handleOpenModal}
              className="bg-[#0F172A] text-white hover:bg-slate-800"
            >
              New campaign
            </Button>
          }
        />
      ) : (
        <div className="space-y-4">
          {campaigns.map((camp) => (
            <Card key={camp.id} className="p-5 sm:p-6 bg-white border border-slate-200/80 shadow-card">
              <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                <div className="min-w-0 space-y-1.5">
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="text-base font-semibold tracking-tight text-[#0F172A]">{camp.name}</h3>
                    <StatusChip status={camp.status} />
                    {camp.language && (
                      <span className="rounded-md bg-slate-100 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-slate-600">
                        {camp.language}
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-[#64748B]">{camp.goal}</p>
                  {camp.product_url && (
                    <div className="flex items-center gap-1.5 text-xs text-slate-500">
                      <Globe className="h-3.5 w-3.5 text-slate-400" />
                      <a
                        href={camp.product_url}
                        target="_blank"
                        rel="noreferrer"
                        className="truncate hover:text-[#0F172A] underline underline-offset-2"
                      >
                        {camp.product_url}
                      </a>
                    </div>
                  )}
                  <div className="flex flex-wrap gap-x-4 gap-y-1 pt-1 text-[11px] font-medium text-[#64748B]">
                    <span>
                      Concurrency <strong className="text-[#0F172A]">{camp.max_concurrent}</strong>
                    </span>
                    <span>
                      Retries <strong className="text-[#0F172A]">{camp.retry_limit}</strong>
                    </span>
                  </div>
                </div>

                <div className="flex flex-wrap items-center gap-2">
                  <Button
                    variant="secondary"
                    size="sm"
                    icon={<Upload className="h-3.5 w-3.5" />}
                    onClick={() => {
                      setImportTarget(camp);
                      setImportResult(null);
                    }}
                  >
                    Import CSV
                  </Button>
                  {camp.status === "active" ? (
                    <Button
                      variant="secondary"
                      size="sm"
                      icon={<Pause className="h-3.5 w-3.5" />}
                      onClick={() => act(() => api.pauseCampaign(camp.id))}
                    >
                      Pause
                    </Button>
                  ) : (
                    <Button
                      size="sm"
                      icon={<Play className="h-3.5 w-3.5 fill-current" />}
                      className="bg-[#0F172A] text-white hover:bg-slate-800"
                      onClick={() => act(() => api.startCampaign(camp.id))}
                    >
                      Start
                    </Button>
                  )}
                  {camp.status !== "draft" && (
                    <Button
                      variant="ghost"
                      size="sm"
                      title="Stop campaign"
                      aria-label="Stop campaign"
                      onClick={() => act(() => api.stopCampaign(camp.id))}
                    >
                      <Square className="h-4 w-4" />
                    </Button>
                  )}
                </div>
              </div>

              <div className="mt-5 grid grid-cols-3 gap-3 border-t border-slate-100 pt-4">
                {[
                  ["Contacts", camp.total_contacts ?? 0],
                  ["Calls", camp.total_calls ?? 0],
                  ["Orders", camp.orders_count ?? 0],
                ].map(([label, value]) => (
                  <div key={label} className="rounded-xl border border-slate-200/80 bg-[#F8FAFC] p-3">
                    <div className="text-[10px] font-semibold uppercase tracking-wider text-[#64748B]">{label}</div>
                    <div className="mt-0.5 text-lg font-bold tabular-nums text-[#0F172A]">{value}</div>
                  </div>
                ))}
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* AI-NATIVE MULTI-STEP CAMPAIGN CREATION MODAL */}
      <Modal
        open={showCreate}
        onClose={handleCloseModal}
        className="max-w-2xl bg-white"
        title={
          <div className="flex items-center justify-between w-full pr-6">
            <div className="flex items-center gap-3">
              <span className="text-base font-bold tracking-tight text-[#0F172A]">
                {step === 1 ? "New Campaign Setup" : "Script Customization & Launch"}
              </span>
            </div>
            {/* Minimalist Step Tracker */}
            <div className="flex items-center gap-2">
              <span
                className={cn(
                  "inline-flex items-center justify-center text-xs font-semibold px-2.5 py-1 rounded-full transition-all",
                  step === 1
                    ? "bg-[#0F172A] text-white"
                    : "bg-[#F8FAFC] text-slate-500 border border-slate-200"
                )}
              >
                Step 1: Setup
              </span>
              <span className="text-slate-300">→</span>
              <span
                className={cn(
                  "inline-flex items-center justify-center text-xs font-semibold px-2.5 py-1 rounded-full transition-all",
                  step === 2
                    ? "bg-[#0F172A] text-white"
                    : "bg-[#F8FAFC] text-slate-500 border border-slate-200"
                )}
              >
                Step 2: Script
              </span>
            </div>
          </div>
        }
      >
        {/* Error notification in modal */}
        {modalError && (
          <div className="mb-4 flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 p-3 text-xs text-red-700">
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
            <span>{modalError}</span>
          </div>
        )}

        {/* STEP 1: CAMPAIGN SETUP */}
        {step === 1 && (
          <form onSubmit={handleNextStep} className="space-y-4">
            <Field label="Campaign Name">
              <Input
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. CURATED Festive Linen Drop"
                className="bg-white border-slate-200 focus:border-[#0F172A]"
              />
            </Field>

            <Field label="Goal / Objective">
              <Textarea
                rows={3}
                required
                value={goal}
                onChange={(e) => setGoal(e.target.value)}
                placeholder="Describe what the agent should achieve on each call (e.g. Introduce festive offer, qualify customer, confirm order or send WhatsApp catalog)"
                className="bg-white border-slate-200 focus:border-[#0F172A]"
              />
            </Field>

            <Field label="Product URL">
              <Input
                type="text"
                required
                value={productUrl}
                onChange={(e) => {
                  setProductUrl(e.target.value);
                  if (!urlTouched) setUrlTouched(true);
                }}
                onBlur={() => setUrlTouched(true)}
                placeholder="https://curatedindia.vercel.app/linen-kurta"
                className={cn(
                  "bg-white border-slate-200 focus:border-[#0F172A]",
                  showUrlError && "border-rose-400 focus:border-rose-500 focus:ring-rose-500/15"
                )}
              />
              {showUrlError && (
                <p className="mt-1 flex items-center gap-1.5 text-xs font-medium text-rose-500">
                  <AlertCircle className="h-3.5 w-3.5 flex-shrink-0" />
                  Please enter a valid URL
                </p>
              )}
            </Field>

            <div className="grid grid-cols-2 gap-4">
              <Field label="Retry Limit">
                <Input
                  type="number"
                  min={0}
                  max={5}
                  value={retryLimit}
                  onChange={(e) => setRetryLimit(Number(e.target.value))}
                  className="bg-white border-slate-200"
                />
              </Field>

              <Field label="Number of People / Max Concurrent Calls">
                <Input
                  type="number"
                  min={1}
                  max={10}
                  value={maxConcurrent}
                  onChange={(e) => setMaxConcurrent(Number(e.target.value))}
                  className="bg-white border-slate-200"
                />
              </Field>
            </div>

            <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-100">
              <Button type="button" variant="secondary" onClick={handleCloseModal}>
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={!isStep1Valid}
                className="bg-[#0F172A] text-white hover:bg-slate-800 disabled:opacity-40 flex items-center gap-1.5"
              >
                <span>Next</span>
                <ArrowRight className="h-3.5 w-3.5" />
              </Button>
            </div>
          </form>
        )}

        {/* STEP 2: SCRIPT CUSTOMIZATION & GENERATION */}
        {step === 2 && (
          <div className="space-y-5">
            {/* Question Prompt */}
            <div>
              <p className="text-sm font-semibold text-[#0F172A]">
                Do you have a specific script for this campaign?
              </p>
              <p className="text-xs text-[#64748B] mt-0.5">
                Choose whether to upload an existing Word document or let AI craft an optimized ~2-minute script.
              </p>
            </div>

            {/* Option Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {/* Option A: Yes (Upload .docx) */}
              <button
                type="button"
                onClick={() => setScriptChoice("upload")}
                className={cn(
                  "p-4 rounded-xl border text-left transition-all relative flex flex-col justify-between",
                  scriptChoice === "upload"
                    ? "border-[#0F172A] bg-[#F8FAFC] shadow-sm ring-1 ring-[#0F172A]"
                    : "border-slate-200 bg-white hover:bg-slate-50/70"
                )}
              >
                <div className="flex items-center justify-between w-full mb-2">
                  <div className="p-2 rounded-lg bg-white border border-slate-200/80 text-[#0F172A]">
                    <FileText className="h-5 w-5" />
                  </div>
                  {scriptChoice === "upload" && (
                    <span className="h-5 w-5 rounded-full bg-[#0F172A] text-white flex items-center justify-center">
                      <Check className="h-3 w-3 stroke-[3]" />
                    </span>
                  )}
                </div>
                <div>
                  <div className="text-sm font-bold text-[#0F172A]">Yes, upload script</div>
                  <div className="text-[11px] text-[#64748B] mt-0.5">
                    Word document (.docx) up to 50MB
                  </div>
                </div>
              </button>

              {/* Option B: No (Generate with AI) */}
              <button
                type="button"
                onClick={() => {
                  setScriptChoice("ai");
                  if (!scriptContent) {
                    handleGenerateScript(scriptLang);
                  }
                }}
                className={cn(
                  "p-4 rounded-xl border text-left transition-all relative flex flex-col justify-between",
                  scriptChoice === "ai"
                    ? "border-[#0F172A] bg-[#F8FAFC] shadow-sm ring-1 ring-[#0F172A]"
                    : "border-slate-200 bg-white hover:bg-slate-50/70"
                )}
              >
                <div className="flex items-center justify-between w-full mb-2">
                  <div className="p-2 rounded-lg bg-white border border-slate-200/80 text-[#0F172A]">
                    <Sparkles className="h-5 w-5 text-amber-500" />
                  </div>
                  {scriptChoice === "ai" && (
                    <span className="h-5 w-5 rounded-full bg-[#0F172A] text-white flex items-center justify-center">
                      <Check className="h-3 w-3 stroke-[3]" />
                    </span>
                  )}
                </div>
                <div>
                  <div className="text-sm font-bold text-[#0F172A]">No, generate with AI</div>
                  <div className="text-[11px] text-[#64748B] mt-0.5">
                    Auto-draft ~2-minute script (up to 800 words)
                  </div>
                </div>
              </button>
            </div>

            {/* Option A: Dropzone */}
            {scriptChoice === "upload" && (
              <div className="space-y-2 animate-fade-in">
                <div
                  onDragOver={(e) => {
                    e.preventDefault();
                    setDragOver(true);
                  }}
                  onDragLeave={() => setDragOver(false)}
                  onDrop={handleDrop}
                  onClick={() => docxInputRef.current?.click()}
                  className={cn(
                    "w-full rounded-xl border-2 border-dashed p-6 text-center cursor-pointer transition-colors bg-[#F8FAFC]",
                    dragOver
                      ? "border-[#0F172A] bg-slate-100"
                      : "border-slate-300 hover:border-[#0F172A]"
                  )}
                >
                  <input
                    ref={docxInputRef}
                    type="file"
                    accept=".docx"
                    className="hidden"
                    onChange={(e) => {
                      const file = e.target.files?.[0];
                      if (file) handleDocxFile(file);
                    }}
                  />
                  {isParsingDoc ? (
                    <div className="flex flex-col items-center justify-center py-2">
                      <Loader2 className="h-6 w-6 animate-spin text-[#0F172A]" />
                      <span className="mt-2 text-xs font-semibold text-[#0F172A]">
                        Extracting script from Word document…
                      </span>
                    </div>
                  ) : uploadedFile ? (
                    <div className="flex flex-col items-center justify-center py-1">
                      <CheckCircle2 className="h-6 w-6 text-emerald-600 mb-1" />
                      <span className="text-xs font-bold text-[#0F172A]">{uploadedFile.name}</span>
                      <span className="text-[11px] text-[#64748B]">
                        {(uploadedFile.size / 1024).toFixed(1)} KB · Click to replace file
                      </span>
                    </div>
                  ) : (
                    <div className="flex flex-col items-center justify-center py-2">
                      <Upload className="h-6 w-6 text-[#64748B] mb-2" />
                      <div className="text-xs font-semibold text-[#0F172A]">
                        Drop your Word document (.docx) here, or browse
                      </div>
                      <div className="text-[11px] text-[#64748B] mt-1">
                        Accepts .docx documents up to 50MB
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Option B: AI Generator Bar */}
            {scriptChoice === "ai" && (
              <div className="flex items-center justify-between p-3 rounded-xl bg-[#F8FAFC] border border-slate-200/80 animate-fade-in">
                <div className="min-w-0 pr-3">
                  <div className="text-xs font-semibold text-[#0F172A] flex items-center gap-1.5">
                    <Sparkles className="h-3.5 w-3.5 text-amber-500 shrink-0" />
                    <span>Gemini Script Engine</span>
                  </div>
                  <div className="text-[11px] text-[#64748B] truncate">
                    Using Goal & {productUrl ? "Product URL" : "defaults"}
                  </div>
                </div>
                <Button
                  type="button"
                  size="sm"
                  disabled={isGenerating}
                  onClick={() => handleGenerateScript(scriptLang)}
                  className="bg-[#0F172A] text-white hover:bg-slate-800 text-xs shrink-0"
                >
                  {isGenerating ? (
                    <>
                      <Loader2 className="h-3.5 w-3.5 animate-spin mr-1.5" />
                      Generating…
                    </>
                  ) : (
                    <>
                      <Sparkles className="h-3.5 w-3.5 mr-1.5 text-amber-400" />
                      Generate Script with AI
                    </>
                  )}
                </Button>
              </div>
            )}

            {/* Language Selector (Hindi, English, Hinglish) */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-semibold uppercase tracking-wider text-[#64748B] flex items-center gap-1">
                  <Languages className="h-3.5 w-3.5" />
                  Select Script Language
                </span>
                {scriptChoice === "ai" && scriptContent && (
                  <button
                    type="button"
                    onClick={() => handleGenerateScript(scriptLang)}
                    disabled={isGenerating}
                    className="text-[11px] font-semibold text-[#0F172A] hover:underline"
                  >
                    Regenerate in this language
                  </button>
                )}
              </div>
              <div className="grid grid-cols-3 gap-2">
                {(
                  [
                    { key: "hindi", label: "Hindi", desc: "हिंदी" },
                    { key: "english", label: "English", desc: "Global" },
                    { key: "hinglish", label: "Hinglish", desc: "Everyday Sales" },
                  ] as const
                ).map((lang) => (
                  <button
                    key={lang.key}
                    type="button"
                    onClick={() => {
                      setScriptLang(lang.key);
                      if (scriptChoice === "ai") {
                        handleGenerateScript(lang.key);
                      }
                    }}
                    className={cn(
                      "py-2 px-3 rounded-lg border text-center transition-all",
                      scriptLang === lang.key
                        ? "border-[#0F172A] bg-[#0F172A] text-white font-semibold shadow-sm"
                        : "border-slate-200 bg-[#F8FAFC] text-slate-700 hover:bg-white"
                    )}
                  >
                    <div className="text-xs font-semibold leading-tight">{lang.label}</div>
                    <div
                      className={cn(
                        "text-[10px] leading-tight mt-0.5",
                        scriptLang === lang.key ? "text-slate-300" : "text-[#64748B]"
                      )}
                    >
                      {lang.desc}
                    </div>
                  </button>
                ))}
              </div>
            </div>

            {/* Script Preview & Live Editor */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-semibold uppercase tracking-wider text-[#64748B]">
                  Script Preview & Editor
                </span>
                <span className="text-[11px] font-medium text-[#64748B]">
                  {wordCount} words · ~{estimatedMin} min speech duration (max 800 words)
                </span>
              </div>
              <Textarea
                rows={7}
                value={scriptContent}
                onChange={(e) => setScriptContent(e.target.value)}
                placeholder="The script will appear here. You can also type or edit directly..."
                className="bg-[#F8FAFC] border-slate-200 text-xs font-sans leading-relaxed focus:bg-white focus:border-[#0F172A]"
              />
            </div>

            {/* Modal Navigation Buttons */}
            <div className="flex items-center justify-between pt-3 border-t border-slate-100">
              <Button
                type="button"
                variant="secondary"
                onClick={() => setStep(1)}
                className="flex items-center gap-1.5"
              >
                <ArrowLeft className="h-3.5 w-3.5" />
                <span>Back</span>
              </Button>

              {/* Primary Navy Blue Action Button */}
              <Button
                type="button"
                disabled={saving || isGenerating || isParsingDoc}
                onClick={handleRunCampaign}
                className="bg-[#0F172A] text-white hover:bg-slate-800 px-5 py-2.5 shadow-md flex items-center gap-2"
              >
                {saving ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin text-white" />
                    <span>Launching Campaign…</span>
                  </>
                ) : (
                  <>
                    <Play className="h-3.5 w-3.5 fill-current text-white" />
                    <span>Run Campaign & Start Calling</span>
                  </>
                )}
              </Button>
            </div>
          </div>
        )}
      </Modal>

      {/* Contacts CSV Import Modal */}
      <Modal open={!!importTarget} onClose={() => setImportTarget(null)} title={`Import contacts · ${importTarget?.name ?? ""}`}>
        <div className="space-y-4">
          <p className="text-xs text-slate-500">
            Headers: <code className="font-mono text-navy-900">{CSV_HEADERS}</code>. Phone in E.164.
          </p>
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={importing}
            className="w-full rounded-xl border-2 border-dashed border-slate-200 bg-slate-50 p-8 text-center transition hover:border-navy-900 disabled:opacity-60"
          >
            <Upload className="mx-auto mb-2 h-6 w-6 text-slate-400" />
            <div className="text-xs font-semibold text-navy-900">{importing ? "Uploading…" : "Choose CSV file"}</div>
            <input ref={fileInputRef} type="file" accept=".csv" onChange={handleFile} className="hidden" />
          </button>

          {importResult && (
            <div
              className={`flex items-start gap-2 rounded-lg border px-3 py-2.5 text-xs ${
                importResult.status === "success" ? "border-slate-200/80 bg-white text-navy-900" : "border-red-200 bg-red-50 text-red-700"
              }`}
            >
              {importResult.status === "success" ? (
                <>
                  <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
                  <div>
                    <div className="font-semibold">{importResult.imported_count ?? 0} contacts imported</div>
                    {!!importResult.rejected_count && (
                      <div className="text-slate-500">{importResult.rejected_count} rows rejected</div>
                    )}
                  </div>
                </>
              ) : (
                <>
                  <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                  <span className="font-semibold">{importResult.error || "Import failed"}</span>
                </>
              )}
            </div>
          )}

          <div className="flex items-center justify-between pt-1">
            <button type="button" onClick={downloadCsvTemplate} className="text-xs font-semibold text-slate-500 hover:text-navy-900">
              Download template
            </button>
            <Button variant="secondary" onClick={() => setImportTarget(null)}>
              Done
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
