import Link from "next/link";
import {
  Bell,
  Building2,
  FileText,
  MapPinned,
  MessageSquareText,
  ShieldAlert,
  TrendingUp,
  Users,
  WalletCards,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { api, type Contract, type Expense, type Person } from "@/lib/api";
import { CopilotChat } from "@/components/CopilotChat";
import { DashboardIntelligence } from "@/components/DashboardIntelligence";
import { MapSection } from "@/components/MapSection";
import { PoliticoProfile } from "@/components/PoliticoProfile";
import {
  MetricTile,
  ModuleCard,
  PageHeader,
  StatusCallout,
} from "@/components/ui/Primitives";

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
      <PageHeader
        description="Uma visao curta do que exige atencao agora: volume monitorado, pessoas, contratos e alertas priorizados."
        eyebrow="Observatorio Nacional de Gastos Publicos"
        status={{
          label: isFallback ? "Dados demonstrativos" : "Dados reais/cacheados",
          tone: isFallback ? "warning" : "success",
        }}
        title="Dashboard Executivo"
      />

      {isFallback ? (
        <div className="mb-6">
          <StatusCallout
            message="A API nao retornou todos os dados esperados, entao esta tela exibe uma amostra segura para manter a navegacao funcionando. Use o Admin para verificar a ingestao e os logs."
            title="Painel em modo demonstrativo"
            tone="warning"
          />
        </div>
      ) : null}

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricTile
          detail="contratos no recorte atual"
          icon={FileText}
          label="Contratos"
          tone="success"
          value={String(totalContracts)}
        />
        <MetricTile
          detail="despesas carregadas no painel"
          icon={WalletCards}
          label="Volume gasto"
          tone="success"
          value={currency(totalSpent)}
        />
        <MetricTile
          detail="pessoas com perfil consolidado"
          icon={Users}
          label="Politicos monitorados"
          tone="neutral"
          value={String(monitoredPoliticians)}
        />
        <MetricTile
          detail="prioridade alta para auditoria"
          icon={ShieldAlert}
          label="Alertas criticos"
          tone="danger"
          value={String(criticalAlerts)}
        />
      </section>

      <div className="mt-6 grid gap-4 xl:grid-cols-[minmax(0,0.95fr)_minmax(320px,0.65fr)]">
        <ModuleCard
          description="Atalhos para as tarefas mais usadas, sem esconder as funcoes em menus."
          icon={TrendingUp}
          title="Modulos principais"
        >
          <div className="grid gap-3 sm:grid-cols-2">
            <ModuleShortcut
              description="Buscar por nome, cargo, UF e abrir relatorio individual."
              href="/politicos"
              icon={Users}
              title="Investigar politicos"
            />
            <ModuleShortcut
              description="Auditar valores, fornecedores, orgaos e objetos contratados."
              href="/contratos"
              icon={Building2}
              title="Analisar contratos"
            />
            <ModuleShortcut
              description="Filtrar riscos por categoria, severidade e status."
              href="/alertas"
              icon={Bell}
              title="Priorizar alertas"
            />
            <ModuleShortcut
              description="Disparar ingestao, acompanhar logs e ativar fontes."
              href="/admin"
              icon={ShieldAlert}
              title="Operar sistema"
            />
          </div>
        </ModuleCard>

        <ModuleCard
          description="Entidade com maior volume no recorte carregado."
          icon={TrendingUp}
          title="Ponto de atencao"
        >
          <div>
            <p className="text-sm font-medium text-slate-500 dark:text-slate-400">
              Maior gasto parlamentar
            </p>
            <h3 className="mt-1 text-lg font-semibold text-slate-950 dark:text-white">
              {topPerson?.full_name ?? "Sem politico carregado"}
            </h3>
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
              {(topPerson?.party_acronym ?? "-")} / {(topPerson?.state_code ?? "-")}
            </p>
            <div className="mt-4 flex items-center gap-3 rounded-md bg-slate-50 px-4 py-3 dark:bg-slate-900">
              <TrendingUp className="h-5 w-5 text-emerald-700" />
              <span className="text-xl font-semibold text-slate-950 dark:text-white">
                {currency(topPerson?.latest_expense_total)}
              </span>
            </div>
          </div>
        </ModuleCard>
      </div>

      <div className="mt-6">
        <ModuleCard
          description="Distribuicao visual para localizar concentracoes por UF."
          icon={MapPinned}
          title="Mapa nacional"
        >
          <MapSection />
        </ModuleCard>
      </div>

      <PoliticoProfile persons={persons} isFallback={isFallback} />

      <div className="mt-6">
        <ModuleCard
          description="Pergunte sobre alertas, contratos, fornecedores e proximas linhas de investigacao."
          icon={MessageSquareText}
          title="Copiloto investigativo"
        >
          <CopilotChat />
        </ModuleCard>
      </div>

      <DashboardIntelligence />
    </div>
  );
}

function ModuleShortcut({
  description,
  href,
  icon: Icon,
  title,
}: {
  description: string;
  href: string;
  icon: LucideIcon;
  title: string;
}) {
  return (
    <Link
      className="group rounded-lg border border-slate-200 p-4 transition hover:border-slate-300 hover:bg-slate-50 dark:border-slate-800 dark:hover:border-slate-700 dark:hover:bg-slate-900"
      href={href}
    >
      <div className="flex items-center gap-3">
        <span className="rounded-md bg-slate-100 p-2 text-slate-700 group-hover:bg-white dark:bg-slate-800 dark:text-slate-200 dark:group-hover:bg-slate-950">
          <Icon className="h-4 w-4" />
        </span>
        <h4 className="font-semibold text-slate-950 dark:text-white">{title}</h4>
      </div>
      <p className="mt-3 text-sm leading-6 text-slate-500 dark:text-slate-400">
        {description}
      </p>
    </Link>
  );
}
