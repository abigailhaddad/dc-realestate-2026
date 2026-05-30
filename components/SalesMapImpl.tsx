"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { MapContainer, TileLayer, Polygon, Tooltip } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import { Play, Pause } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import type { ClusterGeo } from "@/lib/types";

const YEARS = ["2020", "2021", "2022", "2023", "2024", "2025", "2026"];
type Series = "all" | "residential" | "commercial";

function fmt(n: number) {
  return new Intl.NumberFormat("en-US").format(n);
}

function clusterCount(c: ClusterGeo, year: string, series: Series) {
  return c.counts_by_year?.[year]?.[series] ?? 0;
}

function colorFor(value: number, max: number) {
  if (!max || value === 0) return "hsl(28 65% 96%)";
  const t = Math.min(1, value / max);
  const lightness = 92 - t * 60;
  return `hsl(28 70% ${lightness}%)`;
}

const FRAME_MS = 1400;

export function SalesMapImpl({ clusters }: { clusters: ClusterGeo[] }) {
  const [year, setYear] = useState<string>("2020");
  const [series, setSeries] = useState<Series>("all");
  const [playing, setPlaying] = useState(false);
  const playingRef = useRef(playing);
  playingRef.current = playing;

  // Auto-advance when playing. Stop at the last year — don't loop.
  useEffect(() => {
    if (!playing) return;
    const id = window.setInterval(() => {
      setYear((y) => {
        const i = YEARS.indexOf(y);
        if (i >= YEARS.length - 1) {
          setPlaying(false);
          return y;
        }
        return YEARS[i + 1];
      });
    }, FRAME_MS);
    return () => window.clearInterval(id);
  }, [playing]);

  // Hitting play after the animation reached the end rewinds first.
  function togglePlay() {
    if (!playing && year === YEARS[YEARS.length - 1]) {
      setYear(YEARS[0]);
    }
    setPlaying(p => !p);
  }

  // Stop the animation when the user manually picks a year.
  function pickYear(y: string) {
    setPlaying(false);
    setYear(y);
  }

  // Fix the color scale across years so 2020 doesn't look as hot as 2025.
  // Use the global max of (year × cluster) for the chosen series.
  const globalMax = useMemo(() => {
    let m = 0;
    for (const c of clusters) {
      for (const y of YEARS) {
        const v = clusterCount(c, y, series);
        if (v > m) m = v;
      }
    }
    return m;
  }, [clusters, series]);

  // ArcGIS rings are [lng, lat]; Leaflet wants [lat, lng].
  const polys = useMemo(
    () =>
      clusters.map((c) => ({
        ...c,
        value: clusterCount(c, year, series),
        leafletRings: c.rings.map((ring) => ring.map(([x, y]) => [y, x] as [number, number])),
      })),
    [clusters, year, series],
  );

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between flex-wrap">
          <div>
            <CardTitle>Sales activity by neighborhood, year by year</CardTitle>
            <CardDescription>
              Each cluster shaded by qualified-sale count for the year. The color
              scale is fixed across all years — a dark cluster in 2025 has fewer
              sales than the same shade had in 2021.
              {year === "2026" && " 2026 figures are annualized from YTD using prior-year seasonal weights."}
            </CardDescription>
          </div>
          <Tabs value={series} onValueChange={(v) => setSeries(v as Series)}>
            <TabsList>
              <TabsTrigger value="all">All</TabsTrigger>
              <TabsTrigger value="residential">Residential</TabsTrigger>
              <TabsTrigger value="commercial">Commercial</TabsTrigger>
            </TabsList>
          </Tabs>
        </div>
      </CardHeader>
      <CardContent>
        <div className="mb-3 flex items-center gap-3 flex-wrap">
          <button
            onClick={togglePlay}
            className="inline-flex size-9 items-center justify-center rounded-md border border-input bg-background hover:bg-accent"
            aria-label={playing ? "Pause" : "Play"}
          >
            {playing ? <Pause className="size-4" /> : <Play className="size-4" />}
          </button>
          <Tabs value={year} onValueChange={pickYear}>
            <TabsList>
              {YEARS.map((y) => (
                <TabsTrigger key={y} value={y}>
                  {y}
                  {y === "2026" && <span className="ml-1 text-xs text-muted-foreground">proj.</span>}
                </TabsTrigger>
              ))}
            </TabsList>
          </Tabs>
        </div>

        <div className="h-[520px] w-full rounded-md overflow-hidden border">
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
                key={`${p.cluster_num}-${year}-${series}`}
                positions={p.leafletRings}
                pathOptions={{
                  color: "#444",
                  weight: 1,
                  fillColor: colorFor(p.value, globalMax),
                  fillOpacity: 0.78,
                }}
              >
                <Tooltip sticky direction="top">
                  <div className="text-xs">
                    <div className="font-semibold">{p.cluster_name}</div>
                    <div className="text-muted-foreground">Cluster {p.cluster_num} · {year}</div>
                    <div className="mt-1">
                      {fmt(p.value)} {series === "all" ? "" : series} sales
                    </div>
                  </div>
                </Tooltip>
              </Polygon>
            ))}
          </MapContainer>
        </div>

        <div className="mt-4 flex items-center gap-3 text-sm text-foreground">
          <span>Less activity</span>
          <div
            className="h-4 flex-1 rounded"
            style={{
              background:
                "linear-gradient(to right, hsl(28 65% 96%), hsl(28 70% 80%), hsl(28 70% 60%), hsl(28 70% 35%))",
            }}
          />
          <span>More activity</span>
        </div>
      </CardContent>
    </Card>
  );
}
