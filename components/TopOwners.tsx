"use client";

import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";

type Owner = {
  owner: string;
  parcels: number;
  assessed_total: number;
};

function fmt(n: number) {
  return new Intl.NumberFormat("en-US").format(n);
}
function fmtMoney(n: number) {
  if (n >= 1_000_000_000) return `$${(n / 1_000_000_000).toFixed(2)}B`;
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(0)}M`;
  return `$${n}`;
}

const ABBREV: Array<[RegExp, string]> = [
  [/^DISTRICT OF COLUMBIA HOUSING AUTHORITY$/i, "DC Housing Authority"],
  [/^DISTRICT OF COLUMBIA$/i, "District of Columbia (govt)"],
  [/^UNITED STATES OF AMERICA$/i, "United States (federal)"],
  [/^WASHINGTON METROPOLITAN AREA TRANSIT AUTHORITY.*/i, "WMATA"],
  [/^THE CATHOLIC UNIVERSITY OF AMERICA$/i, "Catholic Univ. of America"],
  [/^ROMAN CATHOLIC ARCHBISHOP OF WASHINGTON$/i, "Catholic Archdiocese of DC"],
];

function shorten(name: string) {
  for (const [pat, rep] of ABBREV) {
    if (pat.test(name)) return rep;
  }
  if (name.length > 34) return name.slice(0, 31) + "…";
  // Title-case the all-caps names so they read better.
  return name.replace(/\w\S*/g, (w) => w[0] + w.slice(1).toLowerCase());
}

export function TopOwners({ owners, limit = 20 }: { owners: Owner[]; limit?: number }) {
  const data = owners
    .slice(0, limit)
    .map((o) => ({ ...o, short: shorten(o.owner) }));

  return (
    <Card>
      <CardHeader>
        <CardTitle>Who owns DC&apos;s parcels</CardTitle>
        <CardDescription>
          Top {limit} owners by parcel count, citywide. Grouped by the
          {" "}<code className="px-1 py-0.5 bg-muted rounded text-xs">OWNERNAME</code>{" "}
          field across all 221,163 properties in ITSPE.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div style={{ height: Math.max(420, data.length * 28) }}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data} layout="vertical" margin={{ top: 8, right: 24, left: 0, bottom: 0 }}>
              <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" horizontal={false} />
              <XAxis
                type="number"
                tick={{ fontSize: 13, fill: "var(--muted-foreground)" }}
                tickFormatter={fmt}
                stroke="var(--border)"
              />
              <YAxis
                type="category"
                dataKey="short"
                tick={{ fontSize: 14, fill: "var(--foreground)" }}
                width={210}
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
                formatter={(v, name) => {
                  if (name === "parcels") return [fmt(v as number), "parcels"];
                  if (name === "assessed_total") return [fmtMoney(v as number), "total assessed"];
                  return [v, name];
                }}
                labelStyle={{ color: "var(--foreground)", fontWeight: 600 }}
              />
              <Bar dataKey="parcels" fill="var(--chart-1)" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
