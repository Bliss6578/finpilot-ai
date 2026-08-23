import { useEffect, useState } from "react";
import { Link } from "wouter";
import { CircleAlert, FlaskConical, RefreshCw, Sparkles } from "lucide-react";
import { CashFlowChart } from "@/components/finance-charts";
import { PageHeader, Panel, SectionLabel, StatusPill } from "@/components/paymentor-ui";
import { currency } from "@/data/mockData";
import { fetchCashflow, type CashflowResponse } from "@/services/api";
import { useDateRange } from "@/contexts/DateRangeContext";

export default function CashFlow() {
  const { days } = useDateRange();
  const [data, setData] = useState<CashflowResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      setData(await fetchCashflow(days, days));
    } catch {
      setError("Paymentor could not load this workspace's cash flow. Confirm the backend deployment is current, then try again.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, [days]);

  if (loading && !data) {
    return <div className="auth-loading"><span className="auth-loading-mark">✦</span> Loading this workspace’s money timeline…</div>;
  }

  if (!data) {
    return <Panel className="api-error"><strong>Cash-flow model unavailable</strong><span>{error}</span><button className="button-secondary" onClick={() => void load()}><RefreshCw />Try again</button></Panel>;
  }

  const { summary, drivers } = data;
  const riskTone = summary.risk_level === "low" ? "good" : summary.risk_level === "high" ? "critical" : "medium";
  const riskDate = summary.risk_level === "low" ? undefined : summary.lowest_balance_date;
  const modelSource = `${data.model.tenant_history_days} active Razorpay day${data.model.tenant_history_days === 1 ? "" : "s"} plus this client's saved cash policy and expense ledger. No training-dataset values are shown as client cash.`;
  const lowestDate = new Intl.DateTimeFormat("en-IN", { day: "2-digit", month: "short", year: "numeric" }).format(new Date(summary.lowest_balance_date));

  return <>
    <PageHeader
      eyebrow="Forward view"
      title={summary.risk_level === "low" ? "Cash reserve remains healthy" : `Reserve risk projected ${lowestDate}`}
      description={modelSource}
      action={<button className="button-secondary" onClick={() => void load()} disabled={loading}><RefreshCw />{loading ? "Refreshing…" : "Refresh forecast"}</button>}
    />
    {error && <div className="panel api-error"><strong>Showing the last successful forecast</strong><span>{error}</span></div>}
    <section className="cashflow-metrics">
      <ForecastStat label="Saved cash position" value={currency(summary.cash_available)} note={`Calculated through ${data.as_of}`} primary />
      <ForecastStat label={`${days}-day forecast`} value={currency(summary.forecast_closing_balance)} note="Expected closing balance" />
      <ForecastStat label="Lowest balance" value={currency(summary.lowest_balance)} note={`Expected ${lowestDate}`} />
      <Panel className="forecast-stat"><SectionLabel>Risk level</SectionLabel><span className="stat-value"><StatusPill status={riskTone} /></span><p>Safe reserve {currency(summary.safe_reserve)}</p></Panel>
    </section>
    <Panel>
      <CashFlowChart variant="full" data={data.points} safeReserve={summary.safe_reserve} riskDate={riskDate} />
    </Panel>
    <section className="cashflow-bottom">
      <Panel className="explanation-panel">
        <SectionLabel>Forecast drivers</SectionLabel>
        <h2>Why is your balance changing?</h2>
        <p>This forecast uses only this workspace’s observed Razorpay activity, recorded expenses and saved cash policy.</p>
        <div className="explanation-cols">
          <div>
            <div className="flow-list-title">Expected outflows · next 30 days</div>
            <Flow label="Expected outflow" value={currency(drivers.forecast_outflow)} kind="out" />
            <Flow label="Observed refunds" value={`${(drivers.return_rate * 100).toFixed(1)}% of receipts`} kind="out" />
            <Flow label="Observed payment costs" value={`${(drivers.payment_fee_ratio * 100).toFixed(1)}% of receipts`} kind="out" />
            <Flow label="Fixed operating cost" value={`${currency(drivers.fixed_daily_opex)} / day`} kind="out" />
          </div>
          <div>
            <div className="flow-list-title">Expected inflows</div>
            <Flow label="Expected Razorpay receipts" value={currency(drivers.forecast_inflow)} kind="in" />
            <Flow label="Data owner" value="This workspace" kind="in" />
            <Flow label="Evidence period" value={`${data.model.training_period[0]} – ${data.model.training_period[1]}`} kind="in" />
          </div>
        </div>
      </Panel>
      <Panel className="risk-card">
        <div className="risk-title"><CircleAlert /><SectionLabel>Cash-flow evidence</SectionLabel></div>
        <h2>{summary.risk_level === "low" ? "Reserve stays protected" : `Lowest point ${lowestDate}`}</h2>
        <p>{data.model.tenant_history_days < data.model.minimum_tenant_history_days ? "Confidence is limited because this client has sparse payment history. Paymentor will not invent missing business activity." : "The baseline is calculated from this workspace’s own payment history and financial settings."}</p>
        <div className="risk-stat"><span>Projected low</span><strong>{currency(summary.lowest_balance)}</strong></div>
        <div className="risk-stat"><span>Data source</span><strong>Client Razorpay + saved policy</strong></div>
        <div className="risk-actions"><Link href="/ai-cfo" className="button-secondary"><Sparkles />Ask AI why</Link><Link href="/scenario-lab" className="button-primary"><FlaskConical />Run scenario</Link></div>
      </Panel>
    </section>
  </>;
}

function ForecastStat({ label, value, note, primary }: { label: string; value: string; note: string; primary?: boolean }) {
  return <Panel className={`forecast-stat ${primary ? "primary" : ""}`}><SectionLabel>{label}</SectionLabel><span className="stat-value">{value}</span><p>{note}</p></Panel>;
}

function Flow({ label, value, kind }: { label: string; value: string; kind: "in" | "out" }) {
  return <div className={`flow-item ${kind}`}><span>{label}</span><strong>{value}</strong></div>;
}
