"use client";

import { useState } from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";

type UseMixRow = {
  category: string;
  count: number;          // ITSPE row count (condo-unit-inflated)
  parcels?: number;       // unique-SSL count (matches the map)
  share_count: number;
  land_sqft: number;
  share_land: number;
  assessed: number;
  share_assessed: number;
};

const PRETTY: Record<string, string> = {
  single_family: "Single-family home",
  condo: "Condo",
  multifamily: "Multifamily",
  office: "Office",
  retail: "Retail",
  hotel_lodging: "Hotel / lodging",
  industrial: "Industrial",
  commercial_other: "Commercial (other)",
  institutional: "Institutional (religious / school / govt)",
  vacant: "Vacant land",
  other: "Other",
};

type Mode = "parcels" | "count" | "land" | "assessed";

function fmt(n: number) {
  return new Intl.NumberFormat("en-US").format(n);
}
function fmtAcres(sqft: number) {
  // 43,560 sqft = 1 acre. Show acres for readability.
  const acres = sqft / 43560;
  if (acres >= 1000) return `${(acres / 1000).toFixed(1)}K acres`;
  if (acres >= 1) return `${acres.toFixed(0)} acres`;
  return `${fmt(sqft)} sqft`;
}
function fmtMoney(n: number) {
  if (n >= 1_000_000_000) return `$${(n / 1_000_000_000).toFixed(1)}B`;
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(0)}M`;
  return `$${fmt(n)}`;
}

export function UseMixChart({ rows }: { rows: UseMixRow[] }) {
  const [mode, setMode] = useState<Mode>("parcels");
  const totalParcels = rows.reduce((s, r) => s + (r.parcels ?? 0), 0);
  const totalUnits = rows.reduce((s, r) => s + r.count, 0);

  const data = rows
    .filter((r) => (r.parcels ?? r.count) > 0)
    .map((r) => ({
      ...r,
      label: PRETTY[r.category] || r.category,
      value:
        mode === "parcels" ? (r.parcels ?? 0) :
        mode === "count" ? r.count :
        mode === "land" ? r.land_sqft :
        r.assessed,
    }))
    .sort((a, b) => b.value - a.value);

  const valueFmt =
    mode === "parcels" ? fmt :
    mode === "count" ? fmt :
    mode === "land" ? fmtAcres :
    fmtMoney;

  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between flex-wrap gap-2">
          <div>
            <CardTitle>What DC is made of</CardTitle>
            <CardDescription>
              {mode === "parcels" && (
                <>One row per parcel ({fmt(totalParcels)} total). This matches what you&apos;d
                count if you walked the city — a condo building counts once regardless
                of unit count.</>
              )}
              {mode === "count" && (
                <>One row per ITSPE record ({fmt(totalUnits)} total). Each condo unit
                is its own row, so condos dominate. Different question, different
                count.</>
              )}
              {mode === "land" && (
                <>Total lot area (LANDAREA) by category. Lots with multiple condo
                units count once per parcel here.</>
              )}
              {mode === "assessed" && (
                <>Total assessed value (NEWTOTAL) by category — closer to
                &ldquo;dollar weight of DC.&rdquo;</>
              )}
            </CardDescription>
          </div>
          <Tabs value={mode} onValueChange={(v) => setMode(v as Mode)}>
            <TabsList>
              <TabsTrigger value="parcels">Parcels</TabsTrigger>
              <TabsTrigger value="count">Units (condos split)</TabsTrigger>
              <TabsTrigger value="land">Lot area</TabsTrigger>
              <TabsTrigger value="assessed">$ value</TabsTrigger>
            </TabsList>
          </Tabs>
        </div>
      </CardHeader>
      <CardContent>
        <div style={{ height: Math.max(360, data.length * 32) }}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data} layout="vertical" margin={{ top: 8, right: 100, left: 0, bottom: 0 }}>
              <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" horizontal={false} />
              <XAxis
                type="number"
                tick={{ fontSize: 13, fill: "var(--muted-foreground)" }}
                tickFormatter={(v) => {
                  if (mode === "assessed") {
                    if (v >= 1_000_000_000) return `$${(v / 1_000_000_000).toFixed(0)}B`;
                    if (v >= 1_000_000) return `$${(v / 1_000_000).toFixed(0)}M`;
                  }
                  if (mode === "land") {
                    if (v >= 43560000) return `${Math.round(v / 43560 / 1000)}K ac`;
                    if (v >= 43560) return `${Math.round(v / 43560)} ac`;
                  }
                  return fmt(v);
                }}
                stroke="var(--border)"
              />
              <YAxis
                type="category"
                dataKey="label"
                tick={{ fontSize: 14, fill: "var(--foreground)" }}
                width={240}
                stroke="var(--border)"
                interval={0}
              />
              <Tooltip
                contentStyle={{
                  background: "var(--popover)",
                  border: "1px solid var(--border)",
                  borderRadius: 8,
                  fontSize: 13,
                }}
                formatter={(v) => valueFmt(typeof v === "number" ? v : Number(v))}
                labelStyle={{ color: "var(--foreground)", fontWeight: 600 }}
              />
              <Bar dataKey="value" fill="var(--chart-1)" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
