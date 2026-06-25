import Link from "next/link";
import { notFound } from "next/navigation";
import { Building2 } from "lucide-react";
import { api, type Company } from "@/lib/api";

type PageProps = {
  params: Promise<{ id: string }>;
};

export default async function EmpresaDetailPage({ params }: PageProps) {
  const { id } = await params;
  const company = await getCompany(id);
  if (!company) {
    notFound();
  }

  return (
    <main className="mx-auto max-w-4xl">
      <div className="mb-6 border-b border-slate-200 pb-5">
        <Link className="text-sm font-medium text-slate-500" href="/politicos">
          Voltar para politicos
        </Link>
        <h2 className="mt-2 text-2xl font-semibold text-slate-950">
          Perfil do fornecedor
        </h2>
      </div>

      <section className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex items-start gap-4">
          <div className="rounded-lg bg-slate-100 p-3 text-slate-600">
            <Building2 className="h-7 w-7" />
          </div>
          <div>
            <p className="text-sm font-semibold uppercase text-emerald-700">
              Empresa fornecedora
            </p>
            <h1 className="mt-1 text-3xl font-semibold text-slate-950">
              {company.legal_name}
            </h1>
            {company.trade_name ? (
              <p className="mt-2 text-sm text-slate-600">{company.trade_name}</p>
            ) : null}
          </div>
        </div>

        <div className="mt-6 grid gap-3 md:grid-cols-3">
          <Metric label="CNPJ" value={formatCnpj(company.cnpj)} />
          <Metric label="UF" value={company.state_code ?? "-"} />
          <Metric label="Situacao" value={company.registration_status ?? "-"} />
        </div>
      </section>
    </main>
  );
}

async function getCompany(id: string): Promise<Company | null> {
  try {
    return await api.getCompany(id);
  } catch {
    return null;
  }
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <p className="text-sm font-medium text-slate-500">{label}</p>
      <p className="mt-2 break-words text-lg font-semibold text-slate-950">{value}</p>
    </div>
  );
}

function formatCnpj(value: string) {
  const digits = value.replace(/\D/g, "");
  if (digits.length !== 14) {
    return value;
  }
  return `${digits.slice(0, 2)}.${digits.slice(2, 5)}.${digits.slice(5, 8)}/${digits.slice(8, 12)}-${digits.slice(12)}`;
}
