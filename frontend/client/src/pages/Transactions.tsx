import { useEffect, useMemo, useState } from "react";
import {
  ChevronDown,
  MoreHorizontal,
  RefreshCw,
  Search,
  SlidersHorizontal,
  X,
} from "lucide-react";
import {
  EmptyState,
  PageHeader,
  Panel,
  SectionLabel,
  StatusPill,
} from "@/components/finpilot-ui";
import {
  currency,
  transactions as mockTransactions,
  type TransactionStatus,
} from "@/data/mockData";
import { fetchTransactions, type ApiTransaction } from "@/services/api";

type TransactionView = {
  id: string;
  order: string;
  customer: string;
  email: string;
  amount: number;
  method: string;
  status: TransactionStatus;
  fee: number;
  tax: number;
  date: string;
};
const demoMode = import.meta.env.VITE_DEMO_MODE === "true";
const statusMap: Record<string, TransactionStatus> = {
  captured: "Captured",
  failed: "Failed",
  refunded: "Refunded",
  pending: "Pending",
  authorized: "Pending",
};
export function normalizeTransaction(item: ApiTransaction): TransactionView {
  return {
    id: item.id,
    order: item.order_id ?? "—",
    customer: item.customer,
    email: item.email ?? "—",
    amount: item.amount,
    method: item.method
      ? item.method[0].toUpperCase() + item.method.slice(1)
      : "Other",
    status: statusMap[item.status.toLowerCase()] ?? "Pending",
    fee: item.fee,
    tax: item.tax,
    date: new Intl.DateTimeFormat("en-IN", {
      day: "2-digit",
      month: "short",
      hour: "numeric",
      minute: "2-digit",
    }).format(new Date(item.date)),
  };
}

