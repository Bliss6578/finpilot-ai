import { useEffect, useState } from "react";
import { Link } from "wouter";
import { ArrowRight, CircleAlert, Sparkles, TrendingUp } from "lucide-react";
import { CashFlowChart } from "@/components/finance-charts";
import {
  HealthGauge,
  HealthMetric,
  InsightCard,
  MetricCard,
  MoneyRow,
  Panel,
  SectionLabel,
} from "@/components/finpilot-ui";
import {
  currency,
  healthMetrics,
  transactions as mockTransactions,
} from "@/data/mockData";
import {
  fetchDashboard,
  type ApiTransaction,
  type DashboardResponse,
} from "@/services/api";

const demoMode = import.meta.env.VITE_DEMO_MODE === "true";
const mockDashboard: DashboardResponse = {
  revenue: 542300,
  payment_success_rate: 94.2,
  transaction_counts: { total: 7, captured: 4, failed: 1, refunded: 1 },
  recent_transactions: [],
  data_source: "empty",
};

export default function Dashboard() {
  const [data, setData] = useState<DashboardResponse>(mockDashboard);
  const [loading, setLoading] = useState(!demoMode);
  const [error, setError] = useState(false);
  useEffect(() => {
    if (demoMode) return;
    fetchDashboard()
      .then(setData)
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }, []);
  const recent: (ApiTransaction | (typeof mockTransactions)[number])[] =
    demoMode ? mockTransactions.slice(0, 5) : data.recent_transactions;
  return (
    <>
      <div className="welcome-row">
        <div>
          <h1>
            {loading ? (
              "Reading business signals…"
            ) : (
              <>
                Razorpay revenue <span>{currency(data.revenue)}</span>
              </>
            )}
          </h1>
          <p>
            {demoMode
              ? "Demo Mode is active."
              : `${data.transaction_counts.total} Test Mode payment attempts are available for analysis.`}
          </p>
        </div>
        <div className="live-pill">
          <i />
          {error
            ? "Backend unavailable"
            : demoMode
              ? "Demo signals"
              : "Razorpay signals are live"}
        </div>
      </div>
      {error && (
        <div className="panel api-error">
          <strong>Live dashboard data is unavailable</strong>
          <span>Start the backend on port 8000, then reload this page.</span>
        </div>
      )}
      <section className="panel health-panel">
        <div className="health-left">
          <HealthGauge />
          <div>
            <SectionLabel>Financial health</SectionLabel>
            <h2>Excellent condition</h2>
            <p>Forecast metrics remain in demo mode.</p>
            <p className="health-improved">Transaction metrics are live</p>
          </div>
        </div>
        <div className="health-right">
          <div className="health-right-head">
            <h3>What shapes your score</h3>
            <span>Forecast engine coming next</span>
          </div>
          <div className="health-metrics">
            {healthMetrics.map(metric => (
              <HealthMetric key={metric.label} {...metric} />
            ))}
          </div>
        </div>
      </section>
      <section className="metrics-grid">
        <MetricCard
          label="Razorpay revenue"
          value={currency(data.revenue)}
          change={demoMode ? "Demo" : "Live"}
          detail={`${data.transaction_counts.captured} captured payments`}
        />
        <MetricCard
          label="Payment attempts"
          value={String(data.transaction_counts.total)}
          change={`${data.transaction_counts.failed} failed`}
          changeType={data.transaction_counts.failed ? "down" : "flat"}
          detail="Razorpay Test Mode"
        />
        <MetricCard
          label="Refunded"
          value={String(data.transaction_counts.refunded)}
          change="Synced"
          changeType="flat"
          detail="Current imported records"
        />
        <MetricCard
          label="Payment success"
          value={`${data.payment_success_rate.toFixed(1)}%`}
          change={demoMode ? "Demo" : "Live"}
          detail="capture rate"
        />
      </section>
      <section className="dashboard-primary-grid">
        <Panel>
          <CashFlowChart />
        </Panel>
        <div className="decision-stack">
          <InsightCard
            tone="critical"
            icon={<CircleAlert />}
            title="Cash flow warning"
            action={<Link href="/cash-flow">View forecast</Link>}
          >
            Forecast information remains simulated until the forecasting service
            is connected.
          </InsightCard>
          <InsightCard
            tone="warning"
            icon={<TrendingUp />}
            title="Payment evidence"
            action={<Link href="/transactions">View transactions</Link>}
          >
            <strong>{data.transaction_counts.total}</strong> Razorpay records
            currently support your finance analysis.
          </InsightCard>
          <InsightCard
            tone="positive"
            icon={<Sparkles />}
            title="Live connection"
          >
            FinPilot is reading transaction data through the secure backend API.
          </InsightCard>
        </div>
      </section>
      <section className="two-up">
        <Panel className="money-panel">
          <div className="money-panel-head">
            <div>
              <SectionLabel>Incoming capital</SectionLabel>
              <h2>Money in</h2>
            </div>
            <span className="accent-mini">{currency(data.revenue)}</span>
          </div>
          <MoneyRow
            label="Captured payments"
            value={data.revenue}
            tone="positive"
          />
          <MoneyRow label="Settlements" value={0} />
          <MoneyRow label="Outstanding" value={0} />
        </Panel>
        <Panel className="money-panel">
          <div className="money-panel-head">
            <div>
              <SectionLabel>Payment costs</SectionLabel>
              <h2>Current evidence</h2>
            </div>
          </div>
          <MoneyRow
            label="Failed attempts"
            value={data.transaction_counts.failed}
          />
          <MoneyRow
            label="Refunded payments"
            value={data.transaction_counts.refunded}
            tone="negative"
          />
          <MoneyRow label="Expenses" value={0} />
        </Panel>
      </section>
      <Panel className="transactions-panel">
        <div className="table-panel-head">
          <div>
            <SectionLabel>Live evidence</SectionLabel>
            <h2>Recent transactions</h2>
          </div>
          <Link href="/transactions" className="text-link">
            View all transactions <ArrowRight />
          </Link>
        </div>
        <div className="transaction-table-wrap">
          <table className="transaction-table">
            <thead>
              <tr>
                <th>Customer</th>
                <th>Payment ID</th>
                <th>Amount</th>
                <th>Method</th>
                <th>Status</th>
                <th>Date</th>
              </tr>
            </thead>
            <tbody>
              {recent.map(item => {
                const api = "order_id" in item;
                const status =
                  item.status[0].toUpperCase() + item.status.slice(1);
                const date = api
                  ? new Date(item.date).toLocaleDateString("en-IN", {
                  day: "2-digit",
                      month: "short",
                    })
                  : item.date.split(",")[0];
                return (
                  <tr key={item.id}>
                    <td className="customer">{item.customer}</td>
                    <td className="id-code">{item.id}</td>
                    <td className="amount-cell">{currency(item.amount)}</td>
                    <td>{item.method ?? "Other"}</td>
                    <td>
                      <span
                        className={`status-pill status-${status === "Captured" ? "good" : status === "Failed" ? "critical" : status === "Refunded" ? "warning" : "neutral"}`}
                      >
                        <i />
                        {status}
                      </span>
                    </td>
                    <td>{date}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Panel>
    </>
  );
}
