"use client";

import {
  Building2,
  ChevronLeft,
  ChevronRight,
  FileText,
  Loader2,
  Search,
  WalletCards,
} from "lucide-react";
import Link from "next/link";
import { memo, useEffect, useMemo, useRef, useState } from "react";
import { PrintReportButton } from "@/components/PrintReportButton";
import {
  api,
  type Contract,
  type PaginatedContractsResponse,
} from "@/lib/api";
import { MetricTile, StatusCallout } from "@/components/ui/Primitives";

type ContractsExplorerProps = {
  initialPage: PaginatedContractsResponse;
  isFallback?: boolean;
};

export const ContractsExplorer = memo(function ContractsExplorer({
  initialPage,
  isFallback = false,
}: ContractsExplorerProps) {
  const [data, setData] = useState<PaginatedContractsResponse>(initialPage);
  const [query, setQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [status, setStatus] = useState("Todos");
  const [page, setPage] = useState(initialPage.page || 1);
  const [limit, setLimit] = useState(initialPage.limit || 50);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const firstFetch = useRef(true);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setDebouncedQuery(query.trim());
      setPage(1);
    }, 350);

    return () => window.clearTimeout(timer);
  }, [query]);

  useEffect(() => {
    if (firstFetch.current) {
      firstFetch.current = false;
      if (!isFallback) {
        return;
      }
    }

    let ignore = false;
    setLoading(true);
    setError(null);

    api
      .listContractsPaginated({
        page,
        limit,
        q: debouncedQuery || undefined,
        status: status === "Todos" ? undefined : status,
      })
      .then((payload) => {
        if (!ignore) {
          setData(payload);
        }
      })
      .catch((requestError) => {
        if (!ignore) {
          setError(
            requestError instanceof Error
              ? requestError.message
              : "Nao foi possivel carregar os contratos.",
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
  }, [debouncedQuery, isFallback, limit, page, status]);

  const statuses = useMemo(() => data.statuses ?? [], [data.statuses]);
  const contracts = data.items ?? [];
  const visibleFrom = data.total ? (data.page - 1) * data.limit + 1 : 0;
  const visibleTo = Math.min(data.page * data.limit, data.total);

  function updateStatus(value: string) {
    setStatus(value);
    setPage(1);
  }

  function updateLimit(value: number) {
    setLimit(value);
    setPage(1);
  }

  return (
    <section>
      <div className="mb-6 grid gap-4 md:grid-cols-3">
        <MetricTile
          detail="registros encontrados no filtro atual"
          icon={FileText}
          label="Contratos"
          value={formatNumber(data.total)}
        />
        <MetricTile
          detail={`${formatNumber(visibleFrom)}-${formatNumber(visibleTo)} nesta pagina`}
          icon={Building2}
          label="Pagina atual"
          value={`${formatNumber(data.page)} / ${formatNumber(data.pages)}`}
        />
        <MetricTile
          detail="soma estimada dos contratos filtrados"
          icon={WalletCards}
          label="Valor filtrado"
          tone="success"
          value={currency(data.total_value)}
        />
      </div>

      {isFallback ? (
        <div className="mb-4">
          <StatusCallout
            message="A API nao respondeu ou ainda nao ha contratos reais carregados. A tela esta usando uma amostra demonstrativa para preservar a navegacao."
            title="Dados demonstrativos"
            tone="warning"
          />
        </div>
      ) : null}

      <div className="mb-4 rounded-lg border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-950 print:hidden">
        <div className="grid gap-3 lg:grid-cols-[minmax(220px,1fr)_220px_150px_auto]">
          <label className="relative block">
            <span className="sr-only">Buscar contrato</span>
            <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
            <input
              className="w-full rounded-md border border-slate-300 bg-white py-2 pl-9 pr-3 text-sm text-slate-900 outline-none focus:border-slate-500 dark:border-slate-700 dark:bg-slate-900 dark:text-white"
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Contrato, processo ou objeto"
              value={query}
            />
          </label>
          <select
            className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-slate-500 dark:border-slate-700 dark:bg-slate-900 dark:text-white"
            onChange={(event) => updateStatus(event.target.value)}
            value={status}
          >
            <option>Todos</option>
            {statuses.map((item) => (
              <option key={item.status} value={item.status}>
                {item.label} ({formatNumber(item.total)})
              </option>
            ))}
          </select>
          <select
            className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-slate-500 dark:border-slate-700 dark:bg-slate-900 dark:text-white"
            onChange={(event) => updateLimit(Number(event.target.value))}
            value={limit}
          >
            <option value={25}>25 por pagina</option>
            <option value={50}>50 por pagina</option>
            <option value={100}>100 por pagina</option>
          </select>
          <PrintReportButton />
        </div>
      </div>

      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h3 className="text-base font-semibold text-slate-950 dark:text-white">
            Contratos monitorados
          </h3>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            Mostrando {formatNumber(visibleFrom)} a {formatNumber(visibleTo)} de{" "}
            {formatNumber(data.total)} contratos.
          </p>
        </div>
        <div className="flex items-center gap-2 text-sm text-slate-500 dark:text-slate-400">
          {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileText className="h-5 w-5" />}
          {loading ? "Carregando contratos..." : "Clique para abrir o relatorio individual"}
        </div>
      </div>

      {error ? (
        <div className="mb-4">
          <StatusCallout message={error} title="Falha ao carregar contratos" tone="danger" />
        </div>
      ) : null}

      <div
        aria-busy={loading}
        className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-950"
      >
        <div className="overflow-x-auto">
          <table className="w-full min-w-[980px] text-left text-sm">
            <thead className="bg-slate-50 text-xs uppercase text-slate-500 dark:bg-slate-900 dark:text-slate-400">
              <tr>
                <th className="px-4 py-3">Contrato</th>
                <th className="px-4 py-3">Objeto</th>
                <th className="px-4 py-3">Fornecedor</th>
                <th className="px-4 py-3">Orgao</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Valor</th>
                <th className="px-4 py-3 print:hidden">Acao</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {loading && !contracts.length ? <LoadingRows /> : null}
              {contracts.map((contract) => (
                <ContractRow contract={contract} key={contract.id} />
              ))}
              {!loading && contracts.length === 0 ? (
                <tr>
                  <td className="px-4 py-8 text-center text-sm text-slate-500 dark:text-slate-400" colSpan={7}>
                    Nenhum contrato encontrado para este filtro. Ajuste a busca ou rode a ingestao no Admin.
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
      </div>
    </section>
  );
});

function ContractRow({ contract }: { contract: Contract }) {
  return (
    <tr className="hover:bg-slate-50 dark:hover:bg-slate-900">
      <td className="px-4 py-3 font-medium text-slate-950 dark:text-white">
        {contract.contract_number ?? contract.process_number ?? "Sem numero"}
      </td>
      <td className="max-w-sm px-4 py-3 text-slate-600 dark:text-slate-300">
        <span className="line-clamp-2">{contract.object ?? "Nao informado"}</span>
      </td>
      <td className="px-4 py-3 text-slate-600 dark:text-slate-300">
        {contract.supplier?.legal_name ?? "-"}
      </td>
      <td className="px-4 py-3 text-slate-600 dark:text-slate-300">
        {contract.organization?.name ?? "-"}
      </td>
      <td className="px-4 py-3 text-slate-600 dark:text-slate-300">
        {contract.status ?? "-"}
      </td>
      <td className="px-4 py-3 font-semibold text-slate-950 dark:text-white">
        {currency(contract.total_value)}
      </td>
      <td className="px-4 py-3 print:hidden">
        <Link
          className="rounded-md border border-slate-300 px-3 py-2 text-xs font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
          href={`/contratos/${contract.id}`}
        >
          Abrir relatorio
        </Link>
      </td>
    </tr>
  );
}

function LoadingRows() {
  return (
    <>
      {Array.from({ length: 8 }).map((_, index) => (
        <tr key={index}>
          <td className="px-4 py-3" colSpan={7}>
            <div className="h-10 animate-pulse rounded-md bg-slate-100 dark:bg-slate-900" />
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
  data: PaginatedContractsResponse;
  loading: boolean;
  onNext: () => void;
  onPrevious: () => void;
  visibleFrom: number;
  visibleTo: number;
}) {
  return (
    <div className="flex flex-col gap-3 border-t border-slate-200 px-4 py-3 text-sm text-slate-600 dark:border-slate-800 dark:text-slate-300 sm:flex-row sm:items-center sm:justify-between">
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

function currency(value: string | number | null | undefined) {
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
    maximumFractionDigits: 0,
  }).format(Number(value ?? 0));
}

function formatNumber(value: number) {
  return new Intl.NumberFormat("pt-BR").format(value || 0);
}
