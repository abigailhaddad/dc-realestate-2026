"use client";

import dynamic from "next/dynamic";

const Impl = dynamic(() => import("./YearBuiltMapImpl").then(m => m.YearBuiltMapImpl), {
  ssr: false,
  loading: () => <div className="rounded-md border bg-card p-6 text-sm text-muted-foreground">Loading map…</div>,
});

type ParcelData = {
  categories: string[];
  parcels: [number, number | null, number, number, number][];
};

export function YearBuiltMap({ data }: { data: ParcelData }) {
  return <Impl data={data} />;
}
