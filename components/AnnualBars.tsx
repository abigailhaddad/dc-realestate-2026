"use client";

import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Cell,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";

type AnnualRow = {
  year: string;
  residential_count: number;
  commercial_count: number;
  residential_median: number | null;
  commercial_median: number | null;
};

function fmt(n: number) {
  return new Intl.NumberFormat("en-US").format(n);
}

export function AnnualBars({ rows, series, title, description, color }: {
  rows: AnnualRow[];
  series: "residential" | "commercial";
  title: string;
  description: string;
  color: string;
}) {
  const max = Math.max(...rows.map(r => r[`${series}_count` as keyof AnnualRow] as number));
  // mark partial years (current year — fewer sales)
  const currYear = new Date().getFullYear().toString();

  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="h-60 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={rows} margin={{ top: 8, right: 12, left: 0, bottom: 4 }}>
              <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="year" tick={{ fontSize: 14, fill: "var(--muted-foreground)" }} stroke="var(--border)" />
              <YAxis
                tick={{ fontSize: 13, fill: "var(--muted-foreground)" }}
                tickFormatter={fmt}
                stroke="var(--border)"
                width={60}
                domain={[0, Math.ceil(max * 1.1)]}
              />
              <Tooltip
                contentStyle={{
                  background: "var(--popover)",
                  border: "1px solid var(--border)",
                  borderRadius: 8,
                  fontSize: 13,
                }}
                formatter={(v) => (typeof v === "number" ? fmt(v) : String(v))}
                labelStyle={{ color: "var(--foreground)", fontWeight: 600 }}
              />
              <Bar
                dataKey={`${series}_count`}
                name={series === "residential" ? "Residential sales" : "Commercial sales"}
                radius={[4, 4, 0, 0]}
              >
                {rows.map((r, i) => (
                  <Cell key={i} fill={color} fillOpacity={r.year === currYear ? 0.4 : 1} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
        <p className="mt-2 text-xs text-muted-foreground">
          {rows.some(r => r.year === currYear) && "Lighter bar = current year, partial."}
        </p>
      </CardContent>
    </Card>
  );
}
