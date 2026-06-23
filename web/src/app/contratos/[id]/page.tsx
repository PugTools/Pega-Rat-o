import Link from "next/link";
import { notFound } from "next/navigation";
import { Building2, CalendarDays, FileText } from "lucide-react";
import type { ReactNode } from "react";
import { PrintReportButton } from "@/components/PrintReportButton";
import { api, type ContractDetail } from "@/lib/api";

type PageProps = {
  params: Promise<{ id: string }>;
};

export default async function ContractDetailPage({ params }: PageProps) {
  const { id } = await params;
  const contract = await getContract(id);
  if (!contract) {
    notFound();
  }

  return (
    <main className="mx-auto max-w-5xl">
      <div className="mb-6 flex flex-col gap-3 border-b border-slate-200 pb-5 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <Link className="text-sm font-medium text-slate-500 print:hidden" href="/contratos">
            Voltar para contratos
          </Link>
          <h2 className="mt-2 text-2xl font-semibold text-slate-950">
            Relatorio do contrato
          </h2>
        </div>
        <PrintReportButton />
      </div>

      <section className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex items-start gap-4">
          <div className="rounded-lg bg-slate-100 p-3 text-slate-700">
            <FileText className="h-7 w-7" />
          </div>
          <div>
            <p className="text-sm font-semibold uppercase text-emerald-700">
              {contract.status ?? "Status nao informado"}
            </p>
            <h1 className="mt-1 text-2xl font-semibold text-slate-950">
              {contract.contract_number ?? contract.process_number ?? "Contrato sem numero"}
            </h1>
            <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-600">
              {contract.object ?? "Objeto nao informado"}
            </p>
          </div>
        </div>
      </section>

      <section className="mt-5 grid gap-4 md:grid-cols-3">
        <Metric label="Valor contratado" value={currency(contract.total_value)} />
        <Metric label="Despesas vinculadas" value={currency(contract.expense_total)} />
        <Metric label="Lancamentos" value={String(contract.expenses?.length ?? 0)} />
      </section>

      <section className="mt-5 grid gap-4 lg:grid-cols-2">
        <InfoCard
          icon={<Building2 className="h-5 w-5" />}
          title="Fornecedor"
          lines={[
            contract.supplier?.legal_name ?? "Fornecedor nao informado",
            contract.supplier?.cnpj ? `CNPJ: ${contract.supplier.cnpj}` : "CNPJ nao informado",
            contract.supplier?.state_code ? `UF: ${contract.supplier.state_code}` : "UF nao informada",
          ]}
        />
        <InfoCard
          icon={<Building2 className="h-5 w-5" />}
          title="Orgao contratante"
          lines={[
            contract.organization?.name ?? "Orgao nao informado",
            contract.organization?.jurisdiction_level
              ? `Nivel: ${contract.organization.jurisdiction_level}`
              : "Nivel nao informado",
            contract.organization?.state_code
              ? `UF: ${contract.organization.state_code}`
              : "UF nao informada",
          ]}
        />
      </section>

      <section className="mt-5 rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex items-center gap-2">
          <CalendarDays className="h-5 w-5 text-slate-400" />
          <h3 className="text-base font-semibold text-slate-950">Vigencia</h3>
        </div>
        <div className="mt-4 grid gap-3 text-sm text-slate-600 md:grid-cols-3">
          <p>Assinatura: {contract.signed_at ?? "-"}</p>
          <p>Inicio: {contract.starts_at ?? "-"}</p>
          <p>Fim: {contract.ends_at ?? "-"}</p>
        </div>
      </section>

      <section className="mt-5 rounded-lg border border-slate-200 bg-white shadow-sm">
        <div className="border-b border-slate-200 px-5 py-4">
          <h3 className="text-base font-semibold text-slate-950">
            Despesas vinculadas ao contrato
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
              {(contract.expenses ?? []).map((expense) => (
                <tr key={expense.id}>
                  <td className="px-4 py-3 text-slate-600">{expense.expense_date}</td>
                  <td className="px-4 py-3 text-slate-600">{expense.expense_type ?? "-"}</td>
                  <td className="px-4 py-3 text-slate-600">{expense.description ?? "-"}</td>
                  <td className="px-4 py-3 font-semibold text-slate-950">
                    {currency(expense.amount)}
                  </td>
                </tr>
              ))}
              {!contract.expenses?.length ? (
                <tr>
                  <td className="px-4 py-8 text-center text-slate-500" colSpan={4}>
                    Nenhuma despesa vinculada a este contrato ainda.
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

async function getContract(id: string): Promise<ContractDetail | null> {
  try {
    return await api.getContract(id);
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

function InfoCard({
  icon,
  lines,
  title,
}: {
  icon: ReactNode;
  lines: string[];
  title: string;
}) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-center gap-2">
        <span className="text-slate-400">{icon}</span>
        <h3 className="text-base font-semibold text-slate-950">{title}</h3>
      </div>
      <div className="mt-4 space-y-2 text-sm text-slate-600">
        {lines.map((line) => (
          <p key={line}>{line}</p>
        ))}
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
