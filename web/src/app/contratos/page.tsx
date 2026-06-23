import { ContractsExplorer } from "@/components/ContractsExplorer";
import { api, type Contract } from "@/lib/api";

const fallbackContracts: Contract[] = [
  {
    id: "mock-contract-1",
    contract_number: "CT-2026-001",
    object: "Servico continuado de tecnologia",
    status: "monitorado",
    total_value: "1250000.00",
    created_at: new Date().toISOString(),
    supplier: {
      id: "mock-company-1",
      legal_name: "Fornecedor Tecnologia Ltda",
      cnpj: "00.000.000/0001-00",
      created_at: new Date().toISOString(),
    },
    organization: {
      id: "mock-org-1",
      name: "Orgao demonstrativo",
      normalized_name: "orgao demonstrativo",
    },
  },
  {
    id: "mock-contract-2",
    contract_number: "CT-2026-002",
    object: "Fornecimento de insumos administrativos",
    status: "em analise",
    total_value: "420000.00",
    created_at: new Date().toISOString(),
    supplier: {
      id: "mock-company-2",
      legal_name: "Insumos Publicos SA",
      cnpj: "11.111.111/0001-11",
      created_at: new Date().toISOString(),
    },
    organization: {
      id: "mock-org-2",
      name: "Secretaria demonstrativa",
      normalized_name: "secretaria demonstrativa",
    },
  },
];

async function getContracts(): Promise<{ contracts: Contract[]; isFallback: boolean }> {
  try {
    const contracts = await api.listContracts({ limit: 1000 });
    return {
      contracts: contracts.length ? contracts : fallbackContracts,
      isFallback: contracts.length === 0,
    };
  } catch {
    return { contracts: fallbackContracts, isFallback: true };
  }
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

      <ContractsExplorer contracts={contracts} isFallback={isFallback} />
    </div>
  );
}
