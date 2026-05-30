"use client";

import dynamic from "next/dynamic";
import type { ClusterGeo } from "@/lib/types";

// Leaflet touches `window` at import time, so the leaflet bits have to be
// loaded client-side only.
const SalesMapImpl = dynamic(
  () => import("./SalesMapImpl").then(m => m.SalesMapImpl),
  {
    ssr: false,
    loading: () => (
      <div className="rounded-md border bg-card p-6 text-sm text-muted-foreground">
        Loading map…
      </div>
    ),
  },
);

export function SalesMap({ clusters }: { clusters: ClusterGeo[] }) {
  return <SalesMapImpl clusters={clusters} />;
}
