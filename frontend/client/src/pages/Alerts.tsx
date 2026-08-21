/**
 * Flight Deck design reminder: alerts are ranked operational signals; each card surfaces the financial consequence and sends the owner to a relevant next investigation.
 */
import { useState } from "react";
import { useLocation } from "wouter";
import { alerts } from "@/data/mockData";
import { EmptyState, PageHeader, Panel } from "@/components/finpilot-ui";

export default function Alerts() {
  const [filter, setFilter] = useState("all"); const [, setLocation] = useLocation(); const visible = alerts.filter((alert) => filter === "all" || alert.severity === filter);
  const investigate = (severity: string) => setLocation(severity === "critical" ? "/cash-flow" : severity === "warning" ? "/transactions" : "/ai-cfo");
  return <><PageHeader eyebrow="Priority signals" title="Two financial signals need attention" description="The reserve breach and refund variance need a decision before they become material cash constraints." /><div className="alert-filters">{["all", "critical", "warning", "info", "resolved"].map((item) => <button key={item} onClick={() => setFilter(item)} className={`alert-filter ${filter === item ? "active" : ""}`}>{item === "all" ? "All alerts" : item[0].toUpperCase() + item.slice(1)}</button>)}</div><section className="alerts-list">{visible.length ? visible.map((alert) => <Panel className={`alert-card ${alert.severity}`} key={alert.id}><div className="severity-label">{alert.severity.toUpperCase()}</div><div><h2>{alert.title}</h2><p>{alert.message}</p><div className="alert-numbers"><div><span>{alert.severity === "critical" ? "Projected" : "Signal"}</span><strong>{alert.projected}</strong></div><div><span>{alert.severity === "critical" ? "Reserve" : "Context"}</span><strong>{alert.reserve}</strong></div></div></div><div className="alert-right"><span className="alert-date">{alert.date}</span><button onClick={() => investigate(alert.severity)} className="button-secondary">{alert.action}</button></div></Panel>) : <Panel><EmptyState title="You’re all clear" description="No financial risks are detected in this view right now." /></Panel>}</section></>;
}
