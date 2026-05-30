import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import type { ByUseRow } from "@/lib/types";

function fmt(n: number) {
  return new Intl.NumberFormat("en-US").format(n);
}
function fmtMoney(n: number) {
  if (!n) return "—";
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(2)}M`;
  if (n >= 1_000) return `$${(n / 1_000).toFixed(0)}K`;
  return `$${n}`;
}
function delta(curr: number, prev: number) {
  if (!prev) return "";
  const pct = ((curr - prev) / prev) * 100;
  const sign = pct >= 0 ? "+" : "";
  return `${sign}${pct.toFixed(0)}%`;
}

export function UseTypeTable({ rows }: { rows: ByUseRow[] }) {
  const sorted = rows
    .filter(r => r.total_count > 0)
    .sort((a, b) => b.total_count - a.total_count);

  return (
    <Card>
      <CardHeader>
        <CardTitle>By use type</CardTitle>
        <CardDescription>Sale count + median price by category, 2024 → 2026 YTD</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-left text-xs uppercase tracking-wide text-muted-foreground border-b">
              <tr>
                <th className="py-2 pr-3 font-medium">Category</th>
                <th className="py-2 px-3 font-medium text-right">2024 sales</th>
                <th className="py-2 px-3 font-medium text-right">2025 sales</th>
                <th className="py-2 px-3 font-medium text-right">2026 YTD</th>
                <th className="py-2 px-3 font-medium text-right">Δ 25→24</th>
                <th className="py-2 px-3 font-medium text-right">Median 2024</th>
                <th className="py-2 px-3 font-medium text-right">Median 2025</th>
                <th className="py-2 pl-3 font-medium text-right">Δ price</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {sorted.map(r => (
                <tr key={r.category} className="hover:bg-muted/50">
                  <td className="py-2 pr-3 font-medium">{r.label}</td>
                  <td className="py-2 px-3 text-right tabular-nums">{fmt(r.count_2024)}</td>
                  <td className="py-2 px-3 text-right tabular-nums">{fmt(r.count_2025)}</td>
                  <td className="py-2 px-3 text-right tabular-nums text-muted-foreground">{fmt(r.count_2026_ytd)}</td>
                  <td className="py-2 px-3 text-right tabular-nums text-muted-foreground">{delta(r.count_2025, r.count_2024)}</td>
                  <td className="py-2 px-3 text-right tabular-nums">{fmtMoney(r.median_2024)}</td>
                  <td className="py-2 px-3 text-right tabular-nums">{fmtMoney(r.median_2025)}</td>
                  <td className="py-2 pl-3 text-right tabular-nums text-muted-foreground">{delta(r.median_2025, r.median_2024)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}
