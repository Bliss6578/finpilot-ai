/**
 * Flight Deck design reminder: the Scenario Lab turns a contemplated decision into a clear before-and-after cash outcome, then gives an actionable recommendation.
 */
import { useEffect, useState } from "react";
import { Sparkles } from "lucide-react";
import { toast } from "sonner";
import { ScenarioChart } from "@/components/finance-charts";
import { PageHeader, Panel, SectionLabel } from "@/components/paymentor-ui";
import { currency } from "@/data/mockData";
import { askAICFO, fetchBusinessProfile, simulateScenario, updateBusinessProfile, type ScenarioResult } from "@/services/api";

export default function ScenarioLab() {
  const [tab, setTab] = useState<"quick" | "ask">("quick"); const [revenue, setRevenue] = useState(10); const [expense, setExpense] = useState(5); const [monthly, setMonthly] = useState(50000); const [oneTime, setOneTime] = useState(100000); const [hires, setHires] = useState(2); const [salary, setSalary] = useState(40000); const [scenarioPrompt, setScenarioPrompt] = useState(""); const [result, setResult] = useState<ScenarioResult>(); const [running, setRunning] = useState(false);
  useEffect(() => { fetchBusinessProfile().then(profile => { const saved = profile.scenario_preferences ?? {}; setRevenue(saved.revenue ?? 10); setExpense(saved.expense ?? 5); setMonthly(saved.monthly ?? 50000); setOneTime(saved.one_time ?? 100000); setHires(saved.hires ?? 2); setSalary(saved.salary ?? 40000); setScenarioPrompt(saved.prompt ?? ""); }).catch(() => undefined); }, []);
  const baseline = (result?.baseline.cash_90d_paise ?? 0) / 100; const scenario = (result?.scenario.cash_90d_paise ?? 0) / 100; const impact = (result?.difference.cash_90d_paise ?? 0) / 100;
  const run = async () => {
    if (tab === "ask" && scenarioPrompt.trim().length < 4) {
      toast.error("Describe the decision first", { description: "Include the amount, percentage, or number of people Paymentor should model." });
      return;
    }
    setRunning(true);
    try {
      await updateBusinessProfile({ scenario_preferences: { revenue, expense, monthly, one_time: oneTime, hires, salary, prompt: scenarioPrompt.trim() } });
      const next = tab === "ask"
        ? (await askAICFO(scenarioPrompt.trim())).scenario_result
        : await simulateScenario("custom", { revenue_change_percent: revenue, expense_change_percent: expense, monthly_cost_paise: (monthly + hires * salary) * 100, one_time_paise: oneTime * 100 });
      if (!next) throw new Error("Paymentor needs a financial amount or percentage to calculate this scenario.");
      setResult(next);
      toast.success("Scenario saved and updated", { description: "The result uses the values you entered and belongs only to this workspace." });
    } catch (reason: any) {
      toast.error("Unable to run scenario", { description: reason?.response?.data?.detail ?? reason?.message ?? "Add current cash and expense assumptions in Settings first." });
    } finally {
      setRunning(false);
    }
  };
  return <>
    <PageHeader eyebrow="Decision simulator" title="Test a decision before cash is committed" description="Model operating changes against your 90-day cash position and keep the reserve policy in view." />
    <section className="scenario-layout"><Panel className="scenario-control-panel"><SectionLabel>Build a scenario</SectionLabel><div className="scenario-tabs"><button className={tab === "quick" ? "active" : ""} onClick={() => setTab("quick")}>Quick simulator</button><button className={tab === "ask" ? "active" : ""} onClick={() => setTab("ask")}>Ask Paymentor</button></div>{tab === "quick" ? <><Range label="Revenue" value={revenue} display={`${revenue > 0 ? "+" : ""}${revenue}%`} min={-20} max={40} onChange={setRevenue} /><Range label="Expenses" value={expense} display={`${expense > 0 ? "+" : ""}${expense}%`} min={-20} max={30} onChange={setExpense} /><div className="field-pair"><Field label="New monthly expense" value={monthly} onChange={setMonthly} /><Field label="One-time expense" value={oneTime} onChange={setOneTime} /></div><div className="field-pair"><Field label="New hires" value={hires} onChange={setHires} plain /><Field label="Salary per hire" value={salary} onChange={setSalary} /></div></> : <div className="ask-scenario"><SectionLabel>What are you considering?</SectionLabel><textarea value={scenarioPrompt} onChange={event => setScenarioPrompt(event.target.value)} placeholder="For example: hire 2 developers at ₹40,000 each per month, or increase marketing by ₹75,000." maxLength={600} /><div className="drawer-detail"><span>Calculation source</span><strong>Your description</strong></div><div className="drawer-detail"><span>Forecast period</span><strong>90 days</strong></div></div>}<button className="button-primary" onClick={() => void run()} disabled={running || (tab === "ask" && !scenarioPrompt.trim())}>{running ? "Calculating…" : result ? "Re-run simulation" : "Run simulation"}</button></Panel><Panel className="scenario-result-panel"><div className="scenario-result-head"><div><SectionLabel>90-day outcome</SectionLabel><h2>{result ? "Your scenario forecast" : "Run a tenant-scoped scenario"}</h2><p>Compare this decision with your current expected cash position.</p></div><div className="scenario-legend"><span><i />Current</span><span><i className="scenario-line" />Scenario</span></div></div><ScenarioChart scenario={scenario} /><div className="scenario-result-grid"><Result label="Current 90-day balance" value={currency(baseline)} /><Result label="Scenario balance" value={currency(scenario)} /><Result label="Impact" value={`${impact < 0 ? "−" : "+"}${currency(Math.abs(impact))}`} negative={impact < 0} /><Result label="Runway" value={result?.scenario.runway_months == null ? "Cash-generative" : `${result.scenario.runway_months.toFixed(1)} months`} /></div><div className="recommendation-wide"><div className="spark"><Sparkles /></div><div><h3>Paymentor recommendation</h3><p>{result ? (scenario < 0 ? "This scenario exhausts available cash within 90 days. Reduce or delay the planned cost before approval." : result.disclaimer) : "Enter a current cash balance in Settings, then run a scenario to receive a deterministic result."}</p></div></div></Panel></section>
  </>;
}
function Range({ label, value, display, min, max, onChange }: { label: string; value: number; display: string; min: number; max: number; onChange: (value: number) => void }) { return <div className="control-group"><label>{label}<strong>{display}</strong></label><input className="range-input" type="range" min={min} max={max} value={value} onChange={(event) => onChange(Number(event.target.value))} /></div>; }
function Field({ label, value, onChange, plain }: { label: string; value: number; onChange: (value: number) => void; plain?: boolean }) { return <div className="mini-field"><label>{label}</label><input value={value} onChange={(event) => onChange(Number(event.target.value.replace(/[^0-9]/g, "")))} inputMode="numeric" aria-label={label} /><small className="id-code">{plain ? "people" : "INR"}</small></div>; }
function Result({ label, value, negative }: { label: string; value: string; negative?: boolean }) { return <div className={`result-stat ${negative ? "negative" : ""}`}><span>{label}</span><strong>{value}</strong></div>; }
