"use client";

import dynamic from "next/dynamic";
import { useState } from "react";
import { AlertsTable } from "@/components/AlertsTable";

type SelectedEntity = {
  entityType: string;
  entityId: string;
};

const GraphViewer = dynamic(
  () => import("@/components/GraphViewer").then((module) => module.GraphViewer),
  {
    ssr: false,
    loading: () => (
      <section className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <div className="h-4 w-40 animate-pulse rounded bg-slate-200 dark:bg-slate-700" />
        <div className="mt-4 h-64 animate-pulse rounded bg-slate-100 dark:bg-slate-800" />
      </section>
    ),
  },
);

export function DashboardIntelligence() {
  const [selectedEntity, setSelectedEntity] = useState<SelectedEntity | null>(null);

  return (
    <div className="mt-6 grid gap-6 xl:grid-cols-[minmax(0,1.15fr)_minmax(360px,0.85fr)]">
      <AlertsTable
        onSelectEntity={(entityType, entityId) =>
          setSelectedEntity({ entityType, entityId })
        }
      />

      {selectedEntity ? (
        <GraphViewer
          entityId={selectedEntity.entityId}
          entityType={selectedEntity.entityType}
        />
      ) : (
        <section className="rounded-lg border border-dashed border-slate-300 bg-white p-6 shadow-sm dark:border-slate-700 dark:bg-slate-900">
          <h3 className="text-base font-semibold text-slate-950 dark:text-white">
            Rede de Conexoes
          </h3>
          <p className="mt-2 text-sm leading-6 text-slate-500 dark:text-slate-400">
            Selecione uma entidade em um alerta para visualizar a vizinhanca no
            grafo Neo4j.
          </p>
        </section>
      )}
    </div>
  );
}
