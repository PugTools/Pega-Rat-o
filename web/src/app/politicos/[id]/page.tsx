import Link from "next/link";
import { notFound } from "next/navigation";
import { Building2, ExternalLink, FileText, Mail, MapPin, ReceiptText, UserRound } from "lucide-react";
import type { ReactNode } from "react";
import { PrintReportButton } from "@/components/PrintReportButton";
import { api, type Expense, type PersonDetail } from "@/lib/api";

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
        <Metric label="Patrimonio declarado" value={currency(person.declared_assets_value)} />
        <Metric label="Salario anual ref." value={currency(person.salary_reference_value)} />
        <Metric label="Patrimonio / salario" value={ratioLabel(person.asset_salary_ratio)} />
      </section>

      <section className="mt-5 rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <h3 className="text-base font-semibold text-slate-950">
              Indicador patrimonial
            </h3>
            <p className="mt-1 text-sm leading-6 text-slate-600">
              {assetRiskText(person)}
            </p>
          </div>
          <div className={`w-fit rounded-md px-3 py-2 text-sm font-semibold ${assetRiskClass(person.asset_salary_ratio)}`}>
            {assetRiskLabel(person.asset_salary_ratio)}
          </div>
        </div>
        <div className="mt-4 grid gap-3 text-sm text-slate-600 md:grid-cols-3">
          <p>Ano dos bens: {person.declared_assets_year ?? "-"}</p>
          <p>Ano da referencia salarial: {person.salary_reference_year ?? "-"}</p>
          <p>Fonte salarial: {person.salary_reference_source ?? "referencia nao informada"}</p>
        </div>
      </section>

      <section className="mt-5 grid gap-4 md:grid-cols-3">
        <Metric label="Gasto consolidado" value={currency(person.latest_expense_total)} />
        <Metric label="Ano de gastos" value={String(person.latest_expense_year ?? "-")} />
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
          <p className="mt-1 text-sm text-slate-500">
            Gastos com fornecedor, documento fiscal e trilha de origem quando a fonte publica informar.
          </p>
        </div>
        <div className="grid gap-4 p-5">
          {(person.recent_expenses ?? []).map((expense) => (
            <ExpenseAuditCard expense={expense} key={expense.id} />
          ))}
          {!person.recent_expenses?.length ? (
            <div className="rounded-lg border border-dashed border-slate-300 p-8 text-center text-sm text-slate-500">
              Nenhuma despesa vinculada a este politico ainda.
            </div>
          ) : null}
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

