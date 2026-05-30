"use client";

import { useMemo } from "react";
import { MapContainer, TileLayer, Polygon, Tooltip } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";

type ClusterRow = {
  cluster_num: number;
  cluster_name: string;
  rings: number[][][];
  parcels: number;
  assessed_total: number;
  assessed_exempt: number;
  exempt_share: number;
};

function fmtMoney(n: number) {
  if (n >= 1_000_000_000) return `$${(n / 1_000_000_000).toFixed(2)}B`;
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(0)}M`;
  if (n >= 1_000) return `$${(n / 1_000).toFixed(0)}K`;
  return `$${n}`;
}

function colorFor(share: number) {
  if (share <= 0) return "hsl(28 65% 96%)";
  const t = Math.min(1, share / 0.5); // 50% exempt is the visual cap
  const lightness = 92 - t * 60;
  return `hsl(28 70% ${lightness}%)`;
}

export function TaxExemptMapImpl({ clusters }: { clusters: ClusterRow[] }) {
  const totalExempt = useMemo(
    () => clusters.reduce((s, c) => s + c.assessed_exempt, 0),
    [clusters],
  );
  const totalAssessed = useMemo(
    () => clusters.reduce((s, c) => s + c.assessed_total, 0),
    [clusters],
  );
  const overallShare = totalAssessed ? totalExempt / totalAssessed : 0;

  const polys = useMemo(
    () =>
      clusters.map((c) => ({
        ...c,
        leafletRings: c.rings.map((ring) => ring.map(([x, y]) => [y, x] as [number, number])),
      })),
    [clusters],
  );

  return (
    <Card>
      <CardHeader>
        <CardTitle>DC&apos;s tax-exempt land</CardTitle>
        <CardDescription>
          Each neighborhood cluster shaded by the assessed value held by
          religious, educational, and special-purpose owners (use codes 081–089).
          Hover for the dollar total. Citywide, {fmtMoney(totalExempt)} of assessed
          value ({(overallShare * 100).toFixed(1)}%) is in this category.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="h-[480px] w-full rounded-md overflow-hidden border">
          <MapContainer
            center={[38.905, -77.018]}
            zoom={12}
            scrollWheelZoom={false}
            style={{ height: "100%", width: "100%" }}
          >
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
            {polys.map((p) => (
              <Polygon
                key={p.cluster_num}
                positions={p.leafletRings}
                pathOptions={{
                  color: "#444",
                  weight: 1,
                  fillColor: colorFor(p.exempt_share),
                  fillOpacity: 0.78,
                }}
              >
                <Tooltip sticky direction="top">
                  <div className="text-xs">
                    <div className="font-semibold">{p.cluster_name}</div>
                    <div className="text-muted-foreground">Cluster {p.cluster_num}</div>
                    <div className="mt-1">
                      {(p.exempt_share * 100).toFixed(1)}% tax-exempt
                    </div>
                    <div>{fmtMoney(p.assessed_exempt)} of {fmtMoney(p.assessed_total)}</div>
                  </div>
                </Tooltip>
              </Polygon>
            ))}
          </MapContainer>
        </div>

        <div className="mt-4 flex items-center gap-3 text-sm text-foreground">
          <span>0% exempt</span>
          <div
            className="h-4 flex-1 rounded"
            style={{
              background:
                "linear-gradient(to right, hsl(28 65% 96%), hsl(28 70% 80%), hsl(28 70% 60%), hsl(28 70% 35%))",
            }}
          />
          <span>≥50% exempt</span>
        </div>
      </CardContent>
    </Card>
  );
}
