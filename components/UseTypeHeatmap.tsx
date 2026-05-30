import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import type { ByUseRow } from "@/lib/types";

const YEARS = ["2020", "2021", "2022", "2023", "2024", "2025", "2026"];

function fmt(n: number) {
  return new Intl.NumberFormat("en-US").format(n);
}
function fmtMoney(n: number) {
  if (!n) return "—";
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(2)}M`;
  if (n >= 1_000) return `$${(n / 1_000).toFixed(0)}K`;
  return `$${n}`;
}

function cellColor(value: number, max: number) {
  if (!max || value === 0) return { bg: "var(--muted)", fg: "var(--muted-foreground)" };
  const t = Math.min(1, value / max);
  // 92% lightness at t=0 to 35% lightness at t=1, with chart-1 hue (zinc-orange)
  const lightness = 92 - t * 57;
  return {
    bg: `hsl(28 65% ${lightness}%)`,
    fg: t > 0.55 ? "white" : "var(--foreground)",
  };
}

export function UseTypeHeatmap({ rows }: { rows: ByUseRow[] }) {
  const sorted = rows
    .filter(r => r.total_count > 0)
    .sort((a, b) => b.total_count - a.total_count);

  // Color scale per row (so a category's variation is visible even if it's
  // 100× smaller than another category). Use the row's annualized max.
  return (
    <Card>
      <CardHeader>
        <CardTitle>Sales by use type, by year</CardTitle>
        <CardDescription>
          Annual sale counts. The 2026 column annualizes the YTD count
          (multiplied by 12 / 4 = 3) so it&apos;s comparable to other years; the
          actual count so far is in the bottom of each 2026 cell.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-left text-xs uppercase tracking-wide text-muted-foreground border-b">
              <tr>
                <th className="py-2 pr-3 font-medium">Category</th>
                {YEARS.map(y => (
                  <th key={y} className="py-2 px-3 font-medium text-center">
                    {y}{y === "2026" && <span className="ml-1 text-muted-foreground">proj.</span>}
                  </th>
                ))}
                <th className="py-2 pl-3 font-medium text-right">Median ($)</th>
              </tr>
            </thead>
            <tbody>
              {sorted.map(r => {
                const annualValues = YEARS.map(y =>
                  y === "2026" ? r.count_2026_annualized : (r.counts_by_year?.[y] ?? 0)
                );
                const rowMax = Math.max(...annualValues);
                return (
                  <tr key={r.category} className="border-b last:border-b-0">
                    <td className="py-2 pr-3 font-medium">{r.label}</td>
                    {YEARS.map((y, i) => {
                      const annual = annualValues[i];
                      const { bg, fg } = cellColor(annual, rowMax);
                      const ytdCount = y === "2026" ? r.count_2026_ytd : null;
                      return (
                        <td key={y} className="py-1 px-1 text-center">
                          <div
                            className="rounded mx-auto px-2 py-1.5 tabular-nums leading-tight"
                            style={{ background: bg, color: fg, minWidth: 56 }}
                          >
                            <div className="font-medium">{fmt(annual)}</div>
                            {ytdCount !== null && (
                              <div className="text-xs opacity-70">{fmt(ytdCount)} ytd</div>
                            )}
                          </div>
                        </td>
                      );
                    })}
                    <td className="py-2 pl-3 text-right tabular-nums text-muted-foreground">
                      {fmtMoney(r.medians_by_year?.["2025"] || r.median_2025 || r.median_price)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}
