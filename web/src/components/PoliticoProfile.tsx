"use client";

import { Landmark, Mail, MapPin, TrendingUp, Users, WalletCards } from "lucide-react";
import { memo, useMemo } from "react";
import type { Person } from "@/lib/api";

type PoliticoProfileProps = {
  persons: Person[];
  isFallback?: boolean;
};

type SummaryMetric = {
  label: string;
  value: string;
  detail: string;
  icon: typeof Users;
};

function currency(value: string | number | null | undefined) {
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
    maximumFractionDigits: 0,
  }).format(Number(value ?? 0));
}

function displayValue(value: string | number | null | undefined, fallback = "Nao informado") {
  return value === null || value === undefined || value === "" ? fallback : value;
}

function numberValue(value: string | number | null | undefined) {
  return Number(value ?? 0);
}

function mostFrequent(values: Array<string | null | undefined>) {
  const counts = new Map<string, number>();
  values.forEach((value) => {
    if (value) {
      counts.set(value, (counts.get(value) ?? 0) + 1);
    }
  });

  return [...counts.entries()].sort((a, b) => b[1] - a[1])[0] ?? null;
}

export const PoliticoProfile = memo(function PoliticoProfile({
  persons,
  isFallback = false,
}: PoliticoProfileProps) {
  const analytics = useMemo(() => {
    const sortedBySpending = [...persons].sort(
      (a, b) => numberValue(b.latest_expense_total) - numberValue(a.latest_expense_total),
    );
    const totalSpending = sortedBySpending.reduce(
      (sum, person) => sum + numberValue(person.latest_expense_total),
      0,
    );
    const featured = sortedBySpending[0] ?? persons[0] ?? null;
    const topParty = mostFrequent(persons.map((person) => person.party_acronym));
    const topState = mostFrequent(persons.map((person) => person.state_code));
    const maxSpending = numberValue(sortedBySpending[0]?.latest_expense_total);

    const metrics: SummaryMetric[] = [
      {
        label: "Politicos",
        value: String(persons.length),
        detail: isFallback ? "amostra demonstrativa" : "registros reais/cacheados",
        icon: Users,
      },
      {
        label: "Gasto agregado",
        value: currency(totalSpending),
        detail: featured?.latest_expense_year
          ? `ano ${featured.latest_expense_year}`
          : "sem ano de referencia",
        icon: WalletCards,
      },
      {
        label: "Partido mais presente",
        value: topParty?.[0] ?? "-",
        detail: topParty ? `${topParty[1]} registros` : "sem partido",
        icon: Landmark,
      },
      {
        label: "UF mais presente",
        value: topState?.[0] ?? "-",
        detail: topState ? `${topState[1]} registros` : "sem UF",
        icon: MapPin,
      },
    ];

    return {
      featured,
      maxSpending,
      metrics,
      topSpenders: sortedBySpending.slice(0, 6),
    };
  }, [isFallback, persons]);

  return (
    <section className="mt-6">
      <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h3 className="text-lg font-semibold text-slate-950">
            Transparencia parlamentar
          </h3>
          <p className="mt-1 text-sm text-slate-500">
            Deputados e senadores, partidos, UF e gastos oficiais disponíveis.
          </p>
        </div>
        <span className="w-fit rounded-md border border-slate-200 bg-white px-3 py-2 text-xs font-medium text-slate-600">
          {isFallback ? "Dados demonstrativos" : "Dados do backend"}
        </span>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {analytics.metrics.map((metric) => {
          const Icon = metric.icon;
          return (
            <div
              className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm"
              key={metric.label}
            >
              <div className="flex items-center justify-between gap-3">
                <p className="text-sm font-medium text-slate-500">{metric.label}</p>
                <Icon className="h-5 w-5 text-emerald-700" />
              </div>
              <p className="mt-3 text-2xl font-semibold text-slate-950">
                {metric.value}
              </p>
              <p className="mt-1 text-xs text-slate-500">{metric.detail}</p>
            </div>
          );
        })}
      </div>

      <div className="mt-4 grid gap-4 xl:grid-cols-[minmax(280px,0.85fr)_minmax(0,1.15fr)]">
        <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          {analytics.featured ? (
            <>
              <div className="flex items-start gap-4">
                <div className="h-20 w-20 shrink-0 overflow-hidden rounded-lg bg-slate-100">
                  {analytics.featured.photo_url ? (
                    <img
                      alt=""
                      className="h-full w-full object-cover"
                      src={analytics.featured.photo_url}
                    />
                  ) : (
                    <div className="flex h-full w-full items-center justify-center text-xl font-semibold text-slate-400">
                      {analytics.featured.full_name.slice(0, 1)}
                    </div>
                  )}
                </div>
                <div className="min-w-0">
                  <p className="text-xs font-semibold uppercase text-emerald-700">
                    Maior gasto no recorte
                  </p>
                  <h4 className="mt-1 truncate text-xl font-semibold text-slate-950">
                    {analytics.featured.full_name}
                  </h4>
                  <p className="mt-1 text-sm text-slate-500">
                    {displayValue(analytics.featured.party_acronym, "-")} /{" "}
                    {displayValue(analytics.featured.state_code, "-")}
                  </p>
                </div>
              </div>

              <div className="mt-5 rounded-lg bg-slate-50 p-4">
                <div className="flex items-center gap-2 text-sm font-medium text-slate-700">
                  <TrendingUp className="h-4 w-4 text-emerald-700" />
                  Gasto registrado
                </div>
                <p className="mt-2 text-3xl font-semibold text-slate-950">
                  {currency(analytics.featured.latest_expense_total)}
                </p>
                <p className="mt-1 text-xs text-slate-500">
                  Fonte: {displayValue(analytics.featured.data_origin)}
                </p>
              </div>

              <div className="mt-5 space-y-2 text-sm">
                <div className="flex items-center gap-2 text-slate-600">
                  <Mail className="h-4 w-4 text-slate-400" />
                  <span className="truncate">{displayValue(analytics.featured.email)}</span>
                </div>
                <div className="flex items-center gap-2 text-slate-600">
                  <MapPin className="h-4 w-4 text-slate-400" />
                  <span>{displayValue(analytics.featured.state_code)}</span>
                </div>
              </div>
            </>
          ) : (
            <p className="text-sm text-slate-500">
              Nenhum politico retornado pelo backend.
            </p>
          )}
        </div>

        <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h4 className="text-base font-semibold text-slate-950">
                Ranking de gastos
              </h4>
              <p className="mt-1 text-sm text-slate-500">
                Comparacao proporcional dos maiores valores.
              </p>
            </div>
            <WalletCards className="h-5 w-5 text-emerald-700" />
          </div>

          <div className="space-y-4">
            {analytics.topSpenders.map((person) => {
              const amount = numberValue(person.latest_expense_total);
              const percent =
                analytics.maxSpending > 0 ? Math.max((amount / analytics.maxSpending) * 100, 4) : 4;
              return (
                <div key={person.id}>
                  <div className="flex items-center justify-between gap-3 text-sm">
                    <span className="truncate font-medium text-slate-800">
                      {person.full_name}
                    </span>
                    <span className="shrink-0 font-semibold text-slate-950">
                      {currency(amount)}
                    </span>
                  </div>
                  <div className="mt-2 h-2 overflow-hidden rounded-full bg-slate-100">
                    <div
                      className="h-full rounded-full bg-emerald-600"
                      style={{ width: `${percent}%` }}
                    />
                  </div>
                  <p className="mt-1 text-xs text-slate-500">
                    {displayValue(person.party_acronym, "-")} /{" "}
                    {displayValue(person.state_code, "-")}
                  </p>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      <div className="mt-4 overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
        <div className="overflow-x-auto">
          <table className="min-w-[760px] w-full text-left text-sm">
            <thead className="bg-slate-50 text-xs uppercase text-slate-500">
              <tr>
                <th className="px-4 py-3">Politico</th>
                <th className="px-4 py-3">Partido</th>
                <th className="px-4 py-3">UF</th>
                <th className="px-4 py-3">Gasto</th>
                <th className="px-4 py-3">Origem</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {persons.map((person) => (
                <tr className="hover:bg-slate-50" key={person.id}>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-3">
                      <div className="h-9 w-9 overflow-hidden rounded-md bg-slate-100">
                        {person.photo_url ? (
                          <img
                            alt=""
                            className="h-full w-full object-cover"
                            src={person.photo_url}
                          />
                        ) : (
                          <div className="flex h-full w-full items-center justify-center text-xs font-semibold text-slate-500">
                            {person.full_name.slice(0, 1)}
                          </div>
                        )}
                      </div>
                      <span className="font-medium text-slate-900">
                        {person.full_name}
                      </span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-slate-600">
                    {displayValue(person.party_acronym, "-")}
                  </td>
                  <td className="px-4 py-3 text-slate-600">
                    {displayValue(person.state_code, "-")}
                  </td>
                  <td className="px-4 py-3 font-semibold text-slate-950">
                    {currency(person.latest_expense_total)}
                  </td>
                  <td className="px-4 py-3 text-slate-600">
                    {displayValue(person.data_origin, "-")}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
});

export function PoliticoProfileSkeleton() {
  return (
    <section className="mt-6 animate-pulse">
      <div className="mb-4 h-8 w-72 rounded bg-slate-200" />
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {Array.from({ length: 4 }).map((_, index) => (
          <div className="h-28 rounded-lg border border-slate-200 bg-white p-4" key={index}>
            <div className="h-4 w-24 rounded bg-slate-200" />
            <div className="mt-5 h-7 w-32 rounded bg-slate-200" />
          </div>
        ))}
      </div>
      <div className="mt-4 grid gap-4 xl:grid-cols-[minmax(280px,0.85fr)_minmax(0,1.15fr)]">
        <div className="h-80 rounded-lg border border-slate-200 bg-white" />
        <div className="h-80 rounded-lg border border-slate-200 bg-white" />
      </div>
    </section>
  );
}
