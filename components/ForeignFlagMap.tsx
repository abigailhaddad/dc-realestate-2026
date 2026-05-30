"use client";

import dynamic from "next/dynamic";

const Impl = dynamic(() => import("./ForeignFlagMapImpl").then(m => m.ForeignFlagMapImpl), {
  ssr: false,
  loading: () => (
    <div className="rounded-md border bg-card p-6 text-sm text-muted-foreground">
      Loading flag map…
    </div>
  ),
});

type ForeignParcel = {
  owner: string;
  lat: number;
  lon: number;
  assessed: number;
  address: string;
};

export function ForeignFlagMap({ parcels }: { parcels: ForeignParcel[] }) {
  return <Impl parcels={parcels} />;
}
