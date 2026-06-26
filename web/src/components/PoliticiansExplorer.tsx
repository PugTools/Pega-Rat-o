"use client";

import {
  ChevronLeft,
  ChevronRight,
  FileText,
  Loader2,
  Search,
  SlidersHorizontal,
  Users,
} from "lucide-react";
import Link from "next/link";
import { memo, useEffect, useMemo, useRef, useState } from "react";
import { PrintReportButton } from "@/components/PrintReportButton";
import { api, type PaginatedPersonsResponse, type Person } from "@/lib/api";

const roleOptions = [
  "Todos",
  "Presidente",
  "Vice-presidente",
  "Ministro",
  "Senador",
  "Deputado Federal",
  "Deputado Estadual",
  "Governador",
  "Prefeito",
  "Vereador",
  "Secretario",
  "Assessor",
];

const stateOptions = [
  "Todos",
  "AC",
  "AL",
  "AP",
  "AM",
  "BA",
  "CE",
  "DF",
  "ES",
  "GO",
  "MA",
  "MT",
  "MS",
  "MG",
  "PA",
  "PB",
  "PR",
  "PE",
  "PI",
  "RJ",
  "RN",
  "RS",
  "RO",
  "RR",
  "SC",
  "SP",
  "SE",
  "TO",
];

type PoliticiansExplorerProps = {
  initialPage: PaginatedPersonsResponse;
  isFallback?: boolean;
};

