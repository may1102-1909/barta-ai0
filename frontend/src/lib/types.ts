export type CampaignStatus = "draft" | "active" | "paused" | "stopped" | "completed";

export interface Campaign {
  id: string;
  name: string;
  goal: string;
  status: CampaignStatus | string;
  product_id?: string;
  product_url?: string;
  script?: string;
  language?: "hindi" | "english" | "hinglish" | string;
  window_start?: string;
  window_end?: string;
  max_concurrent: number;
  retry_limit: number;
  total_contacts?: number;
  total_calls?: number;
  orders_count?: number;
  created_at?: string;
}

export interface CampaignCreateInput {
  name: string;
  goal: string;
  product_url?: string;
  max_concurrent: number;
  window_start?: string;
  window_end?: string;
  retry_limit: number;
  script?: string;
  language?: "hindi" | "english" | "hinglish";
}

export interface ScriptGenerateResponse {
  script: string;
  language: string;
  word_count: number;
}

export interface ScriptParseResponse {
  script: string;
  filename: string;
  size: number;
  word_count: number;
}

export interface Funnel {
  contacts: number;
  called: number;
  connected: number;
  interested: number;
  order_confirmed: number;
}

export interface Counters {
  total_calls: number;
  connected_calls: number;
  orders_confirmed: number;
  callbacks_pending: number;
  avg_duration_sec: number;
}

export interface CampaignStats {
  funnel: Funnel;
  counters: Counters;
}

export const EMPTY_STATS: CampaignStats = {
  funnel: { contacts: 0, called: 0, connected: 0, interested: 0, order_confirmed: 0 },
  counters: { total_calls: 0, connected_calls: 0, orders_confirmed: 0, callbacks_pending: 0, avg_duration_sec: 0 },
};

export type CallOutcome =
  | "order_confirmed"
  | "interested"
  | "callback_requested"
  | "not_interested"
  | "do_not_call"
  | "no_answer";

export interface CallSummary {
  id: string;
  contact_name: string;
  contact_phone: string;
  campaign_name?: string | null;
  outcome: CallOutcome | string | null;
  status?: string;
  duration_sec: number;
  started_at?: string | null;
  summary?: string | null;
  transcript_turns?: number;
}

export interface TranscriptTurn {
  speaker: "agent" | "user" | string;
  text: string;
  timestamp?: string;
}

export interface CallDetail extends CallSummary {
  contact_email?: string | null;
  language_preferred?: string | null;
  started_at_ist?: string | null;
  transcript: TranscriptTurn[];
}

export type OrderStatus = "awaiting_details" | "details_received" | "cod" | "paid";

export interface Order {
  id: string;
  customer_name: string;
  customer_email?: string | null;
  customer_phone?: string | null;
  product_name: string;
  quantity: number;
  total_price: number;
  status: OrderStatus | string;
  payment_method?: string | null;
  delivery_address?: string | null;
  form_url?: string | null;
  form_expires_at?: string | null;
  created_at_ist?: string | null;
}

export type CallbackStatus = "pending" | "in_progress" | "done" | "cancelled";

export interface Callback {
  id: string;
  contact_name: string;
  contact_phone: string;
  reason?: string | null;
  status: CallbackStatus | string;
  due_at_iso?: string | null;
  due_at_ist?: string | null;
  created_at?: string | null;
}

export interface OrderForm {
  product_name: string;
  quantity: number;
  price: number;
  customer_name?: string | null;
}

export interface OrderFormSubmission {
  customer_name: string;
  address: string;
  city: string;
  state: string;
  pincode: string;
  payment_method: "cod" | "razorpay";
}

export interface Health {
  status: string;
  twilio_configured?: boolean;
  gnani_configured?: boolean;
  gemini_configured?: boolean;
  resend_configured?: boolean;
}

export interface SimulationStartInput {
  contact_name: string;
  contact_phone: string;
  contact_email?: string;
  preferred_language: string;
}

export interface SimulationStart {
  session_id: string;
  call_id: string;
  transcript?: TranscriptTurn[];
}

export interface SimulationTurn {
  transcript?: TranscriptTurn[];
  tool_called?: string | null;
  outcome?: string | null;
  call_ended?: boolean;
}

export interface ImportResult {
  status: "success" | "error" | string;
  imported_count?: number;
  rejected_count?: number;
  rejected_details?: { row: number; reason: string }[];
  error?: string;
}

export interface ApiMessage {
  status: string;
  message?: string;
}
