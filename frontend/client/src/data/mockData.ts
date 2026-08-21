/**
 * Flight Deck design reminder: mock data is shaped as future FinPilot API responses so the UI emphasizes forward-looking decisions, not just reporting.
 */
export type TransactionStatus = "Captured" | "Failed" | "Refunded" | "Pending";

export const currency = (value: number, compact = false) =>
  new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
    notation: compact ? "compact" : "standard",
  }).format(value);

export const healthMetrics = [
  { label: "Cash flow", value: 91, tone: "good" },
  { label: "Revenue growth", value: 86, tone: "good" },
  { label: "Payment success", value: 94, tone: "good" },
  { label: "Refund health", value: 72, tone: "watch" },
  { label: "Expense control", value: 83, tone: "good" },
  { label: "Settlement health", value: 90, tone: "good" },
];

export const cashFlowData = [
  { date: "Aug 16", actual: 264200, forecast: null, inflow: 42000, outflow: 21000 },
  { date: "Aug 20", actual: 272800, forecast: null, inflow: 28500, outflow: 19900 },
  { date: "Aug 24", actual: 268900, forecast: null, inflow: 25100, outflow: 29000 },
  { date: "Aug 28", actual: 284200, forecast: 284200, inflow: 47300, outflow: 32000 },
  { date: "Sep 01", actual: null, forecast: 251600, inflow: 18200, outflow: 50800 },
  { date: "Sep 05", actual: null, forecast: 196400, inflow: 26700, outflow: 81900 },
  { date: "Sep 09", actual: null, forecast: 124800, inflow: 19200, outflow: 90800 },
  { date: "Sep 12", actual: null, forecast: 58400, inflow: 7400, outflow: 73800 },
  { date: "Sep 16", actual: null, forecast: 142000, inflow: 104400, outflow: 20800 },
  { date: "Sep 20", actual: null, forecast: 173500, inflow: 62400, outflow: 30900 },
];

export const transactions = [
  { id: "pay_Q8H0J4G9", customer: "Ananya Roy", email: "ananya.roy@email.com", amount: 2499, method: "UPI", status: "Captured" as TransactionStatus, fee: 47, tax: 8, date: "Aug 21, 3:42 PM", order: "order_XYZ123" },
  { id: "pay_Q8H0J31F", customer: "Ishaan Mehta", email: "ishaan.mehta@email.com", amount: 8999, method: "Card", status: "Captured" as TransactionStatus, fee: 164, tax: 30, date: "Aug 21, 2:16 PM", order: "order_TEM334" },
  { id: "pay_Q8H0J07C", customer: "Mira Kapoor", email: "mira.kapoor@email.com", amount: 1499, method: "UPI", status: "Refunded" as TransactionStatus, fee: 28, tax: 5, date: "Aug 21, 11:08 AM", order: "order_MKR991" },
  { id: "pay_Q8H0HT2A", customer: "Rahul Shah", email: "rahul.shah@email.com", amount: 3299, method: "Netbanking", status: "Failed" as TransactionStatus, fee: 0, tax: 0, date: "Aug 20, 7:14 PM", order: "order_RSH284" },
  { id: "pay_Q8H0GR9P", customer: "Nisha Iyer", email: "nisha.iyer@email.com", amount: 5299, method: "Card", status: "Captured" as TransactionStatus, fee: 96, tax: 17, date: "Aug 20, 5:41 PM", order: "order_NIY448" },
  { id: "pay_Q8H0F93D", customer: "Vikram Sood", email: "vikram.sood@email.com", amount: 749, method: "UPI", status: "Pending" as TransactionStatus, fee: 14, tax: 2, date: "Aug 20, 2:02 PM", order: "order_VSO872" },
  { id: "pay_Q8H0E18Z", customer: "Kabir Singh", email: "kabir.singh@email.com", amount: 4199, method: "Wallet", status: "Captured" as TransactionStatus, fee: 77, tax: 14, date: "Aug 19, 6:30 PM", order: "order_KSI118" },
];

export const alerts = [
  { id: 1, severity: "critical", title: "Cash Flow Risk", message: "Projected balance falls below your configured reserve.", date: "Sep 12", projected: "₹58,400", reserve: "₹1,00,000", action: "Investigate" },
  { id: 2, severity: "warning", title: "Refund Spike", message: "Refund rate increased 18% compared with your 30-day average.", date: "Today", projected: "14 affected transactions", reserve: "₹21,400 potential impact", action: "View transactions" },
  { id: 3, severity: "info", title: "Settlement delayed", message: "Your expected Razorpay settlement has shifted by one business day.", date: "Tomorrow", projected: "₹74,200 expected", reserve: "Updated forecast", action: "View forecast" },
  { id: 4, severity: "resolved", title: "UPI success rate recovered", message: "Payment success returned above your weekly average after a brief decline.", date: "Aug 19", projected: "96.1% success", reserve: "Resolved", action: "View trend" },
];

export const suggestedQuestions = [
  "Why did profit decrease this month?",
  "Can I afford to hire two employees?",
  "Why are refunds increasing?",
  "How much can I safely spend on marketing?",
  "What financial risks should I worry about?",
];

