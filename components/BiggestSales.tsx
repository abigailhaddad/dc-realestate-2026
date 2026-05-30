import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { TopSale } from "@/lib/types";

function fmtMoney(n: number) {
  if (n >= 1_000_000_000) return `$${(n / 1_000_000_000).toFixed(2)}B`;
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `$${(n / 1_000).toFixed(0)}K`;
  return `$${n}`;
}

export function BiggestSales({ rows, limit = 12 }: { rows: TopSale[]; limit?: number }) {
  const top = rows.slice(0, limit);
  const totalTopN = top.reduce((s, r) => s + r.sale_price, 0);
  const biggest = top[0];
  const overTenMil = rows.filter((r) => r.sale_price >= 10_000_000).length;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Where the big money moved</CardTitle>
        <CardDescription>
          The {limit} largest qualified sales recorded since January 2025 — a small
          slice of citywide volume that accounts for most of the dollar weight.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {biggest && (
          <div className="mb-5 grid gap-3 grid-cols-1 sm:grid-cols-3">
            <HeadStat
              value={fmtMoney(totalTopN)}
              label={`Top ${limit} combined`}
            />
            <HeadStat
              value={fmtMoney(biggest.sale_price)}
              label={`Biggest deal · ${biggest.sale_date}`}
              sub={biggest.address.split(" WASHINGTON")[0]}
            />
            <HeadStat
              value={overTenMil.toString()}
              label="Deals over $10M"
            />
          </div>
        )}

        <div className="space-y-1">
          {top.map((r, i) => (
            <div key={i} className="flex items-baseline gap-3 py-2 border-b last:border-b-0">
              <div className="w-6 text-sm text-muted-foreground tabular-nums">{i + 1}.</div>
              <div className="w-32 text-base font-semibold tabular-nums">{fmtMoney(r.sale_price)}</div>
              <div className="w-24 text-xs text-muted-foreground tabular-nums">{r.sale_date}</div>
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium truncate">{r.address.split(" WASHINGTON")[0]}</div>
                <div className="text-xs text-muted-foreground truncate">
                  {r.cluster_name || "—"}
                </div>
              </div>
              <Badge variant="outline" className="hidden sm:inline-flex">
                {r.use_description || r.use_category}
              </Badge>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

function HeadStat({ value, label, sub }: { value: string; label: string; sub?: string }) {
  return (
    <div className="rounded-lg border p-4 bg-accent/30">
      <div className="text-2xl font-semibold tabular-nums">{value}</div>
      <div className="text-xs uppercase tracking-wide text-muted-foreground mt-1">{label}</div>
      {sub && <div className="text-xs text-muted-foreground mt-0.5 truncate">{sub}</div>}
    </div>
  );
}
