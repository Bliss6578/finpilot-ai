/**
 * Flight Deck design reminder: charts make the difference between observed performance and future risk instantly legible through solid versus dashed paths.
 */
import { useState } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { cashFlowData, currency } from "@/data/mockData";
import { useReducedMotion } from "framer-motion";

const formatAxis = (value: number) => `₹${Math.round(value / 100000)}L`;

export function CashFlowChart({
  variant = "dashboard",
}: {
  variant?: "dashboard" | "full";
}) {
  const [range, setRange] = useState("30D");
  const reducedMotion = useReducedMotion();
  return (
    <div
      className={
        variant === "full" ? "cash-chart cash-chart-full" : "cash-chart"
      }
    >
      <div className="chart-head">
        <div>
          <h2>{variant === "full" ? "Money timeline" : "Cash flow"}</h2>
          <p>
            {variant === "full"
              ? "Actual balance, expected settlements, and projected outflows."
              : "Balance movement and 30-day forecast"}
          </p>
        </div>
        <div className="segmented-control">
          {["7D", "30D", "90D"].map(item => (
            <button
              key={item}
              onClick={() => setRange(item)}
              className={range === item ? "active" : ""}
            >
              {item}
            </button>
          ))}
        </div>
      </div>
      <div className="legend">
        <span>
          <i className="actual" />
          Actual balance
        </span>
        <span>
          <i className="forecast" />
          FinPilot forecast
        </span>
        <span>
          <i className="reserve" />
          Safe reserve
        </span>
      </div>
      <div className="chart-frame">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart
            data={cashFlowData}
            margin={{ top: 18, right: 22, bottom: 4, left: -7 }}
          >
            <defs>
              <linearGradient id="actualArea" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#635BFF" stopOpacity={0.18} />
                <stop offset="100%" stopColor="#635BFF" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="riskArea" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#F59E0B" stopOpacity={0} />
                <stop offset="100%" stopColor="#F59E0B" stopOpacity={0.1} />
              </linearGradient>
            </defs>
            <CartesianGrid
              vertical={false}
              stroke="#E7E8ED"
              strokeDasharray="3 3"
            />
            <XAxis
              dataKey="date"
              tickLine={false}
              axisLine={false}
              interval={variant === "full" ? 0 : 1}
              tick={{ fill: "#8A91A5", fontSize: 11, fontFamily: "Manrope" }}
            />
            <YAxis
              tickFormatter={formatAxis}
              tickLine={false}
              axisLine={false}
              width={48}
              tick={{ fill: "#8A91A5", fontSize: 11, fontFamily: "Manrope" }}
              domain={[0, 350000]}
            />
            <Tooltip
              content={<CashTooltip />}
              cursor={{ stroke: "#C8CCDA", strokeDasharray: "3 3" }}
            />
            <ReferenceLine
              y={100000}
              stroke="#F59E0B"
              strokeDasharray="4 5"
              label={{
                value: "Safe reserve ₹1L",
                position: "insideTopLeft",
                fill: "#B77900",
                fontSize: 11,
              }}
            />
            <Area
              type="monotone"
              dataKey="actual"
              stroke="#635BFF"
              strokeWidth={3}
              fill="url(#actualArea)"
              connectNulls={false}
              isAnimationActive={!reducedMotion}
              animationDuration={900}
              animationEasing="ease-out"
            />
            <Line
              type="monotone"
              dataKey="forecast"
              stroke="#635BFF"
              strokeWidth={3}
              strokeDasharray="7 6"
              dot={false}
              connectNulls={false}
              isAnimationActive={!reducedMotion}
              animationBegin={240}
              animationDuration={1000}
              animationEasing="ease-out"
            />
            <ReferenceLine x="Sep 12" stroke="#DC2626" strokeDasharray="3 3" />
          </AreaChart>
        </ResponsiveContainer>
      </div>
      <div className="forecast-callout">
        <span className="pulse-dot" />
        <div>
          <strong>Sep 12 · Projected balance {currency(58400)}</strong>
          <p>Forecast falls below your safe reserve.</p>
        </div>
        <span className="forecast-label">FORECAST</span>
      </div>
    </div>
  );
}

function CashTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: { value: number; name: string }[];
  label?: string;
}) {
  if (!active || !payload?.length) return null;
  const value = payload.find(entry => entry.value != null)?.value;
  return (
    <div className="chart-tooltip">
      <span>{label}</span>
      <strong>{value ? currency(value) : "—"}</strong>
      <small>
        {payload.some(item => item.name === "forecast")
          ? "Projected balance"
          : "Closing balance"}
      </small>
    </div>
  );
}

export function ScenarioChart({ scenario }: { scenario: number }) {
  const reducedMotion = useReducedMotion();
  const data = cashFlowData.map((point, index) => ({
    ...point,
    scenario: point.forecast
      ? Math.max(42000, point.forecast + (scenario - 142000) * (index / 9))
      : null,
  }));
  return (
    <div className="scenario-chart">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart
          data={data}
          margin={{ top: 12, right: 16, left: -14, bottom: 0 }}
        >
          <CartesianGrid
            vertical={false}
            stroke="#E7E8ED"
            strokeDasharray="3 3"
          />
          <XAxis
            dataKey="date"
            interval={2}
            tickLine={false}
            axisLine={false}
            tick={{ fill: "#8A91A5", fontSize: 10 }}
          />
          <YAxis
            tickFormatter={formatAxis}
            tickLine={false}
            axisLine={false}
            tick={{ fill: "#8A91A5", fontSize: 10 }}
          />
          <Tooltip content={<CashTooltip />} />
          <ReferenceLine y={100000} stroke="#F59E0B" strokeDasharray="4 5" />
          <Line
            type="monotone"
            dataKey="forecast"
            name="Current forecast"
            stroke="#A9AEC1"
            strokeWidth={2.5}
            dot={false}
            isAnimationActive={!reducedMotion}
            animationDuration={700}
          />
          <Line
            type="monotone"
            dataKey="scenario"
            name="Scenario forecast"
            stroke="#635BFF"
            strokeWidth={3}
            dot={false}
            isAnimationActive={!reducedMotion}
            animationDuration={850}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
