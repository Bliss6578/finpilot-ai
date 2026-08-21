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
  financial_summary: {
    gross_revenue: 542300,
    refund_amount: 12400,
    pending_refund_amount: 0,
    razorpay_fees: 10846,
    net_revenue: 519054,
    settled_amount: 442300,
  },
  settlement_counts: { pending: 1, completed: 4, failed: 0 },
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
  const financial = data.financial_summary ?? {
    gross_revenue: data.revenue,
    refund_amount: 0,
    pending_refund_amount: 0,
    razorpay_fees: 0,
    net_revenue: data.revenue,
    settled_amount: 0,
  };
  const settlements = data.settlement_counts ?? {
    pending: 0,
    completed: 0,
    failed: 0,
  };
  return (
    <>
      <div className="welcome-row">
        <div>
          <h1>
            {loading ? (
              "Reading business signals…"
            ) : (
              <>
                Net Razorpay revenue <span>{currency(financial.net_revenue)}</span>
              </>
            )}
          </h1>
          <p>
            {demoMode
              ? "Demo Mode is active."
              : `${data.transaction_counts.total} ${data.mode === "live" ? "Live Mode" : "Test Mode"} payment attempts are available for analysis.`}
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
          label="Net revenue"
          value={currency(financial.net_revenue)}
          change={demoMode ? "Demo" : "Live"}
          detail={`${currency(financial.gross_revenue)} gross revenue`}
        />
        <MetricCard
          label="Refunds"
          value={currency(financial.refund_amount)}
          change={`${data.transaction_counts.refunded} processed`}
          changeType={financial.refund_amount ? "down" : "flat"}
          detail={`${currency(financial.pending_refund_amount)} pending`}
        />
        <MetricCard
          label="Settled to bank"
          value={currency(financial.settled_amount)}
          change={`${settlements.completed} completed`}
          changeType="flat"
          detail={`${settlements.pending} pending settlements`}
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
            <span className="accent-mini">{currency(financial.gross_revenue)}</span>
          </div>
          <MoneyRow
            label="Captured payments"
            value={financial.gross_revenue}
            tone="positive"
          />
          <MoneyRow label="Settled to bank" value={financial.settled_amount} />
          <MoneyRow
            label="Awaiting settlement"
            value={Math.max(financial.net_revenue - financial.settled_amount, 0)}
          />
        </Panel>
        <Panel className="money-panel">
          <div className="money-panel-head">
            <div>
              <SectionLabel>Payment costs</SectionLabel>
              <h2>Current evidence</h2>
            </div>
          </div>
          <MoneyRow
            label="Processed refunds"
            value={financial.refund_amount}
            tone="negative"
          />
          <MoneyRow label="Razorpay fees" value={financial.razorpay_fees} />
          <MoneyRow
            label="Pending refunds"
            value={financial.pending_refund_amount}
            tone="negative"
          />
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
