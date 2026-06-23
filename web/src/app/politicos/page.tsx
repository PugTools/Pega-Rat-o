import { PoliticoProfile } from "@/components/PoliticoProfile";
import { api, type Person } from "@/lib/api";

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
  },
];

async function getPersons(): Promise<{ persons: Person[]; isFallback: boolean }> {
  try {
    const persons = await api.listPersons(100);
    return {
      persons: persons.length ? persons : fallbackPersons,
      isFallback: persons.length === 0,
    };
  } catch {
    return { persons: fallbackPersons, isFallback: true };
  }
}

export default async function PoliticosPage() {
  const { persons, isFallback } = await getPersons();

  return (
    <div className="mx-auto max-w-7xl">
      <div className="mb-6">
        <p className="text-sm font-medium text-slate-500">
          Cadastro e monitoramento
        </p>
        <h2 className="mt-1 text-2xl font-semibold text-slate-950">Politicos</h2>
      </div>

      <PoliticoProfile persons={persons} isFallback={isFallback} />
    </div>
  );
}
