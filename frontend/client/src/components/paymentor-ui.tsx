/**
 * Flight Deck design reminder: these primitives pair calm, paper-light analytical surfaces with Signal Indigo for decision-critical information.
 */
import { ReactNode } from "react";
import { ArrowDownRight, ArrowUpRight, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";
import { currency, TransactionStatus } from "@/data/mockData";
import { useAnimatedValue } from "@/hooks/useAnimatedValue";
import { motion, useReducedMotion } from "framer-motion";

export function SectionLabel({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return <p className={cn("section-label", className)}>{children}</p>;
}

export function Panel({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return <section className={cn("panel", className)}>{children}</section>;
}

export function PageHeader({
  eyebrow,
  title,
  description,
  action,
}: {
  eyebrow?: string;
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <div className="page-header">
      <div>
        {eyebrow && <SectionLabel>{eyebrow}</SectionLabel>}
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      {action && <div className="page-header-action">{action}</div>}
    </div>
  );
}

export function StatusPill({
  status,
}: {
  status:
    | TransactionStatus
    | "good"
    | "warning"
    | "critical"
    | "info"
    | "resolved"
    | "medium";
}) {
  const styles: Record<string, string> = {
    Captured: "status-good",
    Failed: "status-critical",
    Refunded: "status-warning",
    Pending: "status-neutral",
    good: "status-good",
    warning: "status-warning",
    critical: "status-critical",
    info: "status-info",
    resolved: "status-neutral",
    medium: "status-warning",
  };
  return (
    <span className={cn("status-pill", styles[status])}>
      <i />
      {status}
    </span>
  );
}

export function MetricCard({
  label,
  value,
  change,
  changeType = "up",
  detail,
  spark = [18, 31, 25, 39, 34, 48, 52],
}: {
  label: string;
  value: string;
  change?: string;
  changeType?: "up" | "down" | "flat";
  detail?: string;
  spark?: number[];
}) {
  const animated = useAnimatedValue(value);
  const points = spark
    .map(
      (point, index) => `${(index / (spark.length - 1)) * 100},${55 - point}`
    )
    .join(" ");
  return (
    <Panel className="metric-card">
      <div className="metric-topline">
        <SectionLabel>{label}</SectionLabel>
        <div className={cn("metric-change", changeType)}>
          {changeType === "up" ? (
            <ArrowUpRight />
          ) : changeType === "down" ? (
            <ArrowDownRight />
          ) : null}
          {change}
        </div>
      </div>
      <div className="metric-value" ref={animated.ref}>{animated.display}</div>
      <div className="metric-bottom">
        <span>{detail}</span>
        <svg viewBox="0 0 100 60" aria-hidden="true">
          <polyline points={points} fill="none" />
        </svg>
      </div>
    </Panel>
  );
}

export function HealthGauge({ score = 87 }: { score?: number }) {
  const circumference = 2 * Math.PI * 43;
  const reducedMotion = useReducedMotion();
  const animated = useAnimatedValue(String(score), 950);
  return (
    <div className="health-gauge-wrap">
      <svg
        className="health-gauge"
        viewBox="0 0 108 108"
        aria-label={`Financial Health Score ${score} out of 100`}
      >
        <circle cx="54" cy="54" r="43" className="gauge-track" />
        <motion.circle
          cx="54"
          cy="54"
          r="43"
          className="gauge-progress"
          style={{ strokeDasharray: circumference }}
          initial={reducedMotion ? false : { strokeDashoffset: circumference }}
          whileInView={{ strokeDashoffset: circumference * (1 - score / 100) }}
          viewport={{ once: true, amount: 0.5 }}
          transition={{ duration: 0.95, ease: [0.22, 1, 0.36, 1] }}
        />
      </svg>
      <div className="gauge-copy" ref={animated.ref}>
        <strong>{animated.display}</strong>
        <span>out of 100</span>
      </div>
    </div>
  );
}

export function HealthMetric({
  label,
  value,
  tone = "good",
}: {
  label: string;
  value: number;
  tone?: string;
}) {
  return (
    <div className="health-metric">
      <div>
        <span>{label}</span>
        <strong>{value}</strong>
      </div>
      <div className="micro-progress">
        <i className={tone} style={{ width: `${value}%` }} />
      </div>
    </div>
  );
}

export function InsightCard({
  tone,
  icon,
  title,
  children,
  action,
}: {
  tone: "critical" | "warning" | "positive";
  icon: ReactNode;
  title: string;
  children: ReactNode;
  action?: ReactNode;
}) {
  return (
    <Panel className={cn("insight-card", tone)}>
      <div className="insight-icon">{icon}</div>
      <div>
        <SectionLabel>{title}</SectionLabel>
        <p>{children}</p>
        {action && (
          <div className="insight-action">
            {action}
            <ChevronRight />
          </div>
        )}
      </div>
    </Panel>
  );
}

export function MoneyRow({
  label,
  value,
  tone,
}: {
  label: string;
  value: number;
  tone?: "positive" | "negative";
}) {
  return (
    <div className="money-row">
      <span>{label}</span>
      <strong className={tone}>{currency(value)}</strong>
    </div>
  );
}

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <div className="empty-state">
      <div className="empty-orbit" />
      <h3>{title}</h3>
      <p>{description}</p>
      {action}
    </div>
  );
}
