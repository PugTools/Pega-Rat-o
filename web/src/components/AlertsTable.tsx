"use client";

import {
  AlertTriangle,
  ChevronLeft,
  ChevronRight,
  Filter,
  Loader2,
  Network,
  RefreshCw,
} from "lucide-react";
import Link from "next/link";
import { memo, useEffect, useMemo, useState } from "react";
import {
  api,
  type AlertCategory,
  type PaginatedAlertsResponse,
  type RiskAlert,
} from "@/lib/api";

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

const fallbackPage: PaginatedAlertsResponse = {
  items: fallbackAlerts,
  page: 1,
  limit: 25,
  total: fallbackAlerts.length,
  pages: 1,
  has_next: false,
  has_previous: false,
  categories: [
    {
      alert_type: "supplier_concentration",
      label: "Concentracao de fornecedor",
      total: 1,
    },
    {
      alert_type: "abnormal_contract_growth",
      label: "Crescimento contratual",
      total: 1,
    },
  ],
};

type AlertsTableProps = {
  onSelectEntity?: (entityType: string, entityId: string) => void;
};

export const AlertsTable = memo(function AlertsTable({ onSelectEntity }: AlertsTableProps) {
  const [data, setData] = useState<PaginatedAlertsResponse>(fallbackPage);
  const [page, setPage] = useState(1);
  const [limit, setLimit] = useState(25);
  const [alertType, setAlertType] = useState("all");
  const [severity, setSeverity] = useState("all");
  const [status, setStatus] = useState("open");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  const categories = useMemo(() => data.categories ?? [], [data.categories]);
  const visibleFrom = data.total ? (data.page - 1) * data.limit + 1 : 0;
  const visibleTo = Math.min(data.page * data.limit, data.total);

  useEffect(() => {
    let ignore = false;
    setLoading(true);
    setError(null);

    api
      .listAlertsPaginated({
        page,
        limit,
        alertType: alertType === "all" ? undefined : alertType,
        severity: severity === "all" ? undefined : severity,
        status: status === "all" ? undefined : status,
      })
      .then((payload) => {
        if (!ignore) {
          setData(payload);
        }
      })
      .catch((requestError) => {
        if (!ignore) {
          setData(fallbackPage);
          setError(
            requestError instanceof Error
              ? requestError.message
              : "Nao foi possivel carregar os alertas.",
          );
        }
      })
      .finally(() => {
        if (!ignore) {
          setLoading(false);
        }
      });

    return () => {
      ignore = true;
    };
  }, [alertType, limit, page, reloadKey, severity, status]);

  function updateAlertType(value: string) {
    setAlertType(value);
    setPage(1);
  }

  function updateSeverity(value: string) {
    setSeverity(value);
    setPage(1);
  }

  function updateStatus(value: string) {
    setStatus(value);
    setPage(1);
  }

  function updateLimit(value: number) {
    setLimit(value);
    setPage(1);
  }

  return (
    <section className="rounded-lg border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-900">
      <div className="border-b border-slate-200 px-5 py-4 dark:border-slate-800">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <div className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-amber-600" />
              <h3 className="text-base font-semibold text-slate-950 dark:text-white">
                Alertas Recentes
              </h3>
            </div>
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
              {formatNumber(visibleFrom)}-{formatNumber(visibleTo)} de{" "}
              {formatNumber(data.total)} deteccoes do motor de risco
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2 print:hidden">
            <button
              className="inline-flex items-center gap-2 rounded-md border border-slate-300 px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-60 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
              disabled={loading}
              onClick={() => setReloadKey((current) => current + 1)}
              type="button"
            >
              {loading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <RefreshCw className="h-4 w-4" />
              )}
              Atualizar
            </button>
          </div>
        </div>

        <div className="mt-4 grid gap-3 lg:grid-cols-[1fr_180px_160px_150px] print:hidden">
          <label className="relative block">
            <span className="sr-only">Categoria de alerta</span>
            <Filter className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
            <select
              className="w-full rounded-md border border-slate-300 bg-white py-2 pl-9 pr-3 text-sm text-slate-900 outline-none focus:border-slate-500 dark:border-slate-700 dark:bg-slate-950 dark:text-white"
              onChange={(event) => updateAlertType(event.target.value)}
              value={alertType}
            >
              <option value="all">Todas as categorias</option>
              {categories.map((category) => (
                <option key={category.alert_type} value={category.alert_type}>
                  {category.label} ({formatNumber(category.total)})
                </option>
              ))}
            </select>
          </label>
          <select
            className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-slate-500 dark:border-slate-700 dark:bg-slate-950 dark:text-white"
            onChange={(event) => updateSeverity(event.target.value)}
            value={severity}
          >
            <option value="all">Toda severidade</option>
            <option value="critical">Critico</option>
            <option value="high">Alto</option>
            <option value="medium">Medio</option>
            <option value="low">Baixo</option>
          </select>
          <select
            className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-slate-500 dark:border-slate-700 dark:bg-slate-950 dark:text-white"
            onChange={(event) => updateStatus(event.target.value)}
            value={status}
          >
            <option value="all">Todo status</option>
            <option value="open">Abertos</option>
            <option value="reviewing">Em analise</option>
            <option value="closed">Fechados</option>
          </select>
          <select
            className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-slate-500 dark:border-slate-700 dark:bg-slate-950 dark:text-white"
            onChange={(event) => updateLimit(Number(event.target.value))}
            value={limit}
          >
            <option value={10}>10 por pagina</option>
            <option value={25}>25 por pagina</option>
            <option value={50}>50 por pagina</option>
            <option value={100}>100 por pagina</option>
          </select>
        </div>

        <CategoryPills
          active={alertType}
          categories={categories}
          onChange={updateAlertType}
        />

        {error ? (
          <p className="mt-3 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900 dark:border-amber-900 dark:bg-amber-950/40 dark:text-amber-200">
            {error}
          </p>
        ) : null}
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-slate-200 text-sm dark:divide-slate-800">
          <thead className="bg-slate-50 dark:bg-slate-950">
            <tr>
              <th className="px-5 py-3 text-left font-semibold text-slate-600 dark:text-slate-300">
                Titulo
              </th>
              <th className="px-5 py-3 text-left font-semibold text-slate-600 dark:text-slate-300">
                Categoria
              </th>
              <th className="px-5 py-3 text-left font-semibold text-slate-600 dark:text-slate-300">
                Severidade
              </th>
              <th className="px-5 py-3 text-left font-semibold text-slate-600 dark:text-slate-300">
                Entidade
              </th>
              <th className="px-5 py-3 text-left font-semibold text-slate-600 dark:text-slate-300">
                Explicacao
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 bg-white dark:divide-slate-800 dark:bg-slate-900">
            {loading && !data.items.length ? (
              <AlertSkeletonRows />
            ) : (
              data.items.map((alert) => (
                <tr key={alert.id}>
                  <td className="px-5 py-4 font-medium text-slate-900 dark:text-slate-100">
                    {alert.title}
                  </td>
                  <td className="whitespace-nowrap px-5 py-4 text-slate-600 dark:text-slate-300">
                    {alertTypeLabel(alert.alert_type)}
                  </td>
                  <td className="whitespace-nowrap px-5 py-4">
                    <span className={severityClass(alert.severity)}>
                      {severityLabel(alert.severity)}
                    </span>
                  </td>
                  <td className="whitespace-nowrap px-5 py-4 text-slate-600 dark:text-slate-300">
                    <EntityAction alert={alert} onSelectEntity={onSelectEntity} />
                  </td>
                  <td className="max-w-xl px-5 py-4 text-slate-600 dark:text-slate-300">
                    {alert.explanation}
                  </td>
                </tr>
              ))
            )}
            {!loading && data.items.length === 0 ? (
              <tr>
                <td
                  className="px-5 py-8 text-center text-sm text-slate-500 dark:text-slate-400"
                  colSpan={5}
                >
                  Nenhum alerta encontrado para os filtros atuais.
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>

      <PaginationFooter
        data={data}
        loading={loading}
        onNext={() => setPage((current) => Math.min(current + 1, data.pages))}
        onPrevious={() => setPage((current) => Math.max(current - 1, 1))}
        visibleFrom={visibleFrom}
        visibleTo={visibleTo}
      />
    </section>
  );
});

function CategoryPills({
  active,
  categories,
  onChange,
}: {
  active: string;
  categories: AlertCategory[];
  onChange: (value: string) => void;
}) {
  if (!categories.length) {
    return null;
  }

  return (
    <div className="mt-3 flex flex-wrap gap-2 print:hidden">
      <button
        className={categoryPillClass(active === "all")}
        onClick={() => onChange("all")}
        type="button"
      >
        Todas
      </button>
      {categories.slice(0, 10).map((category) => (
        <button
          className={categoryPillClass(active === category.alert_type)}
          key={category.alert_type}
          onClick={() => onChange(category.alert_type)}
          type="button"
        >
          {category.label}: {formatNumber(category.total)}
        </button>
      ))}
    </div>
  );
}

function AlertSkeletonRows() {
  return (
    <>
      {Array.from({ length: 5 }).map((_, index) => (
        <tr className="animate-pulse" key={index}>
          <td className="px-5 py-4">
            <div className="h-4 w-48 rounded bg-slate-200 dark:bg-slate-800" />
          </td>
          <td className="px-5 py-4">
            <div className="h-4 w-32 rounded bg-slate-200 dark:bg-slate-800" />
          </td>
          <td className="px-5 py-4">
            <div className="h-6 w-20 rounded-full bg-slate-200 dark:bg-slate-800" />
          </td>
          <td className="px-5 py-4">
            <div className="h-8 w-28 rounded bg-slate-200 dark:bg-slate-800" />
          </td>
          <td className="px-5 py-4">
            <div className="h-4 w-full max-w-md rounded bg-slate-200 dark:bg-slate-800" />
          </td>
        </tr>
      ))}
    </>
  );
}

function PaginationFooter({
  data,
  loading,
  onNext,
  onPrevious,
  visibleFrom,
  visibleTo,
}: {
  data: PaginatedAlertsResponse;
  loading: boolean;
  onNext: () => void;
  onPrevious: () => void;
  visibleFrom: number;
  visibleTo: number;
}) {
  return (
    <div className="flex flex-col gap-3 border-t border-slate-200 px-5 py-4 text-sm text-slate-600 dark:border-slate-800 dark:text-slate-300 sm:flex-row sm:items-center sm:justify-between">
      <span>
        {formatNumber(visibleFrom)}-{formatNumber(visibleTo)} de {formatNumber(data.total)}
      </span>
      <div className="flex items-center gap-2">
        <button
          className="inline-flex items-center gap-2 rounded-md border border-slate-300 px-3 py-2 font-medium text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
          disabled={loading || !data.has_previous}
          onClick={onPrevious}
          type="button"
        >
          <ChevronLeft className="h-4 w-4" />
          Anterior
        </button>
        <span className="px-2 font-medium text-slate-900 dark:text-white">
          Pagina {formatNumber(data.page)} de {formatNumber(data.pages)}
        </span>
        <button
          className="inline-flex items-center gap-2 rounded-md border border-slate-300 px-3 py-2 font-medium text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
          disabled={loading || !data.has_next}
          onClick={onNext}
          type="button"
        >
          Proxima
          <ChevronRight className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}

function EntityAction({
  alert,
  onSelectEntity,
}: {
  alert: RiskAlert;
  onSelectEntity?: (entityType: string, entityId: string) => void;
}) {
  const href = entityHref(alert.entity_type, alert.entity_id);
  const label = `${entityTypeLabel(alert.entity_type)}:${shortId(alert.entity_id)}`;
  const className =
    "inline-flex items-center gap-2 rounded-md border border-slate-200 px-2.5 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800";

  if (href) {
    return (
      <Link className={className} href={href}>
        <Network className="h-3.5 w-3.5" />
        {label}
      </Link>
    );
  }

  return (
    <button
      className={className}
      onClick={() => onSelectEntity?.(alert.entity_type, alert.entity_id)}
      type="button"
    >
      <Network className="h-3.5 w-3.5" />
      {label}
    </button>
  );
}

function entityHref(entityType: string, entityId: string) {
  const normalizedType = entityType.toLowerCase();
  if (normalizedType === "person" || normalizedType === "persons" || normalizedType === "politico") {
    return `/politicos/${entityId}`;
  }
  if (normalizedType === "company" || normalizedType === "companies" || normalizedType === "empresa") {
    return `/empresas/${entityId}`;
  }
  if (normalizedType === "contract" || normalizedType === "contracts" || normalizedType === "contrato") {
    return `/contratos/${entityId}`;
  }
  return null;
}

function severityClass(severity: string) {
  switch (severity) {
    case "critical":
      return "rounded-full bg-red-50 px-2.5 py-1 text-xs font-semibold text-red-700 dark:bg-red-950/50 dark:text-red-200";
    case "high":
      return "rounded-full bg-orange-50 px-2.5 py-1 text-xs font-semibold text-orange-700 dark:bg-orange-950/50 dark:text-orange-200";
    case "medium":
      return "rounded-full bg-amber-50 px-2.5 py-1 text-xs font-semibold text-amber-700 dark:bg-amber-950/50 dark:text-amber-200";
    default:
      return "rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-700 dark:bg-slate-800 dark:text-slate-200";
  }
}

function severityLabel(severity: string) {
  const labels: Record<string, string> = {
    critical: "Critico",
    high: "Alto",
    medium: "Medio",
    low: "Baixo",
  };
  const normalized = String(severity || "").toLowerCase();
  return labels[normalized] ?? (normalized || "Risco");
}

function alertTypeLabel(alertType: string) {
  const labels: Record<string, string> = {
    expense_fragmentation: "Despesas fracionadas",
    supplier_concentration: "Concentracao de fornecedor",
    abnormal_contract_growth: "Crescimento contratual",
    abnormal_growth: "Crescimento anormal",
    incestuous_relationship: "Vinculo suspeito",
    nepotism_cross: "Nepotismo cruzado",
    donor_winner: "Doador vencedor",
    graph_risk: "Risco no grafo",
  };
  const normalized = String(alertType || "").toLowerCase();
  return labels[normalized] ?? (normalized.replaceAll("_", " ") || "Categoria");
}

function entityTypeLabel(entityType: string) {
  const labels: Record<string, string> = {
    person: "Pessoa",
    company: "Empresa",
    contract: "Contrato",
    organization: "Orgao",
  };
  const normalized = String(entityType || "").toLowerCase();
  return labels[normalized] ?? (normalized || "Entidade");
}

function categoryPillClass(active: boolean) {
  return active
    ? "rounded-full bg-slate-950 px-3 py-1 text-xs font-semibold text-white dark:bg-white dark:text-slate-950"
    : "rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-700 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700";
}

function shortId(value: string) {
  return value.length > 8 ? value.slice(0, 8) : value;
}

function formatNumber(value: number) {
  return new Intl.NumberFormat("pt-BR").format(value || 0);
}
