import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { TopSale } from "@/lib/types";

function fmt(n: number | null) {
  if (n == null) return "—";
  return new Intl.NumberFormat("en-US").format(n);
}

function fmtMoney(n: number) {
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(2)}M`;
  if (n >= 1_000) return `$${(n / 1_000).toFixed(0)}K`;
  return `$${n}`;
}

const CATEGORY_VARIANTS: Record<string, "default" | "secondary" | "outline" | "destructive"> = {
  office: "secondary",
  retail: "secondary",
  multifamily: "default",
  condo: "default",
  single_family: "default",
  institutional: "outline",
  hotel_lodging: "secondary",
  industrial: "outline",
  commercial_other: "secondary",
  vacant: "outline",
  other: "outline",
};

export function TopSalesTable({ rows }: { rows: TopSale[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Largest sales since Jan 2025</CardTitle>
        <CardDescription>Top transactions by price (all use types)</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-left text-xs uppercase tracking-wide text-muted-foreground border-b">
              <tr>
                <th className="py-2 pr-3 font-medium">Date</th>
                <th className="py-2 px-3 font-medium">Address</th>
                <th className="py-2 px-3 font-medium">Use</th>
                <th className="py-2 px-3 font-medium">Neighborhood</th>
                <th className="py-2 px-3 font-medium text-right">Bldg sqft</th>
                <th className="py-2 pl-3 font-medium text-right">Price</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {rows.slice(0, 25).map((r, i) => (
                <tr key={i} className="hover:bg-muted/50">
                  <td className="py-2 pr-3 tabular-nums text-muted-foreground">{r.sale_date}</td>
                  <td className="py-2 px-3">
                    <div className="font-medium">{r.address.split(" WASHINGTON")[0]}</div>
                    {r.buyer && <div className="text-xs text-muted-foreground">{r.buyer}</div>}
                  </td>
                  <td className="py-2 px-3">
                    <Badge variant={CATEGORY_VARIANTS[r.use_category] ?? "outline"}>
                      {r.use_description || r.use_category}
                    </Badge>
                  </td>
                  <td className="py-2 px-3 text-muted-foreground">{r.cluster_name}</td>
                  <td className="py-2 px-3 text-right tabular-nums text-muted-foreground">{fmt(r.building_sqft)}</td>
                  <td className="py-2 pl-3 text-right tabular-nums font-semibold">{fmtMoney(r.sale_price)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}
