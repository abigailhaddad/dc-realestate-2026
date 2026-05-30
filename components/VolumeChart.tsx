"use client";

import { useState } from "react";
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import type { MonthlyRow } from "@/lib/types";

const COLORS = {
  residential: "var(--chart-1)",
  commercial: "var(--chart-3)",
};

function fmt(n: number) {
  return new Intl.NumberFormat("en-US").format(n);
}
function fmtMoney(n: number | null) {
  if (n == null) return "—";
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `$${(n / 1_000).toFixed(0)}K`;
  return `$${n}`;
}

export function VolumeChart({ monthly }: { monthly: MonthlyRow[] }) {
  const [mode, setMode] = useState<"count" | "median">("count");

  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between flex-wrap gap-2">
          <div>
            <CardTitle>Sales by month</CardTitle>
            <CardDescription>Qualified arms-length sales, citywide, since January 2020</CardDescription>
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
        <div className="h-80 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={monthly} margin={{ top: 8, right: 12, left: 0, bottom: 4 }}>
              <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" vertical={false} />
              <XAxis
                dataKey="month"
                tick={{ fontSize: 13, fill: "var(--muted-foreground)" }}
                tickFormatter={(m) => (m.endsWith("-01") || m.endsWith("-07") ? m : "")}
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
                labelStyle={{ color: "var(--foreground)", fontWeight: 600 }}
              />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Line
                type="monotone"
                dataKey={mode === "count" ? "residential_count" : "residential_median"}
                stroke={COLORS.residential}
                strokeWidth={2}
                dot={false}
                name="Residential"
              />
              <Line
                type="monotone"
                dataKey={mode === "count" ? "commercial_count" : "commercial_median"}
                stroke={COLORS.commercial}
                strokeWidth={2}
                dot={false}
                name="Commercial"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
