import { PoliticiansExplorer } from "@/components/PoliticiansExplorer";
import { api, type PaginatedPersonsResponse, type Person } from "@/lib/api";
import { PageHeader } from "@/components/ui/Primitives";

const fallbackPersons: Person[] = [
  {
    id: "mock-person-1",
    full_name: "Maria Silva",
    normalized_name: "maria silva",
    masked_cpf: "***.123.456-**",
    birth_year: 1978,
    data_origin: "demo",
    external_id: "demo-1",
    party_acronym: "MDB",
    state_code: "DF",
    photo_url: null,
    email: "maria.silva@example.local",
    latest_expense_total: "184500.00",
    latest_expense_year: 2025,
    created_at: new Date().toISOString(),
    roles: [
      {
        id: "mock-role-1",
        role_name: "Prefeito",
        jurisdiction_level: "municipal",
        state_code: "DF",
      },
    ],
  },
  {
    id: "mock-person-2",
    full_name: "Joao Pereira",
    normalized_name: "joao pereira",
    masked_cpf: "***.987.654-**",
    birth_year: 1982,
    data_origin: "demo",
    external_id: "demo-2",
    party_acronym: "PL",
    state_code: "SP",
    photo_url: null,
    email: "joao.pereira@example.local",
    latest_expense_total: "127300.00",
    latest_expense_year: 2025,
    created_at: new Date().toISOString(),
    roles: [
      {
        id: "mock-role-2",
        role_name: "Vereador",
        jurisdiction_level: "municipal",
        state_code: "SP",
      },
    ],
  },
];

const fallbackPage: PaginatedPersonsResponse = {
  items: fallbackPersons,
  page: 1,
  limit: 50,
  total: fallbackPersons.length,
  pages: 1,
  has_next: false,
  has_previous: false,
};

async function getPersons(): Promise<{ page: PaginatedPersonsResponse; isFallback: boolean }> {
  try {
    const page = await api.listPersonsPaginated({ page: 1, limit: 50, orderBy: "name" });
    return {
      page: page.items.length ? page : fallbackPage,
      isFallback: page.items.length === 0,
    };
  } catch {
    return { page: fallbackPage, isFallback: true };
  }
}

export default async function PoliticosPage() {
  const { page, isFallback } = await getPersons();

  return (
    <div className="mx-auto max-w-7xl">
      <PageHeader
        description="Busca paginada para consultar agentes publicos sem travar a tela, mesmo com centenas de milhares de registros."
        eyebrow="Cadastro e monitoramento"
        status={{
          label: isFallback ? "Amostra demonstrativa" : `${page.total.toLocaleString("pt-BR")} registros`,
          tone: isFallback ? "warning" : "success",
        }}
        title="Politicos"
      />

      <PoliticiansExplorer initialPage={page} isFallback={isFallback} />
    </div>
  );
}
