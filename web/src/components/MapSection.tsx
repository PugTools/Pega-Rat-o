"use client";

import dynamic from "next/dynamic";

const NationalMap = dynamic(
  () => import("@/components/NationalMap").then((mod) => mod.NationalMap),
  {
    ssr: false,
    loading: () => (
      <section className="mt-6 rounded-lg border border-slate-200 bg-white p-6 text-sm text-slate-500 shadow-sm">
        Carregando mapa nacional...
      </section>
    ),
  },
);

export function MapSection() {
  return <NationalMap />;
}
