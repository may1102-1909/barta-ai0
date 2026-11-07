import type {
  ApiMessage,
  CallDetail,
  CallSummary,
  Callback,
  Campaign,
  CampaignCreateInput,
  CampaignStats,
  Health,
  ImportResult,
  Order,
  OrderForm,
  OrderFormSubmission,
  ScriptGenerateResponse,
  ScriptParseResponse,
  SimulationStart,
  SimulationStartInput,
  SimulationTurn,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function readError(res: Response, fallback: string) {
  try {
    const body = await res.json();
    return body.detail || body.message || fallback;
  } catch {
    return fallback;
  }
}

export async function fetchApi<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options?.headers || {}),
    },
  });
  if (!res.ok) throw new Error(await readError(res, "API request failed"));
  return res.json();
}

function query(params: Record<string, string | number | undefined>) {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== "") search.append(key, String(value));
  });
  const qs = search.toString();
  return qs ? `?${qs}` : "";
}

export const api = {
  getCampaigns: () => fetchApi<Campaign[]>("/campaigns"),
  getCampaign: (id: string) => fetchApi<Campaign>(`/campaigns/${id}`),
  createCampaign: (data: CampaignCreateInput) =>
    fetchApi<Campaign>("/campaigns", { method: "POST", body: JSON.stringify(data) }),
  startCampaign: (id: string) => fetchApi<ApiMessage>(`/campaigns/${id}/start`, { method: "POST" }),
  pauseCampaign: (id: string) => fetchApi<ApiMessage>(`/campaigns/${id}/pause`, { method: "POST" }),
  stopCampaign: (id: string) => fetchApi<ApiMessage>(`/campaigns/${id}/stop`, { method: "POST" }),
  getCampaignStats: (id: string) => fetchApi<CampaignStats>(`/campaigns/${id}/stats`),
  generateScript: (data: { goal: string; product_url?: string; language?: string }) =>
    fetchApi<ScriptGenerateResponse>("/campaigns/generate-script", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  parseScriptDoc: async (file: File): Promise<ScriptParseResponse> => {
    const formData = new FormData();
    formData.append("file", file);
    const res = await fetch(`${API_BASE}/campaigns/parse-script-doc`, {
      method: "POST",
      body: formData,
    });
    if (!res.ok) throw new Error(await readError(res, "Failed to parse script document"));
    return res.json();
  },

  importContactsCsv: async (campaignId: string, file: File): Promise<ImportResult> => {
    const formData = new FormData();
    formData.append("file", file);
    const res = await fetch(`${API_BASE}/campaigns/${campaignId}/contacts/import`, {
      method: "POST",
      body: formData,
    });
    if (!res.ok) throw new Error(await readError(res, "Import failed"));
    return res.json();
  },

  getCalls: (params: { campaign_id?: string; outcome?: string; limit?: number } = {}) =>
    fetchApi<CallSummary[]>(`/calls${query(params)}`),
  getCallDetail: (id: string) => fetchApi<CallDetail>(`/calls/${id}`),

  getOrders: (params: { status?: string; limit?: number; offset?: number } = {}) =>
    fetchApi<Order[]>(`/orders${query(params)}`),
  getOrderDetail: (id: string) => fetchApi<Order>(`/orders/${id}`),

  getCallbacks: (params: { status?: string; limit?: number; offset?: number } = {}) =>
    fetchApi<Callback[]>(`/callbacks${query(params)}`),
  rescheduleCallback: (id: string, newDueAtIso: string) =>
    fetchApi<ApiMessage>(`/callbacks/${id}/reschedule`, {
      method: "POST",
      body: JSON.stringify({ new_due_at_iso: newDueAtIso }),
    }),
  cancelCallback: (id: string) => fetchApi<ApiMessage>(`/callbacks/${id}/cancel`, { method: "POST" }),

  getOrderForm: (token: string) => fetchApi<OrderForm>(`/order-form/${token}`),
  submitOrderForm: (token: string, data: OrderFormSubmission) =>
    fetchApi<ApiMessage>(`/order-form/${token}`, { method: "POST", body: JSON.stringify(data) }),

  startSimulation: (data: SimulationStartInput) =>
    fetchApi<SimulationStart>("/simulator/start", { method: "POST", body: JSON.stringify(data) }),
  sendSimTurn: (sessionId: string, transcript: string) =>
    fetchApi<SimulationTurn>("/simulator/turn", {
      method: "POST",
      body: JSON.stringify({ session_id: sessionId, user_transcript: transcript }),
    }),

  getHealth: () => fetchApi<Health>("/health"),
};
