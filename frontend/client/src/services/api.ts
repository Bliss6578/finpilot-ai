import axios from "axios";

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? "http://localhost:8000",
  timeout: 15_000,
  withCredentials: true,
  headers: { "Content-Type": "application/json" },
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
  recent_transactions: ApiTransaction[];
  data_source: "razorpay" | "empty";
};
export type RazorpayStatus = {
  connected: boolean;
  mode: "test" | "live";
  last_sync: string | null;
  last_sync_status: string;
  connection_type: "oauth" | "env_api_key" | null;
  oauth_available: boolean;
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
};
export type SyncResult = {
  success: boolean;
  records_processed: number;
  synced_at: string;
};
export async function fetchDashboard() {
  return (await api.get<DashboardResponse>("/api/dashboard")).data;
}
export async function fetchTransactions() {
  return (
    await api.get<{ items: ApiTransaction[]; total: number }>(
      "/api/transactions"
    )
  ).data;
}
export async function fetchRazorpayStatus() {
  return (await api.get<RazorpayStatus>("/api/razorpay/status")).data;
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
export async function beginRazorpayOAuth() {
  return (
    await api.get<{ authorization_url: string }>(
      "/api/razorpay/oauth/authorize"
    )
  ).data;
}
