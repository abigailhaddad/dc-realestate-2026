"use client";

import dynamic from "next/dynamic";

const Impl = dynamic(() => import("./TaxExemptMapImpl").then(m => m.TaxExemptMapImpl), {
  ssr: false,
  loading: () => <div className="rounded-md border bg-card p-6 text-sm text-muted-foreground">Loading map…</div>,
});

type ClusterRow = {
  cluster_num: number;
  cluster_name: string;
  rings: number[][][];
  parcels: number;
  assessed_total: number;
  assessed_exempt: number;
  exempt_share: number;
};

export function TaxExemptMap({ clusters }: { clusters: ClusterRow[] }) {
  return <Impl clusters={clusters} />;
}
