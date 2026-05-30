"use client";

import dynamic from "next/dynamic";

const Impl = dynamic(() => import("./ParcelCategoryMapImpl").then(m => m.ParcelCategoryMapImpl), {
  ssr: false,
  loading: () => (
    <div className="rounded-md border bg-card p-6 text-sm text-muted-foreground">
      Loading parcel map…
    </div>
  ),
});

type ParcelData = {
  categories: string[];
  parcels: [number, number | null, number, number, number][];
};

export function ParcelCategoryMap({ data }: { data: ParcelData }) {
  return <Impl data={data} />;
}
