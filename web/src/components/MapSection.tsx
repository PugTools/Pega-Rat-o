"use client";

import dynamic from "next/dynamic";

const NationalMap = dynamic(
  () => import("@/components/NationalMap").then((mod) => mod.NationalMap),
  {
    ssr: false,
    loading: () => (
      <div className="flex h-[420px] items-center justify-center rounded-lg border border-slate-200 bg-slate-50 text-sm text-slate-500 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-400">
        Carregando mapa nacional...
      </div>
    ),
  },
);

export function MapSection() {
  return <NationalMap />;
}
