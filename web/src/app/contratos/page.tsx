import { api, type Contract } from "@/lib/api";

const fallbackContracts: Contract[] = [
  {
    id: "mock-contract-1",
    contract_number: "CT-2026-001",
    object: "Servico continuado de tecnologia",
    status: "monitorado",
    total_value: "1250000.00",
    created_at: new Date().toISOString(),
  },
  {
    id: "mock-contract-2",
    contract_number: "CT-2026-002",
    object: "Fornecimento de insumos administrativos",
    status: "em analise",
    total_value: "420000.00",
    created_at: new Date().toISOString(),
  },
];

async function getContracts(): Promise<{ contracts: Contract[]; isFallback: boolean }> {
  try {
    const contracts = await api.listContracts(100);
    return {
      contracts: contracts.length ? contracts : fallbackContracts,
      isFallback: contracts.length === 0,
    };
  } catch {
    return { contracts: fallbackContracts, isFallback: true };
  }
}

function currency(value: string | number | null | undefined) {
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
  }).format(Number(value ?? 0));
}

export default async function ContratosPage() {
  const { contracts, isFallback } = await getContracts();

  return (
    <div className="mx-auto max-w-7xl">
      <div className="mb-6 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-sm font-medium text-slate-500">
            Contratos publicos monitorados
          </p>
          <h2 className="mt-1 text-2xl font-semibold text-slate-950">Contratos</h2>
        </div>
        <span className="w-fit rounded-md border border-slate-200 bg-white px-3 py-2 text-xs font-medium text-slate-600">
          {isFallback ? "Dados demonstrativos" : "Dados do backend"}
        </span>
      </div>

      <section className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
        <table className="w-full text-left text-sm">
          <thead className="bg-slate-50 text-xs uppercase text-slate-500">
            <tr>
              <th className="px-4 py-3">Contrato</th>
              <th className="px-4 py-3">Objeto</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Valor</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {contracts.map((contract) => (
              <tr key={contract.id}>
                <td className="px-4 py-3 font-medium text-slate-900">
                  {contract.contract_number ?? "Sem numero"}
                </td>
                <td className="px-4 py-3 text-slate-600">
                  {contract.object ?? "Nao informado"}
                </td>
                <td className="px-4 py-3 text-slate-600">
                  {contract.status ?? "Nao informado"}
                </td>
                <td className="px-4 py-3 font-medium text-slate-900">
                  {currency(contract.total_value)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}
