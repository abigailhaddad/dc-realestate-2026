import { Card, CardContent } from "@/components/ui/card";
import type { Summary } from "@/lib/types";

function fmt(n: number) {
  return new Intl.NumberFormat("en-US").format(n);
}

function delta(curr: number, prev: number) {
  if (!prev) return null;
  const pct = ((curr - prev) / prev) * 100;
  return pct;
}

function Card1({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <Card>
      <CardContent className="px-5 py-4">
        <div className="text-xs uppercase tracking-wide text-muted-foreground">{label}</div>
        <div className="mt-1 text-3xl font-semibold tracking-tight">{value}</div>
        {sub && <div className="mt-1 text-sm text-muted-foreground">{sub}</div>}
      </CardContent>
    </Card>
  );
}

export function SummaryCards({ summary }: { summary: Summary }) {
  const peak = Math.max(summary.count_2020, summary.count_2021, summary.count_2022);
  const sinceRecent = delta(summary.count_2025, summary.count_2024);
  const sincePeak = delta(summary.count_2025, peak);

  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
      <Card1 label="Total qualified sales" value={fmt(summary.total_sales)} sub={`Since ${summary.first_sale}`} />
      <Card1 label="Sales in 2025" value={fmt(summary.count_2025)} sub={sinceRecent !== null ? `${sinceRecent >= 0 ? "+" : ""}${sinceRecent.toFixed(1)}% vs 2024` : undefined} />
      <Card1 label="Sales 2026 YTD" value={fmt(summary.count_2026_ytd)} sub={`Through ${summary.last_sale}`} />
      <Card1 label="Vs. peak (2021)" value={`${sincePeak !== null ? sincePeak.toFixed(0) : "?"}%`} sub={`Peak was ${fmt(peak)} sales`} />
    </div>
  );
}
