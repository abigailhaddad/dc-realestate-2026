"use client";

import { useMemo } from "react";
import { MapContainer, TileLayer, CircleMarker, Tooltip } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import type { TopSale } from "@/lib/types";

const CATEGORY_COLOR: Record<string, string> = {
  single_family: "#5a9bd4",
  condo: "#3a6ea5",
  multifamily: "#1f3b73",
  office: "#6b3a8e",
  retail: "#e89240",
  hotel_lodging: "#cc5577",
  industrial: "#8a6a3c",
  commercial_other: "#9a8a4a",
  institutional: "#4a8a5a",
  vacant: "#999999",
  other: "#cc6a99",
};

function fmtMoney(n: number) {
  if (n >= 1_000_000_000) return `$${(n / 1_000_000_000).toFixed(2)}B`;
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `$${(n / 1_000).toFixed(0)}K`;
  return `$${n}`;
}

export function BiggestSalesMapImpl({ rows, limit = 50 }: { rows: TopSale[]; limit?: number }) {
  const sales = rows.filter((r) => r.lat != null && r.lon != null).slice(0, limit);

  const maxPrice = Math.max(...sales.map((s) => s.sale_price), 1);

  // Bubble area ∝ price, so radius ∝ sqrt(price). 6 → 36 px.
  function radius(price: number) {
    const t = Math.sqrt(price / maxPrice);
    return Math.max(5, Math.min(38, 5 + t * 33));
  }

  const totals = useMemo(() => {
    const total = sales.reduce((s, r) => s + r.sale_price, 0);
    const biggest = sales[0];
    return { total, biggest };
  }, [sales]);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Where the big money moved</CardTitle>
        <CardDescription>
          The {sales.length} largest qualified sales recorded since January 2025.
          Bubble size scales with sale price; color is the use category.
          Combined: {fmtMoney(totals.total)}. Biggest:
          {" "}<strong>{fmtMoney(totals.biggest?.sale_price || 0)}</strong>{" "}
          at {totals.biggest?.address.split(" WASHINGTON")[0]}.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="h-[520px] w-full rounded-md overflow-hidden border">
          <MapContainer
            center={[38.905, -77.018]}
            zoom={12}
            scrollWheelZoom={false}
            style={{ height: "100%", width: "100%" }}
            preferCanvas
          >
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
            {sales.map((s, i) => {
              const color = CATEGORY_COLOR[s.use_category] || "#666";
              return (
                <CircleMarker
                  key={i}
                  center={[s.lat as number, s.lon as number]}
                  radius={radius(s.sale_price)}
                  pathOptions={{
                    color,
                    weight: 1.2,
                    fillColor: color,
                    fillOpacity: 0.55,
                  }}
                >
                  <Tooltip direction="top" offset={[0, -radius(s.sale_price)]}>
                    <div className="text-xs">
                      <div className="font-semibold">{fmtMoney(s.sale_price)}</div>
                      <div>{s.address.split(" WASHINGTON")[0]}</div>
                      <div className="text-muted-foreground">
                        {s.use_description || s.use_category} · {s.sale_date}
                      </div>
                    </div>
                  </Tooltip>
                </CircleMarker>
              );
            })}
          </MapContainer>
        </div>
      </CardContent>
    </Card>
  );
}