export default function Transactions() {
  const [search, setSearch] = useState("");
  const [items, setItems] = useState<TransactionView[]>(
    demoMode ? mockTransactions : []
  );
  const [selected, setSelected] = useState<TransactionView | null>(null);
  const [loading, setLoading] = useState(!demoMode);
  const [error, setError] = useState<string | null>(null);
  const [razorpayMode, setRazorpayMode] = useState<"test" | "live">("test");
  const load = async () => {
    if (demoMode) return;
    setLoading(true);
    setError(null);
    try {
      const result = await fetchTransactions();
      setItems(result.items.map(normalizeTransaction));
      setRazorpayMode(result.mode);
    } catch {
      setError(
        "FinPilot could not reach the finance API. Confirm that the backend is running on port 8000."
      );
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => {
    void load();
  }, []);
  const filtered = useMemo(
    () =>
      items.filter(item =>
        `${item.customer} ${item.id} ${item.method}`
          .toLowerCase()
          .includes(search.toLowerCase())
      ),
    [items, search]
  );
  const captured = items.filter(item => item.status === "Captured");
  const failed = items.filter(item => item.status === "Failed");
  const refunded = items.filter(item => item.status === "Refunded");
  const totalValue = captured.reduce((sum, item) => sum + item.amount, 0);
  const captureRate = items.length ? (captured.length / items.length) * 100 : 0;
  return (
    <>
      <PageHeader
        eyebrow="Payment intelligence"
        title={
          loading
            ? "Loading payment signals…"
            : `${items.length} Razorpay payment${items.length === 1 ? "" : "s"}`
        }
        description={
          demoMode
            ? "Demo Mode is active. These records are sample business data."
            : `${razorpayMode === "live" ? "Live Mode" : "Test Mode"} records synchronized securely through the FinPilot backend.`
        }
        action={
          <button
            className="button-secondary"
            onClick={() => void load()}
            disabled={loading}
          >
            <RefreshCw />
            Refresh
          </button>
        }
      />
      {error && (
        <div className="panel api-error">
          <strong>Unable to load transactions</strong>
          <span>{error}</span>
          <button className="button-secondary" onClick={() => void load()}>
            Try again
          </button>
        </div>
      )}
      <section className="summary-cards">
        <Summary
          label="Captured value"
          value={currency(totalValue)}
          note={`${items.length} total attempts`}
        />
        <Summary
          label="Successful"
          value={String(captured.length)}
          note={`${captureRate.toFixed(1)}% capture rate`}
        />
        <Summary
          label="Failed"
          value={String(failed.length)}
          note={`${items.length ? ((failed.length / items.length) * 100).toFixed(1) : "0.0"}% of attempts`}
          type="fail"
        />
        <Summary
          label="Refunded"
          value={String(refunded.length)}
          note={currency(refunded.reduce((sum, item) => sum + item.amount, 0))}
        />
      </section>
      <div className="filter-bar">
        <label className="filter-input">
          <Search />
          <input
            value={search}
            onChange={event => setSearch(event.target.value)}
            placeholder="Search payment, customer or method"
          />
        </label>
        <button className="filter-button">
          Last 30 days <ChevronDown />
        </button>
        <button className="filter-button">
          All methods <ChevronDown />
        </button>
        <button className="filter-button">
          All statuses <ChevronDown />
        </button>
        <button className="filter-button">
          <SlidersHorizontal />
          More filters
        </button>
      </div>
      <Panel className="transactions-panel">
        <div className="table-panel-head">
          <div>
            <SectionLabel>Payment ledger</SectionLabel>
            <h2>
              {loading
                ? "Synchronizing…"
                : `${filtered.length} transactions in this view`}
            </h2>
          </div>
          <span className="id-code">
            Data source · {demoMode ? "Demo" : "Razorpay API"}
          </span>
        </div>
        {!loading && filtered.length === 0 ? (
          <EmptyState
            title="No matching transactions"
            description={
              items.length
                ? "Try changing your search or filters."
                : "Create a Razorpay test payment, then synchronize again."
            }
            action={
              <button className="button-primary" onClick={() => void load()}>
                Refresh Razorpay data
              </button>
            }
          />
        ) : (
          <div className="transaction-table-wrap">
            <table className="transaction-table">
              <thead>
                <tr>
                  <th>Payment ID</th>
                  <th>Customer</th>
                  <th>Amount</th>
                  <th>Method</th>
                  <th>Status</th>
                  <th>Fee</th>
                  <th>Date</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {filtered.map(transaction => (
                  <tr
                    key={transaction.id}
                    onClick={() => setSelected(transaction)}
                  >
                    <td className="id-code">{transaction.id}</td>
                    <td>
                      <strong className="customer">
                        {transaction.customer}
                      </strong>
                      <br />
                      <span className="id-code">{transaction.email}</span>
                    </td>
                    <td className="amount-cell">
                      {currency(transaction.amount)}
                    </td>
                    <td>{transaction.method}</td>
                    <td>
                      <StatusPill status={transaction.status} />
                    </td>
                    <td>{transaction.fee ? currency(transaction.fee) : "—"}</td>
                    <td>{transaction.date}</td>
                    <td>
                      <button
                        className="icon-button"
                        aria-label={`Open ${transaction.id}`}
                      >
                        <MoreHorizontal />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>
      <TransactionDrawer
        transaction={selected}
        onClose={() => setSelected(null)}
      />
    </>
  );
}
function Summary({
  label,
  value,
  note,
  type,
}: {
  label: string;
  value: string;
  note: string;
  type?: "fail";
}) {
  return (
    <Panel className="summary-card">
      <SectionLabel>{label}</SectionLabel>
      <strong>{value}</strong>
      <span className={type === "fail" ? "trend fail" : "trend"}>{note}</span>
    </Panel>
  );
}
function TransactionDrawer({
  transaction,
  onClose,
}: {
  transaction: TransactionView | null;
  onClose: () => void;
}) {
  if (!transaction) return null;

  return (
    <>
      <button
        className="drawer-backdrop open"
        onClick={onClose}
        aria-label="Close payment details"
      />
      <aside
        className="transaction-drawer open"
        role="dialog"
        aria-modal="true"
        aria-label="Payment details"
      >
        <>
          <div className="drawer-head">
            <div>
              <SectionLabel>Transaction detail</SectionLabel>
              <h2>Payment details</h2>
            </div>
            <button
              className="drawer-close"
              onClick={onClose}
              aria-label="Close payment details"
            >
              <X />
            </button>
          </div>
          <div className="drawer-amount">
            {currency(transaction.amount)}
            <div className="drawer-status">
              <StatusPill status={transaction.status} />
            </div>
          </div>
          <div className="drawer-detail-list">
            <Detail label="Payment ID" value={transaction.id} mono />
            <Detail label="Order ID" value={transaction.order} mono />
            <Detail label="Customer" value={transaction.customer} />
            <Detail label="Email" value={transaction.email} />
            <Detail label="Method" value={transaction.method} />
            <Detail label="Fee" value={currency(transaction.fee)} />
            <Detail label="Tax" value={currency(transaction.tax)} />
            <Detail label="Created" value={transaction.date} />
          </div>
          <div className="drawer-buttons">
            <button className="button-secondary">View raw data</button>
            <button className="button-primary">Ask AI about this</button>
          </div>
        </>
      </aside>
    </>
  );
}
function Detail({
  label,
  value,
  mono,
}: {
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div className="drawer-detail">
      <span>{label}</span>
      <strong className={mono ? "id-code" : ""}>{value}</strong>
    </div>
  );
}
