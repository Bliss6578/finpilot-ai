import { useEffect, useState } from "react";
import { Check, RefreshCw, ShieldAlert } from "lucide-react";
import { toast } from "sonner";
import { EmptyState, PageHeader, Panel, SectionLabel } from "@/components/finpilot-ui";
import { createApproval, decideApproval, fetchAnomalies, fetchApprovals, fetchRecommendations, fetchRevenueLeaks, fetchSettlementIntelligence, type AnomalyResult, type Approval, type Recommendation, type RevenueLeakResponse, type SettlementIntelligence } from "@/services/api";

export default function Intelligence() {
  const [leaks, setLeaks] = useState<RevenueLeakResponse>();
  const [settlements, setSettlements] = useState<SettlementIntelligence>();
  const [anomalies, setAnomalies] = useState<AnomalyResult>();
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const load = async () => { setLoading(true); try { const [l, s, a, r, p] = await Promise.all([fetchRevenueLeaks(), fetchSettlementIntelligence(), fetchAnomalies(), fetchRecommendations(), fetchApprovals()]); setLeaks(l); setSettlements(s); setAnomalies(a); setRecommendations(r.items); setApprovals(p.items); setError(false); } catch { setError(true); } finally { setLoading(false); } };
  useEffect(() => { void load(); }, []);
  const requestApproval = async (item: Recommendation) => { await createApproval(item); toast.success("Approval requested"); await load(); };
  const decide = async (id: string, decision: "approved" | "rejected") => { const result = await decideApproval(id, decision); toast.success(decision === "approved" ? (result.executed ? "Approved and executed" : "Approval recorded") : "Recommendation rejected"); await load(); };
  return <>
    <PageHeader eyebrow="Operational intelligence" title={`₹${(leaks?.potential_leak ?? 0).toLocaleString("en-IN")} potential revenue leakage`} description="Observed leaks, settlement reconciliation, tenant-trained anomalies and owner-controlled execution." />
    <div className="page-actions"><button className="button-secondary" onClick={() => void load()} disabled={loading}><RefreshCw className={loading ? "spin" : ""} />Refresh intelligence</button></div>
    {error && <div className="api-error"><strong>Intelligence unavailable</strong><span>FinPilot could not calculate every workspace signal.</span></div>}
    <section className="intelligence-grid">
      <Panel><SectionLabel>Revenue leak detector</SectionLabel><h2>₹{(leaks?.potential_leak ?? 0).toLocaleString("en-IN")}</h2><p>{leaks?.methodology ?? "Calculating observed leakage…"}</p><div className="signal-list">{leaks?.signals.map(signal => <div key={signal.type}><span>{signal.title}<small>{signal.confidence}</small></span><strong>₹{signal.amount.toLocaleString("en-IN")}</strong></div>)}</div></Panel>
      <Panel><SectionLabel>Settlement reconciliation</SectionLabel><h2>{settlements?.status === "reconciled" ? "Reconciled" : "Needs attention"}</h2><div className="signal-list"><div><span>Expected net settlement</span><strong>₹{(settlements?.expected_net_settlement ?? 0).toLocaleString("en-IN")}</strong></div><div><span>Variance</span><strong>₹{(settlements?.variance ?? 0).toLocaleString("en-IN")}</strong></div><div><span>Average delay</span><strong>{settlements?.average_delay_days == null ? "—" : `${settlements.average_delay_days}d`}</strong></div></div>{settlements?.limitations.map(item => <small key={item}>{item}</small>)}</Panel>
      <Panel><SectionLabel>Anomaly model</SectionLabel><h2>{anomalies?.trained ? `${anomalies.anomalies.length} unusual days` : "Learning history"}</h2><p>{anomalies?.trained ? `Isolation Forest trained on ${anomalies.observations} client days.` : `${anomalies?.observations ?? 0}/${anomalies?.minimum_days ?? 14} active days available. No trained-model claim is made yet.`}</p></Panel>
    </section>
    <Panel className="recommendation-panel"><SectionLabel>Recommendation engine</SectionLabel><h2>Prioritized next moves</h2>{recommendations.length ? <div className="recommendation-list">{recommendations.map(item => <div key={item.id}><span className={`priority-chip ${item.priority}`}>{item.priority}</span><div><strong>{item.title}</strong><small>{item.basis.replaceAll("_", " ")}{item.impact ? ` · ₹${item.impact.toLocaleString("en-IN")} at issue` : ""}</small></div><button className="button-primary" onClick={() => void requestApproval(item)}>Request approval</button></div>)}</div> : <EmptyState title="No material action is required" description="Leak, settlement, anomaly and cash-flow checks did not cross an action threshold." />}</Panel>
    <Panel className="approval-panel"><SectionLabel>Approval workflow</SectionLabel><h2>Owner-controlled actions</h2>{approvals.length ? <div className="recommendation-list">{approvals.map(item => <div key={item.id}><ShieldAlert /><div><strong>{item.title}</strong><small>{item.status}{item.executed_at ? " · executed inside FinPilot" : ""}</small></div>{item.status === "pending" && <span className="approval-actions"><button className="button-secondary" onClick={() => void decide(item.id, "rejected")}>Reject</button><button className="button-primary" onClick={() => void decide(item.id, "approved")}><Check />Approve</button></span>}</div>)}</div> : <p>No approval requests yet.</p>}</Panel>
  </>;
}