function ExpenseAuditCard({ expense }: { expense: Expense }) {
  const supplierId = expense.supplier_company_id ?? expense.company_id;
  const supplierName = expense.supplier_name ?? "Fornecedor nao vinculado";
  const supplierCnpj = expense.supplier_cnpj
    ? formatCnpj(expense.supplier_cnpj)
    : "CNPJ nao informado";
  const documentNumber =
    expense.commitment_number ?? expense.payment_number ?? expense.liquidation_number ?? "-";

  return (
    <article className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex flex-col gap-3 border-b border-slate-100 pb-4 md:flex-row md:items-center md:justify-between">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-sm font-medium text-slate-500">
            {formatDate(expense.expense_date)}
          </span>
          <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${expenseBadgeClass(expense.expense_type)}`}>
            {expense.expense_type ?? "Despesa"}
          </span>
        </div>
        <p className="text-xl font-semibold text-slate-950">
          {currency(expense.amount)}
        </p>
      </div>

      <div className="mt-4 grid gap-4 text-sm text-slate-600 md:grid-cols-2">
        <div className="rounded-md bg-slate-50 p-3">
          <div className="flex items-center gap-2 font-semibold text-slate-950">
            <Building2 className="h-4 w-4 text-slate-500" />
            Fornecedor
          </div>
          <div className="mt-2">
            {supplierId ? (
              <Link className="font-medium text-blue-700 hover:text-blue-900" href={`/empresas/${supplierId}`}>
                {supplierName}
              </Link>
            ) : (
              <span className="font-medium text-slate-800">{supplierName}</span>
            )}
            <p className="mt-1 text-xs text-slate-500">{supplierCnpj}</p>
          </div>
        </div>

        <div className="rounded-md bg-slate-50 p-3">
          <div className="flex items-center gap-2 font-semibold text-slate-950">
            <ReceiptText className="h-4 w-4 text-slate-500" />
            Nota Fiscal / Empenho
          </div>
          <p className="mt-2 font-mono text-sm text-slate-700">{documentNumber}</p>
        </div>
      </div>

      <div className="mt-4 rounded-md border border-slate-200 p-3">
        <div className="flex items-center gap-2 font-semibold text-slate-950">
          <FileText className="h-4 w-4 text-slate-500" />
          Detalhes
        </div>
        <p className="mt-2 text-sm leading-6 text-slate-600">
          {expense.description ?? "Descricao nao informada pela fonte."}
        </p>
      </div>

      <div className="mt-4 flex justify-end">
        {expense.document_url ? (
          <a
            className="inline-flex items-center gap-2 rounded-md border border-slate-300 px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"
            href={expense.document_url}
            rel="noreferrer"
            target="_blank"
          >
            <ExternalLink className="h-4 w-4" />
            Ver Nota Fiscal
          </a>
        ) : (
          <span className="inline-flex items-center gap-2 rounded-md border border-slate-200 px-3 py-2 text-sm font-medium text-slate-400">
            <ExternalLink className="h-4 w-4" />
            Nota fiscal indisponivel
          </span>
        )}
      </div>
    </article>
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

function formatDate(value: string) {
  const parsed = new Date(`${value}T00:00:00`);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  }).format(parsed);
}

function formatCnpj(value: string) {
  const digits = value.replace(/\D/g, "");
  if (digits.length !== 14) {
    return value;
  }
  return `${digits.slice(0, 2)}.${digits.slice(2, 5)}.${digits.slice(5, 8)}/${digits.slice(8, 12)}-${digits.slice(12)}`;
}

function expenseBadgeClass(value: string | null | undefined) {
  const normalized = (value ?? "").toLowerCase();
  if (normalized.includes("hosped") || normalized.includes("hotel")) {
    return "bg-blue-50 text-blue-700";
  }
  if (normalized.includes("passagem") || normalized.includes("aereo") || normalized.includes("voo")) {
    return "bg-orange-50 text-orange-700";
  }
  if (normalized.includes("combust")) {
    return "bg-amber-50 text-amber-700";
  }
  if (normalized.includes("divulg") || normalized.includes("consult")) {
    return "bg-violet-50 text-violet-700";
  }
  return "bg-slate-100 text-slate-700";
}

function ratioLabel(value: string | number | null | undefined) {
  const ratio = Number(value ?? 0);
  if (!ratio) {
    return "-";
  }
  return `${ratio.toLocaleString("pt-BR", { maximumFractionDigits: 1 })} anos`;
}

function assetRiskLabel(value: string | number | null | undefined) {
  const ratio = Number(value ?? 0);
  if (!ratio) {
    return "Sem dados suficientes";
  }
  if (ratio >= 30) {
    return "Prioridade critica";
  }
  if (ratio >= 15) {
    return "Prioridade alta";
  }
  if (ratio >= 8) {
    return "Monitorar";
  }
  return "Compativel na regua atual";
}

function assetRiskClass(value: string | number | null | undefined) {
  const ratio = Number(value ?? 0);
  if (!ratio) {
    return "bg-slate-100 text-slate-700";
  }
  if (ratio >= 30) {
    return "bg-red-50 text-red-800";
  }
  if (ratio >= 15) {
    return "bg-amber-50 text-amber-800";
  }
  if (ratio >= 8) {
    return "bg-yellow-50 text-yellow-800";
  }
  return "bg-emerald-50 text-emerald-800";
}

function assetRiskText(person: PersonDetail) {
  const ratio = Number(person.asset_salary_ratio ?? 0);
  if (!ratio) {
    return "Nao ha patrimonio declarado e remuneracao de referencia suficientes para calcular este indicador.";
  }
  return `O patrimonio declarado equivale a ${ratioLabel(ratio)} da remuneracao anual de referencia do cargo. Este indicador prioriza auditoria e nao prova irregularidade sozinho.`;
}
