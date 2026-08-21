import axios from "axios";

const configuredApiUrl =
  import.meta.env.VITE_API_BASE_URL ??
  import.meta.env.VITE_API_URL ??
  "http://localhost:8000";

// API methods already include the `/api` prefix. Accept either a backend
// origin or a URL ending in `/api` so production configuration is forgiving.
const apiBaseUrl = configuredApiUrl.replace(/\/api\/?$/, "").replace(/\/$/, "");

export const api = axios.create({
  baseURL: apiBaseUrl,
  // Render's free service can need close to a minute to wake after inactivity.
  // Keep authentication requests alive long enough for that cold start.
  timeout: 75_000,
  withCredentials: true,
  headers: {
    "Content-Type": "application/json",
    "X-FinPilot-Request": "1",
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
  data_source: "razorpay_history" | "razorpay_plus_dataset" | "uci_online_retail_ii_demo";
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
export async function fetchDashboard() {
  return (await api.get<DashboardResponse>("/api/dashboard")).data;
}
export async function fetchTransactions() {
  return (
    await api.get<{ items: ApiTransaction[]; total: number; mode: "test" | "live" }>(
      "/api/transactions"
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
    await api.post<AuthSession>("/api/auth/email/verification/confirm", { token })
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
