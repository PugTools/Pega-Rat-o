import Link from "next/link";
import { notFound } from "next/navigation";
import { Mail, MapPin, UserRound } from "lucide-react";
import type { ReactNode } from "react";
import { PrintReportButton } from "@/components/PrintReportButton";
import { api, type PersonDetail } from "@/lib/api";

type PageProps = {
  params: Promise<{ id: string }>;
};

export default async function PoliticoDetailPage({ params }: PageProps) {
  const { id } = await params;
  const person = await getPerson(id);
  if (!person) {
    notFound();
  }

  return (
    <main className="mx-auto max-w-5xl">
      <div className="mb-6 flex flex-col gap-3 border-b border-slate-200 pb-5 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <Link className="text-sm font-medium text-slate-500 print:hidden" href="/politicos">
            Voltar para politicos
          </Link>
          <h2 className="mt-2 text-2xl font-semibold text-slate-950">
            Relatorio individual
          </h2>
        </div>
        <PrintReportButton />
      </div>

      <section className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-col gap-5 sm:flex-row sm:items-start">
          <div className="h-28 w-28 overflow-hidden rounded-lg bg-slate-100">
            {person.photo_url ? (
              <img alt="" className="h-full w-full object-cover" src={person.photo_url} />
            ) : (
              <div className="flex h-full w-full items-center justify-center">
                <UserRound className="h-10 w-10 text-slate-400" />
              </div>
            )}
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-sm font-semibold uppercase text-emerald-700">
              {rolesLabel(person)}
            </p>
            <h1 className="mt-1 text-3xl font-semibold text-slate-950">
              {person.full_name}
            </h1>
            <div className="mt-3 flex flex-wrap gap-2 text-sm text-slate-600">
              <span className="rounded-md bg-slate-100 px-2.5 py-1">
                Partido: {person.party_acronym ?? "-"}
              </span>
              <span className="rounded-md bg-slate-100 px-2.5 py-1">
                UF: {person.state_code ?? "-"}
              </span>
              <span className="rounded-md bg-slate-100 px-2.5 py-1">
                Fonte: {person.data_origin ?? "-"}
              </span>
            </div>
            <div className="mt-4 grid gap-2 text-sm text-slate-600 sm:grid-cols-2">
              <Info icon={<Mail className="h-4 w-4" />} value={person.email ?? "Email nao informado"} />
              <Info icon={<MapPin className="h-4 w-4" />} value={locationLabel(person)} />
            </div>
          </div>
        </div>
      </section>

      <section className="mt-5 grid gap-4 md:grid-cols-3">
        <Metric label="Gasto consolidado" value={currency(person.latest_expense_total)} />
        <Metric label="Ano de referencia" value={String(person.latest_expense_year ?? "-")} />
        <Metric label="Despesas recentes" value={String(person.recent_expenses?.length ?? 0)} />
      </section>

      <section className="mt-5 rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <h3 className="text-base font-semibold text-slate-950">Cargos registrados</h3>
        <div className="mt-4 grid gap-3 md:grid-cols-2">
          {(person.roles ?? []).map((role) => (
            <div className="rounded-md border border-slate-200 p-4" key={role.id}>
              <p className="font-semibold text-slate-950">{role.role_name}</p>
              <p className="mt-1 text-sm text-slate-500">
                {role.jurisdiction_level ?? "nivel nao informado"} / {role.state_code ?? "-"}
              </p>
              <p className="mt-1 text-sm text-slate-500">
                Partido no cargo: {role.party_acronym ?? person.party_acronym ?? "-"}
              </p>
            </div>
          ))}
          {!person.roles?.length ? (
            <p className="text-sm text-slate-500">Nenhum cargo registrado para esta pessoa.</p>
          ) : null}
        </div>
      </section>

      <section className="mt-5 rounded-lg border border-slate-200 bg-white shadow-sm">
        <div className="border-b border-slate-200 px-5 py-4">
          <h3 className="text-base font-semibold text-slate-950">
            Despesas recentes vinculadas
          </h3>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-[720px] w-full text-left text-sm">
            <thead className="bg-slate-50 text-xs uppercase text-slate-500">
              <tr>
                <th className="px-4 py-3">Data</th>
                <th className="px-4 py-3">Tipo</th>
                <th className="px-4 py-3">Descricao</th>
                <th className="px-4 py-3">Valor</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {(person.recent_expenses ?? []).map((expense) => (
                <tr key={expense.id}>
                  <td className="px-4 py-3 text-slate-600">{expense.expense_date}</td>
                  <td className="px-4 py-3 text-slate-600">{expense.expense_type ?? "-"}</td>
                  <td className="px-4 py-3 text-slate-600">{expense.description ?? "-"}</td>
                  <td className="px-4 py-3 font-semibold text-slate-950">
                    {currency(expense.amount)}
                  </td>
                </tr>
              ))}
              {!person.recent_expenses?.length ? (
                <tr>
                  <td className="px-4 py-8 text-center text-slate-500" colSpan={4}>
                    Nenhuma despesa vinculada a este politico ainda.
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  );
}

async function getPerson(id: string): Promise<PersonDetail | null> {
  try {
    return await api.getPerson(id);
  } catch {
    return null;
  }
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <p className="text-sm font-medium text-slate-500">{label}</p>
      <p className="mt-2 text-2xl font-semibold text-slate-950">{value}</p>
    </div>
  );
}

function Info({ icon, value }: { icon: ReactNode; value: string }) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-slate-400">{icon}</span>
      <span>{value}</span>
    </div>
  );
}

function rolesLabel(person: PersonDetail) {
  const roles = person.roles ?? [];
  if (!roles.length) {
    return "Cargo nao informado";
  }
  return roles.map((item) => item.role_name).join(", ");
}

function locationLabel(person: PersonDetail) {
  const role = person.roles?.[0];
  return [role?.municipality_code, person.state_code].filter(Boolean).join(" / ") || "Localidade nao informada";
}

function currency(value: string | number | null | undefined) {
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
    maximumFractionDigits: 0,
  }).format(Number(value ?? 0));
}
