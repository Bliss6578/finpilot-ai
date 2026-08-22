import { useEffect, useState } from "react";
import { useLocation } from "wouter";
import { RefreshCw } from "lucide-react";
import { EmptyState, PageHeader, Panel } from "@/components/finpilot-ui";
import { fetchFinancialAlerts, markFinancialAlertRead, type FinancialAlert } from "@/services/api";

export default function Alerts() {
  const [filter, setFilter] = useState("all");
  const [alerts, setAlerts] = useState<FinancialAlert[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [, setLocation] = useLocation();
  const load = async (refresh = false) => { setLoading(true); try { setAlerts((await fetchFinancialAlerts(refresh)).items); setError(false); } catch { setError(true); } finally { setLoading(false); } };
  useEffect(() => { void load(true); }, []);
  const visible = alerts.filter(alert => filter === "all" || (filter === "resolved" ? alert.status === "read" : alert.severity === filter));
  const investigate = async (alert: FinancialAlert) => { if (alert.status === "unread") await markFinancialAlertRead(alert.id); setLocation(alert.type.includes("cash") || alert.type.includes("revenue") ? "/cash-flow" : alert.type.includes("payment") || alert.type.includes("refund") ? "/transactions" : "/ai-cfo"); };
  return <>
    <PageHeader eyebrow="Priority signals" title={`${alerts.filter(item => item.status === "unread").length} financial signals need attention`} description="Signals are calculated from this workspace's daily financial metrics and rolling baselines." />
    <div className="alert-filters">{["all", "critical", "warning", "info", "resolved"].map(item => <button key={item} onClick={() => setFilter(item)} className={`alert-filter ${filter === item ? "active" : ""}`}>{item === "all" ? "All alerts" : item[0].toUpperCase() + item.slice(1)}</button>)}<button className="button-secondary" onClick={() => void load(true)} disabled={loading}><RefreshCw className={loading ? "spin" : ""} />Refresh</button></div>
    {error && <div className="api-error"><strong>Alerts unavailable</strong><span>FinPilot could not calculate this workspace's signals.</span></div>}
    <section className="alerts-list">{visible.length ? visible.map(alert => <Panel className={`alert-card ${alert.severity}`} key={alert.id}><div className="severity-label">{alert.severity.toUpperCase()}</div><div><h2>{alert.title}</h2><p>{alert.description}</p><div className="alert-numbers"><div><span>Observed</span><strong>{alert.metric_value == null ? "—" : alert.metric_value.toFixed(1)}</strong></div><div><span>Baseline</span><strong>{alert.baseline_value == null ? "—" : alert.baseline_value.toFixed(1)}</strong></div></div></div><div className="alert-right"><span className="alert-date">{new Date(alert.created_at).toLocaleDateString("en-IN", { dateStyle: "medium" })}</span><button onClick={() => void investigate(alert)} className="button-secondary">Investigate</button></div></Panel>) : <Panel><EmptyState title={loading ? "Calculating signals…" : "You’re all clear"} description="No financial risks are detected in this workspace right now." /></Panel>}</section>
  </>;
}
