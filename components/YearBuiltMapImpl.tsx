"use client";

import { useMemo, useState } from "react";
import { MapContainer, TileLayer, CircleMarker } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";

type ParcelData = {
  categories: string[];
  // [cat_idx, year_built, land_area_sqft, lat, lon]
  parcels: [number, number | null, number, number, number][];
};

function colorFor(year: number | null): string {
  if (year == null) return "#aaa";
  if (year < 1900) return "#1a3d70";  // deep blue — original DC
  if (year < 1950) return "#3a8aa8";  // teal — rowhouse + interwar era
  if (year < 2000) return "#e8a73a";  // amber — postwar to end of century
  return "#a82022";                    // red — 21st century
}

const LEGEND = [
  { label: "pre-1900", color: "#1a3d70" },
  { label: "1900-1949", color: "#3a8aa8" },
  { label: "1950-1999", color: "#e8a73a" },
  { label: "2000+", color: "#a82022" },
  { label: "unknown", color: "#aaa" },
];

// Map lot area (sqft) → radius in pixels (constant across zoom levels).
// Log-scaled so the typical rowhouse and the huge institutional parcel both
// stay readable without one drowning the map.
function radiusFor(landSqft: number): number {
  if (!landSqft || landSqft <= 0) return 2;
  // 1,000 sqft → 4.5px · 10,000 → 6px · 100,000 → 7.5px · 1M → 9px
  return Math.max(2, Math.min(9, Math.log10(landSqft + 1) * 1.5));
}

export function YearBuiltMapImpl({ data }: { data: ParcelData }) {
  const [residentialOnly, setResidentialOnly] = useState<"all" | "res">("all");

  const residentialIdxs = useMemo(() => {
    const want = new Set(["single_family", "condo", "multifamily"]);
    return new Set(
      data.categories.map((c, i) => (want.has(c) ? i : -1)).filter((i) => i >= 0),
    );
  }, [data.categories]);

  const filtered = useMemo(
    () =>
      data.parcels.filter(
        ([catIdx]) => residentialOnly === "all" || residentialIdxs.has(catIdx),
      ),
    [data, residentialOnly, residentialIdxs],
  );

  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between flex-wrap gap-2">
          <div>
            <CardTitle>When DC was built</CardTitle>
            <CardDescription>
              Every parcel as a dot — radius scales with lot area, color is year built.
              {" "}{filtered.length.toLocaleString()} parcels shown.
            </CardDescription>
          </div>
          <Tabs value={residentialOnly} onValueChange={(v) => setResidentialOnly(v as "all" | "res")}>
            <TabsList>
              <TabsTrigger value="all">All uses</TabsTrigger>
              <TabsTrigger value="res">Residential only</TabsTrigger>
            </TabsList>
          </Tabs>
        </div>
      </CardHeader>
      <CardContent>
        <div className="mb-3 flex flex-wrap gap-x-5 gap-y-2 text-sm">
          {LEGEND.map((l) => (
            <div key={l.label} className="flex items-center gap-2">
              <span
                className="inline-block size-4 rounded-full"
                style={{ background: l.color }}
              />
              <span className="text-foreground">{l.label}</span>
            </div>
          ))}
        </div>

        <div className="h-[460px] w-full rounded-md overflow-hidden border">
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
            {filtered.map(([, year, area, lat, lon], i) => {
              const color = colorFor(year);
              return (
                <CircleMarker
                  key={i}
                  center={[lat, lon]}
                  radius={radiusFor(area)}
                  pathOptions={{
                    color,
                    weight: 0.3,
                    fillColor: color,
                    fillOpacity: 0.55,
                  }}
                  interactive={false}
                />
              );
            })}
          </MapContainer>
        </div>
      </CardContent>
    </Card>
  );
}
