"use client";

import { useMemo, useState } from "react";
import { MapContainer, TileLayer, CircleMarker } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";

type ParcelData = {
  categories: string[];
  // [cat_idx, year_built, land_area_sqft, lat, lon]
  parcels: [number, number | null, number, number, number][];
};

// Bin the 11 fine-grained use codes into 5 broad bins that read clearly on a city-zoom map.
const BIN_OF: Record<string, string> = {
  single_family: "residential",
  condo: "residential",
  multifamily: "residential",
  office: "commercial",
  retail: "commercial",
  hotel_lodging: "commercial",
  industrial: "commercial",
  commercial_other: "commercial",
  institutional: "institutional",
  vacant: "vacant",
  other: "other",
};

const BIN_COLOR: Record<string, string> = {
  residential: "#5a9bd4",     // blue
  commercial: "#e89240",       // orange
  institutional: "#4a8a5a",    // green
  vacant: "#999999",           // grey
  other: "#cc6a99",            // pink/magenta
};

const BIN_LABEL: Record<string, string> = {
  residential: "Residential",
  commercial: "Commercial",
  institutional: "Institutional",
  vacant: "Vacant",
  other: "Other",
};

const BIN_ORDER = ["residential", "commercial", "institutional", "vacant", "other"];

function radiusFor(landSqft: number): number {
  if (!landSqft || landSqft <= 0) return 2;
  // Log-scaled so the typical rowhouse and the huge institutional parcel both
  // stay readable without one drowning the map.
  // 1,000 sqft → 4.5px · 10,000 → 6px · 100,000 → 7.5px · 1M → 9px
  return Math.max(2, Math.min(9, Math.log10(landSqft + 1) * 1.5));
}

export function ParcelCategoryMapImpl({ data }: { data: ParcelData }) {
  const [hidden, setHidden] = useState<Set<string>>(new Set());

  // Build [bin, area, lat, lon] tuples, ordered so residential renders first
  // and the smaller (but more interesting) categories paint on top.
  const dots = useMemo(() => {
    const renderOrder = { residential: 0, vacant: 1, other: 2, commercial: 3, institutional: 4 };
    return data.parcels
      .map(([catIdx, , area, lat, lon]) => {
        const cat = data.categories[catIdx] || "other";
        return { bin: BIN_OF[cat] || "other", area, lat, lon };
      })
      .sort((a, b) => (renderOrder[a.bin as keyof typeof renderOrder] ?? 5)
                    - (renderOrder[b.bin as keyof typeof renderOrder] ?? 5));
  }, [data]);

  const visible = dots.filter((d) => !hidden.has(d.bin));

  function toggle(bin: string) {
    setHidden((prev) => {
      const next = new Set(prev);
      if (next.has(bin)) next.delete(bin);
      else next.add(bin);
      return next;
    });
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>What DC is made of, mapped</CardTitle>
        <CardDescription>
          Every parcel as a dot — radius scales with lot area, color is its use
          category. The 11 raw use codes are binned into five buckets so the
          city-scale view is legible. Click a legend chip to hide that bin.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="mb-3 flex flex-wrap gap-x-3 gap-y-2 text-sm">
          {BIN_ORDER.map((bin) => {
            const off = hidden.has(bin);
            return (
              <button
                key={bin}
                onClick={() => toggle(bin)}
                className="flex items-center gap-2 px-2 py-1 rounded border border-input hover:bg-accent transition-opacity"
                style={{ opacity: off ? 0.35 : 1 }}
                aria-pressed={!off}
              >
                <span
                  className="inline-block size-4 rounded-full"
                  style={{ background: BIN_COLOR[bin] }}
                />
                <span className="text-foreground">{BIN_LABEL[bin]}</span>
              </button>
            );
          })}
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
            {visible.map((d, i) => {
              const color = BIN_COLOR[d.bin];
              return (
                <CircleMarker
                  key={i}
                  center={[d.lat, d.lon]}
                  radius={radiusFor(d.area)}
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
