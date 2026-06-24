"use client";

import { FileText, Search, Users } from "lucide-react";
import Link from "next/link";
import { memo, useMemo, useState } from "react";
import type { Person } from "@/lib/api";
import { PrintReportButton } from "@/components/PrintReportButton";

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

type PoliticiansExplorerProps = {
  persons: Person[];
  isFallback?: boolean;
};

export const PoliticiansExplorer = memo(function PoliticiansExplorer({
  persons,
  isFallback = false,
}: PoliticiansExplorerProps) {
  const [query, setQuery] = useState("");
  const [role, setRole] = useState("Todos");
  const [stateCode, setStateCode] = useState("Todos");

  const states = useMemo(
    () =>
      Array.from(
        new Set(persons.map((person) => person.state_code).filter(Boolean) as string[]),
      ).sort(),
    [persons],
  );

  const filtered = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    return persons.filter((person) => {
      const roles = person.roles ?? [];
      const matchesQuery =
        !normalizedQuery ||
        person.full_name.toLowerCase().includes(normalizedQuery) ||
        (person.party_acronym ?? "").toLowerCase().includes(normalizedQuery) ||
        roles.some((item) => item.role_name.toLowerCase().includes(normalizedQuery));
      const matchesRole =
        role === "Todos" ||
        roles.some((item) => item.role_name.toLowerCase().includes(role.toLowerCase()));
      const matchesState = stateCode === "Todos" || person.state_code === stateCode;
      return matchesQuery && matchesRole && matchesState;
    });
  }, [persons, query, role, stateCode]);

  const roleCounts = useMemo(() => {
    const counts = new Map<string, number>();
    persons.forEach((person) => {
      (person.roles ?? []).forEach((item) => {
        counts.set(item.role_name, (counts.get(item.role_name) ?? 0) + 1);
      });
    });
    return Array.from(counts.entries()).sort((a, b) => b[1] - a[1]);
  }, [persons]);

  return (
    <section>
      <div className="mb-6 grid gap-4 md:grid-cols-3">
        <Metric label="Registros" value={String(persons.length)} />
        <Metric label="No filtro atual" value={String(filtered.length)} />
        <Metric label="Cargos distintos" value={String(roleCounts.length)} />
      </div>

      <div className="mb-4 rounded-lg border border-slate-200 bg-white p-4 shadow-sm print:hidden">
        <div className="grid gap-3 lg:grid-cols-[minmax(220px,1fr)_220px_160px_auto]">
          <label className="relative block">
            <span className="sr-only">Buscar politico</span>
            <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
            <input
              className="w-full rounded-md border border-slate-300 py-2 pl-9 pr-3 text-sm outline-none focus:border-slate-500"
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Buscar por nome, partido ou cargo"
              value={query}
            />
          </label>
          <select
            className="rounded-md border border-slate-300 px-3 py-2 text-sm outline-none focus:border-slate-500"
            onChange={(event) => setRole(event.target.value)}
            value={role}
          >
            {roleOptions.map((item) => (
              <option key={item}>{item}</option>
            ))}
          </select>
          <select
            className="rounded-md border border-slate-300 px-3 py-2 text-sm outline-none focus:border-slate-500"
            onChange={(event) => setStateCode(event.target.value)}
            value={stateCode}
          >
            <option>Todos</option>
            {states.map((item) => (
              <option key={item}>{item}</option>
            ))}
          </select>
          <PrintReportButton />
        </div>
        <div className="mt-3 flex flex-wrap gap-2">
          {roleCounts.slice(0, 10).map(([roleName, count]) => (
            <button
              className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-700 hover:bg-slate-200"
              key={roleName}
              onClick={() => setRole(roleName)}
              type="button"
            >
              {roleName}: {count}
            </button>
          ))}
        </div>
      </div>

      <div className="mb-4 flex items-center justify-between">
        <div>
          <h3 className="text-base font-semibold text-slate-950">
            Lista de agentes publicos
          </h3>
          <p className="mt-1 text-sm text-slate-500">
            {isFallback
              ? "Amostra demonstrativa enquanto a base real esta vazia."
              : "Clique em um registro para abrir o relatorio individual."}
          </p>
        </div>
        <FileText className="h-5 w-5 text-slate-400" />
      </div>

      <div className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
        <div className="overflow-x-auto">
          <table className="min-w-[1040px] w-full text-left text-sm">
            <thead className="bg-slate-50 text-xs uppercase text-slate-500">
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
            <tbody className="divide-y divide-slate-100">
              {filtered.map((person) => (
                <tr className="hover:bg-slate-50" key={person.id}>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-3">
                      <div className="h-10 w-10 overflow-hidden rounded-md bg-slate-100">
                        {person.photo_url ? (
                          <img alt="" className="h-full w-full object-cover" src={person.photo_url} />
                        ) : (
                          <div className="flex h-full w-full items-center justify-center text-sm font-semibold text-slate-500">
                            {person.full_name.slice(0, 1)}
                          </div>
                        )}
                      </div>
                      <span className="font-medium text-slate-950">{person.full_name}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-slate-600">{rolesLabel(person)}</td>
                  <td className="px-4 py-3 text-slate-600">{person.party_acronym ?? "-"}</td>
                  <td className="px-4 py-3 text-slate-600">{person.state_code ?? "-"}</td>
                  <td className="px-4 py-3 font-medium text-slate-950">
                    {currency(person.declared_assets_value)}
                  </td>
                  <td className="px-4 py-3 text-slate-600">
                    {ratioLabel(person.asset_salary_ratio)}
                  </td>
                  <td className="px-4 py-3 text-slate-600">{person.data_origin ?? "-"}</td>
                  <td className="px-4 py-3 print:hidden">
                    <Link
                      className="rounded-md border border-slate-300 px-3 py-2 text-xs font-medium text-slate-700 hover:bg-slate-50"
                      href={`/politicos/${person.id}`}
                    >
                      Abrir relatorio
                    </Link>
                  </td>
                </tr>
              ))}
              {filtered.length === 0 ? (
                <tr>
                  <td className="px-4 py-8 text-center text-sm text-slate-500" colSpan={8}>
                    Nenhum agente encontrado para este filtro. Rode a ingestao no Admin ou ajuste os filtros.
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
        <Users className="h-5 w-5 text-emerald-700" />
      </div>
      <p className="mt-3 text-2xl font-semibold text-slate-950">{value}</p>
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
