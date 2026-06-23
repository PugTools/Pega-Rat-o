"use client";

import { Building2, FileText, Search } from "lucide-react";
import Link from "next/link";
import { memo, useMemo, useState } from "react";
import type { Contract } from "@/lib/api";
import { PrintReportButton } from "@/components/PrintReportButton";

type ContractsExplorerProps = {
  contracts: Contract[];
  isFallback?: boolean;
};

export const ContractsExplorer = memo(function ContractsExplorer({
  contracts,
  isFallback = false,
}: ContractsExplorerProps) {
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("Todos");

  const statuses = useMemo(
    () =>
      Array.from(
        new Set(contracts.map((contract) => contract.status).filter(Boolean) as string[]),
      ).sort(),
    [contracts],
  );

  const filtered = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    return contracts.filter((contract) => {
      const matchesQuery =
        !normalizedQuery ||
        (contract.contract_number ?? "").toLowerCase().includes(normalizedQuery) ||
        (contract.process_number ?? "").toLowerCase().includes(normalizedQuery) ||
        (contract.object ?? "").toLowerCase().includes(normalizedQuery) ||
        (contract.supplier?.legal_name ?? "").toLowerCase().includes(normalizedQuery) ||
        (contract.organization?.name ?? "").toLowerCase().includes(normalizedQuery);
      const matchesStatus = status === "Todos" || contract.status === status;
      return matchesQuery && matchesStatus;
    });
  }, [contracts, query, status]);

  const totalValue = filtered.reduce(
    (sum, contract) => sum + Number(contract.total_value ?? 0),
    0,
  );

  return (
    <section>
      <div className="mb-6 grid gap-4 md:grid-cols-3">
        <Metric label="Contratos" value={String(contracts.length)} />
        <Metric label="No filtro atual" value={String(filtered.length)} />
        <Metric label="Valor filtrado" value={currency(totalValue)} />
      </div>

      <div className="mb-4 rounded-lg border border-slate-200 bg-white p-4 shadow-sm print:hidden">
        <div className="grid gap-3 lg:grid-cols-[minmax(220px,1fr)_220px_auto]">
          <label className="relative block">
            <span className="sr-only">Buscar contrato</span>
            <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
            <input
              className="w-full rounded-md border border-slate-300 py-2 pl-9 pr-3 text-sm outline-none focus:border-slate-500"
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Buscar por contrato, objeto, orgao ou fornecedor"
              value={query}
            />
          </label>
          <select
            className="rounded-md border border-slate-300 px-3 py-2 text-sm outline-none focus:border-slate-500"
            onChange={(event) => setStatus(event.target.value)}
            value={status}
          >
            <option>Todos</option>
            {statuses.map((item) => (
              <option key={item}>{item}</option>
            ))}
          </select>
          <PrintReportButton />
        </div>
      </div>

      <div className="mb-4 flex items-center justify-between">
        <div>
          <h3 className="text-base font-semibold text-slate-950">
            Contratos monitorados
          </h3>
          <p className="mt-1 text-sm text-slate-500">
            {isFallback
              ? "Amostra demonstrativa enquanto a base real esta vazia."
              : "Clique em um contrato para abrir o relatorio individual."}
          </p>
        </div>
        <FileText className="h-5 w-5 text-slate-400" />
      </div>

      <div className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
        <div className="overflow-x-auto">
          <table className="min-w-[980px] w-full text-left text-sm">
            <thead className="bg-slate-50 text-xs uppercase text-slate-500">
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
            <tbody className="divide-y divide-slate-100">
              {filtered.map((contract) => (
                <tr className="hover:bg-slate-50" key={contract.id}>
                  <td className="px-4 py-3 font-medium text-slate-950">
                    {contract.contract_number ?? contract.process_number ?? "Sem numero"}
                  </td>
                  <td className="max-w-sm px-4 py-3 text-slate-600">
                    <span className="line-clamp-2">{contract.object ?? "Nao informado"}</span>
                  </td>
                  <td className="px-4 py-3 text-slate-600">
                    {contract.supplier?.legal_name ?? "-"}
                  </td>
                  <td className="px-4 py-3 text-slate-600">
                    {contract.organization?.name ?? "-"}
                  </td>
                  <td className="px-4 py-3 text-slate-600">{contract.status ?? "-"}</td>
                  <td className="px-4 py-3 font-semibold text-slate-950">
                    {currency(contract.total_value)}
                  </td>
                  <td className="px-4 py-3 print:hidden">
                    <Link
                      className="rounded-md border border-slate-300 px-3 py-2 text-xs font-medium text-slate-700 hover:bg-slate-50"
                      href={`/contratos/${contract.id}`}
                    >
                      Abrir relatorio
                    </Link>
                  </td>
                </tr>
              ))}
              {filtered.length === 0 ? (
                <tr>
                  <td className="px-4 py-8 text-center text-sm text-slate-500" colSpan={7}>
                    Nenhum contrato encontrado para este filtro. Rode a ingestao no Admin ou ajuste os filtros.
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
});

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium text-slate-500">{label}</p>
        <Building2 className="h-5 w-5 text-emerald-700" />
      </div>
      <p className="mt-3 text-2xl font-semibold text-slate-950">{value}</p>
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
