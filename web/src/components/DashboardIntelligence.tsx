"use client";

import { useState } from "react";
import { AlertsTable } from "@/components/AlertsTable";
import { GraphViewer } from "@/components/GraphViewer";

type SelectedEntity = {
  entityType: string;
  entityId: string;
};

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
        <section className="rounded-lg border border-dashed border-slate-300 bg-white p-6 shadow-sm">
          <h3 className="text-base font-semibold text-slate-950">
            Rede de Conexoes
          </h3>
          <p className="mt-2 text-sm leading-6 text-slate-500">
            Selecione uma entidade em um alerta para visualizar a vizinhanca no
            grafo Neo4j.
          </p>
        </section>
      )}
    </div>
  );
}