export const PoliticiansExplorer = memo(function PoliticiansExplorer({
  initialPage,
  isFallback = false,
}: PoliticiansExplorerProps) {
  const [data, setData] = useState<PaginatedPersonsResponse>(initialPage);
  const [query, setQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [role, setRole] = useState("Todos");
  const [stateCode, setStateCode] = useState("Todos");
  const [orderBy, setOrderBy] = useState<"expense_total" | "name" | "party" | "state">("name");
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
      .listPersonsPaginated({
        page,
        limit,
        name: debouncedQuery || undefined,
        roleName: role === "Todos" ? undefined : role,
        stateCode: stateCode === "Todos" ? undefined : stateCode,
        orderBy,
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
              : "Nao foi possivel carregar a lista paginada.",
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
  }, [debouncedQuery, isFallback, limit, orderBy, page, role, stateCode]);

  const persons = data.items ?? [];
  const visibleFrom = data.total ? (data.page - 1) * data.limit + 1 : 0;
  const visibleTo = Math.min(data.page * data.limit, data.total);

  const activeFilterText = useMemo(() => {
    const filters = [
      debouncedQuery ? `busca "${debouncedQuery}"` : null,
      role !== "Todos" ? `cargo ${role}` : null,
      stateCode !== "Todos" ? `UF ${stateCode}` : null,
    ].filter(Boolean);
    return filters.length ? filters.join(" / ") : "sem filtros ativos";
  }, [debouncedQuery, role, stateCode]);

  function updateRole(value: string) {
    setRole(value);
    setPage(1);
  }

  function updateState(value: string) {
    setStateCode(value);
    setPage(1);
  }

  function updateOrder(value: "expense_total" | "name" | "party" | "state") {
    setOrderBy(value);
    setPage(1);
  }

  function updateLimit(value: number) {
    setLimit(value);
    setPage(1);
  }

  return (
    <section>
      <div className="mb-6 grid gap-4 md:grid-cols-3">
        <Metric label="Registros encontrados" value={formatNumber(data.total)} />
        <Metric label="Pagina atual" value={`${formatNumber(visibleFrom)}-${formatNumber(visibleTo)}`} />
        <Metric label="Total de paginas" value={formatNumber(data.pages)} />
      </div>

      <div className="mb-4 rounded-lg border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-950 print:hidden">
        <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-700 dark:text-slate-200">
          <SlidersHorizontal className="h-4 w-4" />
          Filtros paginados no servidor
        </div>
        <div className="grid gap-3 xl:grid-cols-[minmax(240px,1fr)_210px_130px_180px_130px_auto]">
          <label className="relative block">
            <span className="sr-only">Buscar politico</span>
            <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
            <input
              className="w-full rounded-md border border-slate-300 bg-white py-2 pl-9 pr-3 text-sm text-slate-900 outline-none focus:border-slate-500 dark:border-slate-700 dark:bg-slate-900 dark:text-white"
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Buscar por nome"
              value={query}
            />
          </label>
          <select
            className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-slate-500 dark:border-slate-700 dark:bg-slate-900 dark:text-white"
            onChange={(event) => updateRole(event.target.value)}
            value={role}
          >
            {roleOptions.map((item) => (
              <option key={item}>{item}</option>
            ))}
          </select>
          <select
            className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-slate-500 dark:border-slate-700 dark:bg-slate-900 dark:text-white"
            onChange={(event) => updateState(event.target.value)}
            value={stateCode}
          >
            {stateOptions.map((item) => (
              <option key={item}>{item}</option>
            ))}
          </select>
          <select
            className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-slate-500 dark:border-slate-700 dark:bg-slate-900 dark:text-white"
            onChange={(event) =>
              updateOrder(event.target.value as "expense_total" | "name" | "party" | "state")
            }
            value={orderBy}
          >
            <option value="name">Nome</option>
            <option value="expense_total">Maior gasto</option>
            <option value="party">Partido</option>
            <option value="state">UF</option>
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

        <div className="mt-3 flex flex-wrap gap-2">
          {roleOptions.slice(1).map((roleName) => (
            <button
              className={`rounded-full px-3 py-1 text-xs font-medium transition ${
                role === roleName
                  ? "bg-slate-950 text-white dark:bg-white dark:text-slate-950"
                  : "bg-slate-100 text-slate-700 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
              }`}
              key={roleName}
              onClick={() => updateRole(roleName)}
              type="button"
            >
              {roleName}
            </button>
          ))}
        </div>
      </div>

      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h3 className="text-base font-semibold text-slate-950 dark:text-white">
            Lista de agentes publicos
          </h3>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            {isFallback
              ? "Amostra demonstrativa enquanto a API nao respondeu."
              : `Mostrando ${formatNumber(visibleFrom)} a ${formatNumber(visibleTo)} de ${formatNumber(data.total)} registros, ${activeFilterText}.`}
          </p>
        </div>
        <div className="flex items-center gap-2 text-sm text-slate-500 dark:text-slate-400">
          {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileText className="h-5 w-5" />}
          {loading ? "Carregando pagina..." : "Clique para abrir o relatorio individual"}
        </div>
      </div>

      {error ? (
        <div className="mb-4 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900 dark:border-amber-900 dark:bg-amber-950/30 dark:text-amber-200">
          {error}
        </div>
      ) : null}

      <div
        aria-busy={loading}
        className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-950"
      >
        <div className="overflow-x-auto">
          <table className="w-full min-w-[1040px] text-left text-sm">
            <thead className="bg-slate-50 text-xs uppercase text-slate-500 dark:bg-slate-900 dark:text-slate-400">
              <tr>
                <th className="px-4 py-3">Nome</th>
                <th className="px-4 py-3">Cargo</th>
                <th className="px-4 py-3">Partido</th>
                <th className="px-4 py-3">UF</th>
                <th className="px-4 py-3">Patrimonio</th>
                <th className="px-4 py-3">Razao</th>
                <th className="px-4 py-3">Fonte</th>
                <th className="px-4 py-3 print:hidden">Acao</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {loading && !persons.length ? <LoadingRows /> : null}
              {persons.map((person) => (
                <PersonRow key={person.id} person={person} />
              ))}
              {!loading && persons.length === 0 ? (
                <tr>
                  <td className="px-4 py-8 text-center text-sm text-slate-500 dark:text-slate-400" colSpan={8}>
                    Nenhum agente encontrado para este filtro. Ajuste a busca ou rode a ingestao no Admin.
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

function PersonRow({ person }: { person: Person }) {
  return (
    <tr className="hover:bg-slate-50 dark:hover:bg-slate-900">
      <td className="px-4 py-3">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 overflow-hidden rounded-md bg-slate-100 dark:bg-slate-800">
            {person.photo_url ? (
              <img alt="" className="h-full w-full object-cover" src={person.photo_url} />
            ) : (
              <div className="flex h-full w-full items-center justify-center text-sm font-semibold text-slate-500 dark:text-slate-300">
                {person.full_name.slice(0, 1)}
              </div>
            )}
          </div>
          <span className="font-medium text-slate-950 dark:text-white">{person.full_name}</span>
        </div>
      </td>
      <td className="px-4 py-3 text-slate-600 dark:text-slate-300">{rolesLabel(person)}</td>
      <td className="px-4 py-3 text-slate-600 dark:text-slate-300">{person.party_acronym ?? "-"}</td>
      <td className="px-4 py-3 text-slate-600 dark:text-slate-300">{person.state_code ?? "-"}</td>
      <td className="px-4 py-3 font-medium text-slate-950 dark:text-white">
        {currency(person.declared_assets_value)}
      </td>
      <td className="px-4 py-3 text-slate-600 dark:text-slate-300">
        {ratioLabel(person.asset_salary_ratio)}
      </td>
      <td className="px-4 py-3 text-slate-600 dark:text-slate-300">{person.data_origin ?? "-"}</td>
      <td className="px-4 py-3 print:hidden">
        <Link
          className="rounded-md border border-slate-300 px-3 py-2 text-xs font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
          href={`/politicos/${person.id}`}
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
          <td className="px-4 py-3" colSpan={8}>
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
  data: PaginatedPersonsResponse;
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

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-950">
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium text-slate-500 dark:text-slate-400">{label}</p>
        <Users className="h-5 w-5 text-emerald-700" />
      </div>
      <p className="mt-3 text-2xl font-semibold text-slate-950 dark:text-white">{value}</p>
    </div>
  );
}

function rolesLabel(person: Person) {
  const roles = person.roles ?? [];
  if (!roles.length) {
    return "Sem cargo informado";
  }
  return roles.map((item) => item.role_name).join(", ");
}

function currency(value: string | number | null | undefined) {
  const numericValue = Number(value ?? 0);
  if (!numericValue) {
    return "-";
  }
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
    maximumFractionDigits: 0,
  }).format(numericValue);
}

function ratioLabel(value: string | number | null | undefined) {
  const ratio = Number(value ?? 0);
  if (!ratio) {
    return "-";
  }
  return `${ratio.toLocaleString("pt-BR", { maximumFractionDigits: 1 })} anos`;
}

function formatNumber(value: number) {
  return new Intl.NumberFormat("pt-BR").format(value || 0);
}
