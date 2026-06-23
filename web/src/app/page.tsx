import { FileText, ShieldAlert, TrendingUp, Users, WalletCards } from "lucide-react";
import { api, type Contract, type Expense, type Person } from "@/lib/api";
import { BackofficeSettings } from "@/components/BackofficeSettings";
import { CopilotChat } from "@/components/CopilotChat";
import { DashboardIntelligence } from "@/components/DashboardIntelligence";
import { MapSection } from "@/components/MapSection";
import { PoliticoProfile } from "@/components/PoliticoProfile";

type DashboardData = {
  contracts: Contract[];
  expenses: Expense[];
  persons: Person[];
  isFallback: boolean;
};

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

const fallbackExpenses: Expense[] = [
  {
    id: "mock-expense-1",
    amount: "48900.00",
    expense_date: "2026-06-20",
    fiscal_year: 2026,
    description: "Possivel despesa fracionada abaixo do limite configurado",
    state_code: "DF",
  },
  {
    id: "mock-expense-2",
    amount: "320000.00",
    expense_date: "2026-06-19",
    fiscal_year: 2026,
    description: "Concentracao elevada em fornecedor recorrente",
    state_code: "SP",
  },
  {
    id: "mock-expense-3",
    amount: "875000.00",
    expense_date: "2026-06-18",
    fiscal_year: 2026,
    description: "Crescimento anormal em contrato comparavel",
    state_code: "RJ",
  },
];

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

async function getDashboardData(): Promise<DashboardData> {
  try {
    const [contracts, expenses, persons] = await Promise.all([
      api.listContracts(50),
      api.listExpenses(50),
      api.listPersons(50),
    ]);

    return {
      contracts: contracts.length ? contracts : fallbackContracts,
      expenses: expenses.length ? expenses : fallbackExpenses,
      persons: persons.length ? persons : fallbackPersons,
      isFallback: contracts.length === 0 || expenses.length === 0 || persons.length === 0,
    };
  } catch {
    return {
      contracts: fallbackContracts,
      expenses: fallbackExpenses,
      persons: fallbackPersons,
      isFallback: true,
    };
  }
}

function currency(value: string | number | null | undefined) {
  const amount = Number(value ?? 0);
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
    maximumFractionDigits: 0,
  }).format(amount);
}

export default async function Home() {
  const { contracts, expenses, persons, isFallback } = await getDashboardData();
  const totalContracts = contracts.length;
  const totalSpent = expenses.reduce(
    (sum, expense) => sum + Number(expense.amount ?? 0),
    0,
  );
  const criticalAlerts = expenses.filter(
    (expense) => Number(expense.amount) > 250000,
  ).length;
  const monitoredPoliticians = persons.length;
  const topPerson = [...persons].sort(
    (a, b) => Number(b.latest_expense_total ?? 0) - Number(a.latest_expense_total ?? 0),
  )[0];

  return (
    <div className="mx-auto max-w-7xl">
      <div className="mb-8 flex flex-col gap-4 border-b border-slate-200 pb-6 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-sm font-medium text-slate-500">
            Observatorio Nacional de Gastos Publicos
          </p>
          <h2 className="mt-1 text-2xl font-semibold text-slate-950">
            Dashboard Executivo
          </h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
            Visao operacional de contratos, despesas, politicos monitorados e
            alertas priorizados pelo motor de risco.
          </p>
        </div>
        <span className="w-fit rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs font-semibold text-emerald-800">
          {isFallback ? "Aguardando dados reais" : "Dados reais/cacheados"}
        </span>
      </div>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          detail="contratos no recorte atual"
          icon={FileText}
          label="Contratos"
          tone="emerald"
          value={String(totalContracts)}
        />
        <MetricCard
          detail="despesas carregadas no painel"
          icon={WalletCards}
          label="Volume gasto"
          tone="emerald"
          value={currency(totalSpent)}
        />
        <MetricCard
          detail="pessoas com perfil consolidado"
          icon={Users}
          label="Politicos monitorados"
          tone="slate"
          value={String(monitoredPoliticians)}
        />
        <MetricCard
          detail="prioridade alta para auditoria"
          icon={ShieldAlert}
          label="Alertas criticos"
          tone="red"
          value={String(criticalAlerts)}
        />
      </section>

      <section className="mt-4 rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-sm font-medium text-slate-500">Maior gasto parlamentar</p>
            <h3 className="mt-1 text-lg font-semibold text-slate-950">
              {topPerson?.full_name ?? "Sem politico carregado"}
            </h3>
            <p className="mt-1 text-sm text-slate-500">
              {(topPerson?.party_acronym ?? "-")} / {(topPerson?.state_code ?? "-")}
            </p>
          </div>
          <div className="flex items-center gap-3 rounded-md bg-slate-50 px-4 py-3">
            <TrendingUp className="h-5 w-5 text-emerald-700" />
            <span className="text-xl font-semibold text-slate-950">
              {currency(topPerson?.latest_expense_total)}
            </span>
          </div>
        </div>
      </section>

      <MapSection />

      <PoliticoProfile persons={persons} isFallback={isFallback} />

      <div className="mt-6 grid gap-6 xl:grid-cols-[minmax(0,0.9fr)_minmax(360px,1.1fr)]">
        <CopilotChat />
        <BackofficeSettings />
      </div>

      <DashboardIntelligence />
    </div>
  );
}

function MetricCard({
  detail,
  icon: Icon,
  label,
  tone,
  value,
}: {
  detail: string;
  icon: typeof FileText;
  label: string;
  tone: "emerald" | "red" | "slate";
  value: string;
}) {
  const toneClasses = {
    emerald: "bg-emerald-50 text-emerald-700",
    red: "bg-red-50 text-red-700",
    slate: "bg-slate-100 text-slate-700",
  };

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm font-medium text-slate-500">{label}</p>
        <div className={`rounded-md p-2 ${toneClasses[tone]}`}>
          <Icon className="h-5 w-5" />
        </div>
      </div>
      <p className="mt-4 text-2xl font-semibold text-slate-950 md:text-3xl">
        {value}
      </p>
      <p className="mt-1 text-xs text-slate-500">{detail}</p>
    </div>
  );
}
