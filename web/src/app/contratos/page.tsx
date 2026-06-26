import { ContractsExplorer } from "@/components/ContractsExplorer";
import { api, type Contract, type PaginatedContractsResponse } from "@/lib/api";
import { PageHeader } from "@/components/ui/Primitives";

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

const fallbackPage: PaginatedContractsResponse = {
  items: fallbackContracts,
  page: 1,
  limit: 50,
  total: fallbackContracts.length,
  pages: 1,
  has_next: false,
  has_previous: false,
  total_value: fallbackContracts.reduce(
    (sum, contract) => sum + Number(contract.total_value ?? 0),
    0,
  ),
  statuses: [
    { status: "monitorado", label: "monitorado", total: 1 },
    { status: "em analise", label: "em analise", total: 1 },
  ],
};

async function getContracts(): Promise<{ page: PaginatedContractsResponse; isFallback: boolean }> {
  try {
    const page = await api.listContractsPaginated({ page: 1, limit: 50 });
    return {
      page: page.items.length ? page : fallbackPage,
      isFallback: page.items.length === 0,
    };
  } catch {
    return { page: fallbackPage, isFallback: true };
  }
}

export default async function ContratosPage() {
  const { page, isFallback } = await getContracts();

  return (
    <div className="mx-auto max-w-7xl">
      <PageHeader
        description="Consulta paginada de contratos, fornecedores, orgaos e valores para auditoria."
        eyebrow="Contratos publicos monitorados"
        status={{
          label: isFallback ? "Dados demonstrativos" : `${page.total.toLocaleString("pt-BR")} contratos`,
          tone: isFallback ? "warning" : "success",
        }}
        title="Contratos"
      />

      <ContractsExplorer initialPage={page} isFallback={isFallback} />
    </div>
  );
}
