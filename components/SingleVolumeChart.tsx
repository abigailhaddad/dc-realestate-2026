"use client";

import { useState } from "react";
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import type { MonthlyRow } from "@/lib/types";

function fmt(n: number) {
  return new Intl.NumberFormat("en-US").format(n);
}
function fmtMoney(n: number | null) {
  if (n == null) return "—";
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `$${(n / 1_000).toFixed(0)}K`;
  return `$${n}`;
}

const MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

function yearOnly(m: string) {
  // Label only the first month of each year, with the year itself.
  if (!m || !m.endsWith("-01")) return "";
  return m.slice(0, 4);
}

function tooltipMonth(m: string) {
  if (!m) return "";
  const [year, mm] = m.split("-");
  const monthIdx = parseInt(mm, 10) - 1;
  return `${MONTH_NAMES[monthIdx]} ${year}`;
}

type Props = {
  monthly: MonthlyRow[];
  series: "residential" | "commercial";
  title: string;
  description: string;
  color: string;
};

export function SingleVolumeChart({ monthly, series, title, description, color }: Props) {
  const [mode, setMode] = useState<"count" | "median">("count");

  const rawKey = mode === "count" ? `${series}_count` : `${series}_median`;
  const trendKey = mode === "count"
    ? `${series}_count_avg12`
    : `${series}_median_avg12`;

  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between flex-wrap gap-2">
          <div>
            <CardTitle>{title}</CardTitle>
            <CardDescription>{description}</CardDescription>
          </div>
          <Tabs value={mode} onValueChange={(v) => setMode(v as "count" | "median")}>
            <TabsList>
              <TabsTrigger value="count">Volume</TabsTrigger>
              <TabsTrigger value="median">Median price</TabsTrigger>
            </TabsList>
          </Tabs>
        </div>
      </CardHeader>
      <CardContent>
        <div className="h-72 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={monthly} margin={{ top: 8, right: 12, left: 0, bottom: 4 }}>
              <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" vertical={false} />
              <XAxis
                dataKey="month"
                tick={{ fontSize: 14, fill: "var(--muted-foreground)" }}
                tickFormatter={yearOnly}
                interval={0}
                stroke="var(--border)"
              />
              <YAxis
                tick={{ fontSize: 13, fill: "var(--muted-foreground)" }}
                tickFormatter={mode === "count" ? fmt : fmtMoney}
                stroke="var(--border)"
                width={60}
              />
              <Tooltip
                contentStyle={{
                  background: "var(--popover)",
                  border: "1px solid var(--border)",
                  borderRadius: 8,
                  fontSize: 13,
                }}
                formatter={(v) => (typeof v === "number" ? (mode === "count" ? fmt(v) : fmtMoney(v)) : String(v))}
                labelFormatter={(label) => tooltipMonth(label as string)}
                labelStyle={{ color: "var(--foreground)", fontWeight: 600 }}
              />
              <Line
                type="monotone"
                dataKey={rawKey}
                stroke={color}
                strokeWidth={1.5}
                strokeOpacity={0.35}
                dot={false}
                name="Monthly"
              />
              <Line
                type="monotone"
                dataKey={trendKey}
                stroke={color}
                strokeWidth={2.5}
                dot={false}
                name="12-mo avg"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
