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
import type { CashflowPoint } from "@/services/api";
import { useReducedMotion } from "framer-motion";

const formatAxis = (value: number) => {
  const absolute = Math.abs(value);
  if (absolute >= 10000000) return `₹${(value / 10000000).toFixed(1).replace(".0", "")}Cr`;
  if (absolute >= 100000) return `₹${(value / 100000).toFixed(1).replace(".0", "")}L`;
  if (absolute >= 1000) return `₹${(value / 1000).toFixed(0)}K`;
  return `₹${value.toFixed(0)}`;
};

export function CashFlowChart({
  variant = "dashboard",
  data,
  safeReserve = 100000,
  riskDate,
}: {
  variant?: "dashboard" | "full";
  data?: CashflowPoint[];
  safeReserve?: number;
  riskDate?: string;
}) {
  const [range, setRange] = useState<"7D" | "30D" | "90D">("30D");
  const reducedMotion = useReducedMotion();
  const allChartData = (data ?? cashFlowData).map(point => ({
    ...point,
    displayDate: "kind" in point
      ? new Intl.DateTimeFormat("en-IN", { day: "2-digit", month: "short" }).format(new Date(point.date))
      : point.date,
  }));
  const actual = allChartData.filter(point => point.actual != null);
  const forecast = allChartData.filter(point => point.forecast != null);
  const rangeDays = range === "7D" ? 7 : range === "30D" ? 30 : 90;
  const chartData = [...actual.slice(-rangeDays), ...forecast.slice(0, rangeDays)];
  const tickInterval = Math.max(Math.floor(chartData.length / 7) - 1, 0);
  const reserveLabel = `Safe reserve ${currency(safeReserve)}`;
  const visibleValues = chartData.flatMap(point =>
    [point.actual, point.forecast].filter(
      (value): value is number => typeof value === "number" && Number.isFinite(value),
    ),
  );
  const largestVisibleValue = Math.max(safeReserve, ...visibleValues, 1);
  const chartMaximum = Math.ceil((largestVisibleValue * 1.18) / 100000) * 100000;
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
              : `Balance movement · ${range} actual and forecast view`}
          </p>
        </div>
        <div className="segmented-control">
          {(["7D", "30D", "90D"] as const).map(item => (
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
          Paymentor forecast
        </span>
        <span>
          <i className="reserve" />
          Safe reserve
        </span>
      </div>
      <div className="chart-frame">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart
            data={chartData}
            margin={{ top: 18, right: 22, bottom: 4, left: -7 }}
          >
            <defs>
              <linearGradient id="actualArea" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#39BFFF" stopOpacity={0.24} />
                <stop offset="100%" stopColor="#39BFFF" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="riskArea" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#F59E0B" stopOpacity={0} />
                <stop offset="100%" stopColor="#F59E0B" stopOpacity={0.1} />
              </linearGradient>
            </defs>
            <CartesianGrid
              vertical={false}
              stroke="#2A527F"
              strokeOpacity={0.72}
              strokeDasharray="3 3"
            />
            <XAxis
              dataKey="displayDate"
              tickLine={false}
              axisLine={false}
              interval={tickInterval}
              tick={{ fill: "#B8CAE0", fontSize: 11, fontFamily: "Manrope", fontWeight: 600 }}
            />
            <YAxis
              tickFormatter={formatAxis}
              tickLine={false}
              axisLine={false}
              width={48}
              tick={{ fill: "#B8CAE0", fontSize: 11, fontFamily: "Manrope", fontWeight: 600 }}
              domain={[0, chartMaximum]}
            />
            <Tooltip
              content={<CashTooltip />}
              cursor={{ stroke: "#DDF3FF", strokeWidth: 1.5, strokeDasharray: "3 3" }}
            />
            <ReferenceLine
              y={safeReserve}
              stroke="#F59E0B"
              strokeDasharray="4 5"
              label={{
                value: reserveLabel,
                position: "insideTopLeft",
                fill: "#FFC24B",
                fontSize: 11,
                fontWeight: 700,
              }}
            />
            <Area
              type="monotone"
              dataKey="actual"
              stroke="#39BFFF"
              strokeWidth={3}
              fill="url(#actualArea)"
              connectNulls={false}
              activeDot={{ r: 5, fill: "#39BFFF", stroke: "#FFFFFF", strokeWidth: 2 }}
              isAnimationActive={!reducedMotion}
              animationDuration={900}
              animationEasing="ease-out"
            />
            <Line
              type="monotone"
              dataKey="forecast"
              stroke="#39BFFF"
              strokeWidth={3}
              strokeDasharray="7 6"
              dot={false}
              activeDot={{ r: 5, fill: "#39BFFF", stroke: "#FFFFFF", strokeWidth: 2 }}
              connectNulls={false}
              isAnimationActive={!reducedMotion}
              animationBegin={240}
              animationDuration={1000}
              animationEasing="ease-out"
            />
            {riskDate && (
              <ReferenceLine
                x={new Intl.DateTimeFormat("en-IN", { day: "2-digit", month: "short" }).format(new Date(riskDate))}
                stroke="#DC2626"
                strokeDasharray="3 3"
              />
            )}
          </AreaChart>
        </ResponsiveContainer>
      </div>
      {riskDate && <div className="forecast-callout">
        <span className="pulse-dot" />
        <div>
          <strong>{new Intl.DateTimeFormat("en-IN", { day: "2-digit", month: "short" }).format(new Date(riskDate))} · Forecast risk point</strong>
          <p>Forecast falls below your safe reserve.</p>
        </div>
        <span className="forecast-label">FORECAST</span>
      </div>}
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
    <div className="chart-tooltip" role="status" aria-live="polite">
      <span>{label}</span>
      <strong>{value != null ? currency(value) : "—"}</strong>
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
            stroke="#2A527F"
            strokeOpacity={0.72}
            strokeDasharray="3 3"
          />
          <XAxis
            dataKey="date"
            interval={2}
            tickLine={false}
            axisLine={false}
            tick={{ fill: "#B8CAE0", fontSize: 10, fontWeight: 600 }}
          />
          <YAxis
            tickFormatter={formatAxis}
            tickLine={false}
            axisLine={false}
            tick={{ fill: "#B8CAE0", fontSize: 10, fontWeight: 600 }}
          />
          <Tooltip
            content={<CashTooltip />}
            cursor={{ stroke: "#DDF3FF", strokeWidth: 1.5, strokeDasharray: "3 3" }}
          />
          <ReferenceLine y={100000} stroke="#F59E0B" strokeDasharray="4 5" />
          <Line
            type="monotone"
            dataKey="forecast"
            name="Current forecast"
            stroke="#7695B8"
            strokeWidth={2.5}
            dot={false}
            activeDot={{ r: 5, fill: "#7695B8", stroke: "#FFFFFF", strokeWidth: 2 }}
            isAnimationActive={!reducedMotion}
            animationDuration={700}
          />
          <Line
            type="monotone"
            dataKey="scenario"
            name="Scenario forecast"
            stroke="#39BFFF"
            strokeWidth={3}
            dot={false}
            activeDot={{ r: 5, fill: "#39BFFF", stroke: "#FFFFFF", strokeWidth: 2 }}
            isAnimationActive={!reducedMotion}
            animationDuration={850}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
