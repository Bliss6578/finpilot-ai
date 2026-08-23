import axios from "axios";

const configuredApiUrl =
  import.meta.env.VITE_API_BASE_URL ??
  import.meta.env.VITE_API_URL ??
  "http://localhost:8000";

// API methods already include the `/api` prefix. Accept either a backend
// origin or a URL ending in `/api` so production configuration is forgiving.
// In production, send API requests through Vercel's same-origin rewrite. This
// keeps the secure session cookie first-party on Safari/iOS and other browsers
// that block third-party cookies. Development continues to call FastAPI
// directly so the local frontend and backend can run on separate ports.
const apiBaseUrl = import.meta.env.PROD
  ? ""
  : configuredApiUrl.replace(/\/api\/?$/, "").replace(/\/$/, "");

export const api = axios.create({
  baseURL: apiBaseUrl,
  // Render's free service can need close to a minute to wake after inactivity.
  // Keep authentication requests alive long enough for that cold start.
  timeout: 75_000,
  withCredentials: true,
  headers: {
    "Content-Type": "application/json",
    "X-Paymentor-Request": "1",
  },
});
export type ApiTransaction = {
  id: string;
  order_id: string | null;
  customer: string;
  email: string | null;
  amount: number;
  currency: string;
  method: string | null;
  status: string;
  fee: number;
  tax: number;
  date: string;
  mode?: "test" | "live";
};
export type DashboardResponse = {
  revenue: number;
  payment_success_rate: number;
  transaction_counts: {
    total: number;
    captured: number;
    failed: number;
    refunded: number;
  };
  financial_summary?: {
    gross_revenue: number;
    refund_amount: number;
    pending_refund_amount: number;
    razorpay_fees: number;
    net_revenue: number;
    settled_amount: number;
  };
  settlement_counts?: {
    pending: number;
    completed: number;
    failed: number;
  };
  recent_transactions: ApiTransaction[];
  data_source: "razorpay" | "empty";
  mode?: "test" | "live";
};
export type RazorpayStatus = {
  connected: boolean;
  mode: "test" | "live";
  last_sync: string | null;
  last_sync_status: string;
  connection_type: "oauth" | "env_api_key" | "api_key" | null;
  api_key_id: string | null;
  webhook_url: string | null;
  oauth_available: boolean;
};
export type RazorpayAPIKeyConnection = {
  connected: true;
  mode: "test" | "live";
  key_id: string;
  webhook_url: string;
  webhook_secret: string | null;
};
export type RazorpayWebhookCredentials = {
  webhook_url: string;
  webhook_secret: string;
};
export type AuthSession = {
  user: {
    id: string;
    email: string;
    full_name: string;
    email_verified: boolean;
  };
  business: {
    id: string;
    name: string;
    slug: string;
    currency: string;
    role: string;
  };
  razorpay_connected: boolean;
  razorpay_mode: "test" | "live" | null;
};
export type SyncResult = {
  success: boolean;
  records_processed: number;
  records?: {
    payments: number;
    refunds: number;
    settlements: number;
  };
  warnings?: string[];
  synced_at: string;
};
export type CashflowPoint = {
  date: string;
  actual: number | null;
  forecast: number | null;
  lower: number | null;
  upper: number | null;
  inflow: number;
  outflow: number;
  kind: "actual" | "forecast";
};
export type CashflowResponse = {
  as_of: string;
  currency: "INR";
  mode: "test" | "live";
  data_source: "workspace_financials";
  summary: {
    cash_available: number;
    forecast_closing_balance: number;
    lowest_balance: number;
    lowest_balance_date: string;
    safe_reserve: number;
    risk_level: "low" | "medium" | "high";
  };
  drivers: {
    forecast_inflow: number;
    forecast_outflow: number;
    return_rate: number;
    variable_cost_ratio: number;
    payment_fee_ratio: number;
    fixed_daily_opex: number;
  };
  model: {
    name: string;
    trained_on: string;
    training_period: [string, string];
    tenant_history_days: number;
    minimum_tenant_history_days: number;
    limitations: string[];
  };
  points: CashflowPoint[];
};
export type AICFOContext = {
  as_of: string | null;
  mode: "test" | "live";
  razorpay_connected: boolean;
  latest_data_at: string | null;
  payment_attempts: number;
  suggestions: string[];
  focus: {
    title: string;
    description: string;
    cashflow_source: CashflowResponse["data_source"];
  };
};
export type AICFOResponse = {
  conversation_id: string;
  answer: string;
  recommendation: string;
  classification: "fact" | "forecast" | "recommendation";
  metrics: { label: string; value: string; detail: string }[];
  insights: { type: "positive" | "warning"; title: string; value: string }[];
  actions: { label: string; action: string }[];
  tools_used: string[];
  engine: string;
  scenario_result?: ScenarioResult;
  llm?: { provider: "openai"; model: string; grounded: boolean; fallback: boolean };
  agent?: {
    plan: { domain: string; intent: string; period_days: number; tools: string[]; scenario_type?: string | null; scenario_parameters?: Record<string, number> | null };
    confidence: number;
    evidence_id?: string;
    privacy: "processed_inside_paymentor";
    data_completeness?: Record<string, boolean>;
    reasoning_reference?: {
      operations: string[];
      similarity: number;
      source: string;
      policy: "operation_hint_only";
    } | null;
  };
  suggestions: string[];
  evidence: {
    tenant_scope: "authenticated_workspace";
    mode: "test" | "live";
    period_days: number;
    latest_data_at: string | null;
    cashflow_source: CashflowResponse["data_source"];
    sources: string[];
  };
};
export type FinancialSummary = {
  as_of: string;
  currency: string;
  current: Record<string, number | string>;
  previous: Record<string, number | string>;
  changes: { net_revenue_percent: number | null; net_cashflow_percent: number | null; failure_rate_points: number; refund_rate_points: number };
  cash: { current_paise: number | null; monthly_outflow_paise: number; monthly_net_burn_paise: number; runway_months: number | null; target_runway_months: number; minimum_reserve_paise: number };
  health: { score: number; status: string; components: Record<string, number>; limitations: string[] };
  data_completeness: Record<string, boolean>;
  forecast: CashflowResponse;
};
export type ScenarioResult = {
  scenario_type: string;
  currency: string;
  baseline: { monthly_inflow_paise: number; monthly_outflow_paise: number; monthly_net_burn_paise: number; runway_months: number | null; cash_90d_paise: number; break_even_revenue_paise: number };
  scenario: { monthly_inflow_paise: number; monthly_outflow_paise: number; monthly_net_burn_paise: number; runway_months: number | null; cash_90d_paise: number; break_even_revenue_paise: number };
  difference: { monthly_outflow_paise: number; runway_months: number | null; cash_90d_paise: number };
  disclaimer: string;
};
export type FinancialAlert = { id: string; type: string; severity: "critical" | "warning" | "info"; title: string; description: string; metric_value: number | null; baseline_value: number | null; status: string; evidence: Record<string, unknown>; created_at: string };
export type ScenarioPreferences = { revenue?: number; expense?: number; monthly?: number; one_time?: number; hires?: number; salary?: number; prompt?: string };
export type BusinessProfile = { name: string; currency: string; industry: string | null; website: string | null; current_cash: number | null; monthly_budget: number | null; monthly_fixed_expenses: number | null; minimum_reserve: number; target_runway_months: number; target_growth_rate: number | null; risk_tolerance: "conservative" | "moderate" | "aggressive"; ai_control_mode: "observer" | "advisor" | "autopilot"; notification_preferences: Record<string, boolean>; scenario_preferences: ScenarioPreferences };
export type ExpenseRecord = { id: string; category: string; description: string | null; amount: number; expense_type: string; recurring: boolean; recurrence_frequency?: "weekly" | "monthly" | "quarterly" | "yearly" | null; recurrence_end_date?: string | null; next_due_date?: string | null; vendor?: string | null; notes?: string | null; expense_date: string };
export type RevenueLeakResponse = { period_days: number; mode: string; potential_leak: number; gross_revenue: number; fee_rate: number; signals: { type: string; title: string; amount: number; count: number; confidence: "observed" | "provisional"; action: string }[]; methodology: string };
export type SettlementIntelligence = { period_days: number; mode: string; status: "reconciled" | "attention"; expected_net_settlement: number; settled_amount: number; variance: number; pending_settlements: number; average_delay_days: number | null; maximum_delay_days: number | null; stale_captured_payments: number; limitations: string[] };
export type AnomalyResult = { model: string; trained: boolean; observations: number; minimum_days?: number; anomalies: { date: string; score: number; net_cashflow: number; failure_rate: number; refund_rate: number }[] };
export type Recommendation = { id: string; priority: "critical" | "high" | "medium"; title: string; impact: number; basis: string; action_type: "update_cash_policy" | "create_follow_up"; parameters: Record<string, unknown> };
export type Approval = { id: string; action_type: string; title: string; parameters: Record<string, unknown>; status: string; created_at: string; resolved_at: string | null; executed_at: string | null; execution_result: Record<string, unknown> };
export async function fetchDashboard(days = 30) {
  return (await api.get<DashboardResponse>("/api/dashboard", { params: { days } })).data;
}
export async function fetchTransactions(days = 30) {
  return (
    await api.get<{ items: ApiTransaction[]; total: number; mode: "test" | "live" }>(
      "/api/transactions",
      { params: { days } }
    )
  ).data;
}
export async function fetchRazorpayStatus() {
  return (await api.get<RazorpayStatus>("/api/razorpay/status")).data;
}
export async function fetchCashflow(historyDays = 60, forecastDays = 30) {
  return (
    await api.get<CashflowResponse>("/api/cashflow", {
      params: { history_days: historyDays, forecast_days: forecastDays },
    })
  ).data;
}
export async function fetchAICFOContext() {
  return (await api.get<AICFOContext>("/api/ai-cfo/context")).data;
}
export async function askAICFO(question: string, conversationId?: string) {
  return (await api.post<AICFOResponse>("/api/v1/cfo/chat", { message: question, conversation_id: conversationId })).data;
}
export async function fetchFinancialSummary(days = 30) { return (await api.get<FinancialSummary>("/api/v1/dashboard/summary", { params: { days } })).data; }
export async function simulateScenario(type: string, parameters: Record<string, number>) { return (await api.post<ScenarioResult>("/api/v1/scenarios/simulate", { type, parameters })).data; }
export async function fetchFinancialAlerts(refresh = false) { return (await api.get<{ items: FinancialAlert[]; unread: number }>("/api/v1/alerts", { params: { refresh } })).data; }
export async function markFinancialAlertRead(alertId: string) { return (await api.patch<{ status: string }>(`/api/v1/alerts/${alertId}`)).data; }
export async function fetchBusinessProfile() { return (await api.get<BusinessProfile>("/api/v1/settings/business-profile")).data; }
export async function updateBusinessProfile(profile: Partial<BusinessProfile>) { return (await api.put<BusinessProfile>("/api/v1/settings/business-profile", profile)).data; }
export async function fetchExpenses() { return (await api.get<{ items: ExpenseRecord[]; total: number }>("/api/v1/expenses")).data; }
export async function createExpense(expense: Omit<ExpenseRecord, "id">) { return (await api.post<{ id: string; created: boolean }>("/api/v1/expenses", expense)).data; }
export async function deleteExpense(expenseId: string) { return (await api.delete<{ deleted: boolean }>(`/api/v1/expenses/${expenseId}`)).data; }
export async function fetchCFOConversation(conversationId: string) { return (await api.get<{ id: string; title: string; messages: { id: string; role: "user" | "assistant"; content: string; structured_content: AICFOResponse; created_at: string }[] }>(`/api/v1/cfo/conversations/${conversationId}`)).data; }
export async function fetchCFOConversations() { return (await api.get<{ items: { id: string; title: string; created_at: string; updated_at: string }[] }>("/api/v1/cfo/conversations")).data; }
export async function fetchRevenueLeaks() { return (await api.get<RevenueLeakResponse>("/api/v1/intelligence/revenue-leaks")).data; }
export async function fetchSettlementIntelligence() { return (await api.get<SettlementIntelligence>("/api/v1/intelligence/settlements")).data; }
export async function fetchAnomalies() { return (await api.get<AnomalyResult>("/api/v1/intelligence/anomalies")).data; }
export async function fetchRecommendations() { return (await api.get<{ generated_at: string; items: Recommendation[] }>("/api/v1/recommendations")).data; }
export async function fetchApprovals() { return (await api.get<{ items: Approval[] }>("/api/v1/approvals")).data; }
export async function createApproval(recommendation: Recommendation) { return (await api.post<{ id: string; status: string }>("/api/v1/approvals", { action_type: recommendation.action_type, title: recommendation.title, parameters: recommendation.parameters })).data; }
export async function decideApproval(id: string, decision: "approved" | "rejected") { return (await api.post<{ id: string; status: string; executed: boolean }>(`/api/v1/approvals/${id}/decision`, { decision })).data; }
export function financialReportUrl(days = 30) { return `${apiBaseUrl}/api/v1/reports/financial-summary?days=${days}`; }
export async function downloadFinancialReport(days = 30) { return (await api.get<Blob>("/api/v1/reports/financial-summary", { params: { days }, responseType: "blob" })).data; }
export async function syncRazorpay() {
  return (await api.post<SyncResult>("/api/razorpay/sync")).data;
}
export async function fetchSession() {
  return (await api.get<AuthSession>("/api/auth/me")).data;
}
export async function signIn(email: string, password: string) {
  return (await api.post<AuthSession>("/api/auth/login", { email, password })).data;
}
export async function signUp(payload: {
  full_name: string;
  email: string;
  password: string;
  business_name: string;
}) {
  return (await api.post<AuthSession>("/api/auth/signup", payload)).data;
}
export async function signOut() {
  await api.post("/api/auth/logout");
}
export async function changePassword(currentPassword: string, newPassword: string) {
  return (
    await api.post<AuthSession>("/api/auth/change-password", {
      current_password: currentPassword,
      new_password: newPassword,
    })
  ).data;
}
export async function revokeOtherSessions() {
  return (
    await api.post<{ revoked_sessions: number }>(
      "/api/auth/sessions/revoke-others"
    )
  ).data;
}
export async function requestEmailVerification() {
  return (
    await api.post<{ status: "sent" | "recently_sent" | "already_verified" }>(
      "/api/auth/email/verification/request"
    )
  ).data;
}
export async function confirmEmailVerification(token: string) {
  return (
    await api.post<{ status: "verified" }>("/api/auth/email/verification/confirm", { token })
  ).data;
}
export async function requestPasswordReset(email: string) {
  await api.post("/api/auth/password/forgot", { email });
}
export async function resetPassword(token: string, newPassword: string) {
  await api.post("/api/auth/password/reset", {
    token,
    new_password: newPassword,
  });
}
export async function beginRazorpayOAuth() {
  return (
    await api.get<{ authorization_url: string }>(
      "/api/razorpay/oauth/authorize"
    )
  ).data;
}
export async function connectRazorpayApiKeys(
  keyId: string,
  keySecret: string,
  confirmLiveAccess = false
) {
  return (
    await api.post<RazorpayAPIKeyConnection>("/api/razorpay/api-keys/connect", {
      key_id: keyId,
      key_secret: keySecret,
      confirm_live_access: confirmLiveAccess,
    })
  ).data;
}
export async function rotateRazorpayWebhookSecret() {
  return (
    await api.post<RazorpayWebhookCredentials>(
      "/api/razorpay/api-keys/webhook/rotate"
    )
  ).data;
}
export async function disconnectRazorpayApiKeys() {
  await api.delete("/api/razorpay/api-keys/disconnect");
}
