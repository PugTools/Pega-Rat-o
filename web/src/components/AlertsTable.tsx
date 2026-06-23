"use client";

import { AlertTriangle, Network } from "lucide-react";
import { memo, useEffect, useMemo, useState } from "react";
import { api, type RiskAlert } from "@/lib/api";

const fallbackAlerts: RiskAlert[] = [
  {
    id: "demo-alert-1",
    entity_type: "company",
    entity_id: "demo-company",
    alert_type: "supplier_concentration",
    severity: "critical",
    score: "92.000",
    title: "Concentracao elevada em fornecedor",
    explanation:
      "Fornecedor concentra parcela relevante dos pagamentos analisados do orgao.",
    evidence: {},
    status: "open",
    created_at: new Date().toISOString(),
  },
  {
    id: "demo-alert-2",
    entity_type: "contract",
    entity_id: "demo-contract",
    alert_type: "abnormal_contract_growth",
    severity: "high",
    score: "78.000",
    title: "Crescimento anormal de valor contratual",
    explanation:
      "Contrato apresenta valor acima da media historica de contratos comparaveis.",
    evidence: {},
    status: "open",
    created_at: new Date().toISOString(),
  },
];

type AlertsTableProps = {
  onSelectEntity?: (entityType: string, entityId: string) => void;
};

export const AlertsTable = memo(function AlertsTable({ onSelectEntity }: AlertsTableProps) {
  const [alerts, setAlerts] = useState<RiskAlert[]>([]);
  const [loading, setLoading] = useState(true);
  const visibleAlerts = useMemo(
    () =>
      [...alerts].sort(
        (a, b) => severityWeight(b.severity) - severityWeight(a.severity),
      ),
    [alerts],
  );

  useEffect(() => {
    let mounted = true;

    api
      .listAlerts(25)
      .then((items) => {
        if (mounted) {
          setAlerts(items.length ? items : fallbackAlerts);
        }
      })
      .catch(() => {
        if (mounted) {
          setAlerts(fallbackAlerts);
        }
      })
      .finally(() => {
        if (mounted) {
          setLoading(false);
        }
      });

    return () => {
      mounted = false;
    };
  }, []);

  return (
    <section className="rounded-lg border border-slate-200 bg-white shadow-sm">
      <div className="flex items-center justify-between border-b border-slate-200 px-5 py-4">
        <div>
          <h3 className="text-base font-semibold text-slate-950">
            Alertas Recentes
          </h3>
          <p className="mt-1 text-sm text-slate-500">
            Deteccoes produzidas pelo motor de regras
          </p>
        </div>
        <AlertTriangle className="h-5 w-5 text-amber-600" />
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-slate-200 text-sm">
          <thead className="bg-slate-50">
            <tr>
              <th className="px-5 py-3 text-left font-semibold text-slate-600">
                Titulo
              </th>
              <th className="px-5 py-3 text-left font-semibold text-slate-600">
                Severidade
              </th>
              <th className="px-5 py-3 text-left font-semibold text-slate-600">
                Entidade
              </th>
              <th className="px-5 py-3 text-left font-semibold text-slate-600">
                Explicacao
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 bg-white">
            {loading ? (
              <AlertSkeletonRows />
            ) : (
              visibleAlerts.map((alert) => (
                <tr key={alert.id}>
                  <td className="px-5 py-4 font-medium text-slate-900">
                    {alert.title}
                  </td>
                  <td className="whitespace-nowrap px-5 py-4">
                    <span className={severityClass(alert.severity)}>
                      {severityLabel(alert.severity)}
                    </span>
                  </td>
                  <td className="whitespace-nowrap px-5 py-4 text-slate-600">
                    <button
                      className="inline-flex items-center gap-2 rounded-md border border-slate-200 px-2.5 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
                      onClick={() =>
                        onSelectEntity?.(alert.entity_type, alert.entity_id)
                      }
                      type="button"
                    >
                      <Network className="h-3.5 w-3.5" />
                      {alert.entity_type}:{shortId(alert.entity_id)}
                    </button>
                  </td>
                  <td className="max-w-xl px-5 py-4 text-slate-600">
                    {alert.explanation}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
});

function AlertSkeletonRows() {
  return (
    <>
      {Array.from({ length: 4 }).map((_, index) => (
        <tr className="animate-pulse" key={index}>
          <td className="px-5 py-4">
            <div className="h-4 w-48 rounded bg-slate-200" />
          </td>
          <td className="px-5 py-4">
            <div className="h-6 w-20 rounded-full bg-slate-200" />
          </td>
          <td className="px-5 py-4">
            <div className="h-8 w-28 rounded bg-slate-200" />
          </td>
          <td className="px-5 py-4">
            <div className="h-4 w-full max-w-md rounded bg-slate-200" />
          </td>
        </tr>
      ))}
    </>
  );
}

function severityWeight(severity: string) {
  const weights: Record<string, number> = {
    critical: 4,
    high: 3,
    medium: 2,
    low: 1,
  };
  return weights[severity] ?? 0;
}

function severityClass(severity: string) {
  switch (severity) {
    case "critical":
      return "rounded-full bg-red-50 px-2.5 py-1 text-xs font-semibold text-red-700";
    case "high":
      return "rounded-full bg-orange-50 px-2.5 py-1 text-xs font-semibold text-orange-700";
    case "medium":
      return "rounded-full bg-amber-50 px-2.5 py-1 text-xs font-semibold text-amber-700";
    default:
      return "rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-700";
  }
}

function severityLabel(severity: string) {
  const labels: Record<string, string> = {
    critical: "Critico",
    high: "Alto",
    medium: "Medio",
    low: "Baixo",
  };
  return labels[severity] ?? severity;
}

function shortId(value: string) {
  return value.length > 8 ? value.slice(0, 8) : value;
}
