/**
 * Flight Deck design reminder: the timeline is the centrepiece, showing the business owner what will happen and why before offering the next decision route.
 */
import { Link } from "wouter";
import { CircleAlert, FlaskConical, Sparkles } from "lucide-react";
import { CashFlowChart } from "@/components/finance-charts";
import { PageHeader, Panel, SectionLabel, StatusPill } from "@/components/finpilot-ui";

export default function CashFlow() {
  return <>
    <PageHeader eyebrow="Forward view" title="Reserve breach projected Sep 12" description="Your current operating plan leaves a four-day cash buffer gap. Inspect the drivers, then test a corrective scenario." />
    <section className="cashflow-metrics"><ForecastStat label="Cash available" value="₹2,84,200" note="Today’s available balance" primary /><ForecastStat label="30-day forecast" value="₹1,42,000" note="Expected closing balance" /><ForecastStat label="Lowest balance" value="₹58,400" note="Expected on Sep 12" /><Panel className="forecast-stat"><SectionLabel>Risk level</SectionLabel><span className="stat-value"><StatusPill status="medium" /></span><p>Attention recommended</p></Panel></section>
    <Panel><CashFlowChart variant="full" /></Panel>
    <section className="cashflow-bottom"><Panel className="explanation-panel"><SectionLabel>Forecast drivers</SectionLabel><h2>Why is your balance changing?</h2><p>Expected settlements and planned operating expenses are shaping the next 30 days.</p><div className="explanation-cols"><div><div className="flow-list-title">Largest expected outflows</div><Flow label="Supplier payment" value="₹85,000" kind="out" /><Flow label="Advertising" value="₹50,000" kind="out" /><Flow label="Payroll" value="₹1,20,000" kind="out" /></div><div><div className="flow-list-title">Expected inflows</div><Flow label="Razorpay settlement" value="₹74,200" kind="in" /><Flow label="Expected sales" value="₹1,84,000" kind="in" /><Flow label="Outstanding invoices" value="₹55,200" kind="in" /></div></div></Panel><Panel className="risk-card"><div className="risk-title"><CircleAlert /><SectionLabel>Cash flow risk</SectionLabel></div><h2>Below safe reserve on Sep 12</h2><p>Your balance could fall below your configured <strong>₹1,00,000</strong> reserve for four days.</p><div className="risk-stat"><span>Projected balance</span><strong>₹58,400</strong></div><div className="risk-stat"><span>Risk duration</span><strong>4 days</strong></div><div className="risk-actions"><Link href="/ai-cfo" className="button-secondary"><Sparkles />Ask AI why</Link><Link href="/scenario-lab" className="button-primary"><FlaskConical />Run scenario</Link></div></Panel></section>
  </>;
}
function ForecastStat({ label, value, note, primary }: { label: string; value: string; note: string; primary?: boolean }) { return <Panel className={`forecast-stat ${primary ? "primary" : ""}`}><SectionLabel>{label}</SectionLabel><span className="stat-value">{value}</span><p>{note}</p></Panel>; }
function Flow({ label, value, kind }: { label: string; value: string; kind: "in" | "out" }) { return <div className={`flow-item ${kind}`}><span>{label}</span><strong>{value}</strong></div>; }
