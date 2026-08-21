import { useEffect, useState } from "react";
import { Link } from "wouter";
import { CircleAlert, FlaskConical, RefreshCw, Sparkles } from "lucide-react";
import { CashFlowChart } from "@/components/finance-charts";
import { PageHeader, Panel, SectionLabel, StatusPill } from "@/components/finpilot-ui";
import { currency } from "@/data/mockData";
import { fetchCashflow, type CashflowResponse } from "@/services/api";

export default function CashFlow() {
  const [data, setData] = useState<CashflowResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      setData(await fetchCashflow(90, 90));
    } catch {
      setError("FinPilot could not load the cash-flow model. Confirm the backend deployment is current, then try again.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  if (loading && !data) {
    return <div className="auth-loading"><span className="auth-loading-mark">✦</span> Training the money timeline…</div>;
  }

  if (!data) {
    return <Panel className="api-error"><strong>Cash-flow model unavailable</strong><span>{error}</span><button className="button-secondary" onClick={() => void load()}><RefreshCw />Try again</button></Panel>;
  }

  const { summary, drivers } = data;
  const riskTone = summary.risk_level === "low" ? "good" : summary.risk_level === "high" ? "critical" : "medium";
  const riskDate = summary.risk_level === "low" ? undefined : summary.lowest_balance_date;
  const modelSource = data.data_source === "razorpay_history"
    ? `Personalized from ${data.model.tenant_history_days} days of this workspace's Razorpay history.`
    : data.data_source === "razorpay_plus_dataset"
      ? `Showing this workspace's ${data.model.tenant_history_days} active Razorpay day${data.model.tenant_history_days === 1 ? "" : "s"}; the retail model fills missing history until ${data.model.minimum_tenant_history_days} active days are available.`
      : `Dataset-backed demo prior trained on ${data.model.trained_on}; connect and sync Razorpay to overlay current workspace activity.`;
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
      <ForecastStat label="Modeled cash position" value={currency(summary.cash_available)} note={`Calculated through ${data.as_of}`} primary />
      <ForecastStat label="30-day forecast" value={currency(summary.forecast_closing_balance)} note="Expected closing balance" />
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
        <p>The model combines learned retail seasonality with transparent cash-flow assumptions.</p>
        <div className="explanation-cols">
          <div>
            <div className="flow-list-title">Expected outflows · next 30 days</div>
            <Flow label="Total modeled outflow" value={currency(drivers.forecast_outflow)} kind="out" />
            <Flow label="Variable operating costs" value={`${(drivers.variable_cost_ratio * 100).toFixed(0)}% of sales`} kind="out" />
            <Flow label="Returns learned from dataset" value={`${(drivers.return_rate * 100).toFixed(1)}%`} kind="out" />
            <Flow label="Fixed operating cost" value={`${currency(drivers.fixed_daily_opex)} / day`} kind="out" />
          </div>
          <div>
            <div className="flow-list-title">Expected inflows</div>
            <Flow label="Modeled sales receipts" value={currency(drivers.forecast_inflow)} kind="in" />
            <Flow label="Model" value={data.model.name} kind="in" />
            <Flow label="Source period" value={`${data.model.training_period[0]} – ${data.model.training_period[1]}`} kind="in" />
          </div>
        </div>
      </Panel>
      <Panel className="risk-card">
        <div className="risk-title"><CircleAlert /><SectionLabel>Cash-flow evidence</SectionLabel></div>
        <h2>{summary.risk_level === "low" ? "Reserve stays protected" : `Lowest point ${lowestDate}`}</h2>
        <p>{data.data_source === "razorpay_history" ? "The sales baseline comes from this workspace. Expense assumptions remain modeled until expense tracking is connected." : data.data_source === "razorpay_plus_dataset" ? "Synced Razorpay activity is shown immediately. Dataset seasonality fills days without enough workspace history." : "This is an isolated hackathon demo forecast. It does not claim that the dataset contains real bank balances or expenses."}</p>
        <div className="risk-stat"><span>Projected low</span><strong>{currency(summary.lowest_balance)}</strong></div>
        <div className="risk-stat"><span>Data source</span><strong>{data.data_source === "razorpay_history" ? "Razorpay + model" : data.data_source === "razorpay_plus_dataset" ? "Current Razorpay + dataset" : "Retail dataset demo"}</strong></div>
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
