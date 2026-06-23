const rawApiBaseUrl = "https://studious-waffle-7vp46vqvq57pfggw-8000.app.github.dev";
const API_BASE_URL = normalizeApiBaseUrl(rawApiBaseUrl);
const MOCK_AUTH_TOKEN = "mock-token-ongp";

export type Company = {
  id: string;
  legal_name: string;
  trade_name?: string | null;
  cnpj: string;
  state_code?: string | null;
  created_at: string;
};

export type Person = {
  id: string;
  full_name: string;
  normalized_name: string;
  masked_cpf?: string | null;
  birth_year?: number | null;
  data_origin?: string | null;
  external_id?: string | null;
  party_acronym?: string | null;
  state_code?: string | null;
  photo_url?: string | null;
  email?: string | null;
  latest_expense_total?: string | number | null;
  latest_expense_year?: number | null;
  created_at: string;
};

export type Contract = {
  id: string;
  contract_number?: string | null;
  process_number?: string | null;
  supplier_company_id?: string | null;
  organization_id?: string | null;
  object?: string | null;
  status?: string | null;
  total_value?: string | number | null;
  created_at: string;
};

export type Expense = {
  id: string;
  amount: string | number;
  expense_date: string;
  fiscal_year: number;
  organization_id?: string | null;
  company_id?: string | null;
  person_id?: string | null;
  description?: string | null;
  state_code?: string | null;
};

export type RiskAlert = {
  id: string;
  entity_type: string;
  entity_id: string;
  alert_type: string;
  severity: "critical" | "high" | "medium" | "low" | string;
  score: string | number;
  title: string;
  explanation: string;
  evidence: Record<string, unknown>;
  status: string;
  created_at: string;
};

export type GraphNode = {
  id: string;
  label: string;
  properties: Record<string, unknown>;
};

export type GraphEdge = {
  id: string;
  source: string;
  target: string;
  type: string;
  properties: Record<string, unknown>;
};

export type EntityGraph = {
  nodes: GraphNode[];
  edges: GraphEdge[];
};

export type CopilotResponse = {
  answer: string;
  sources: unknown;
  mode: string;
  requested_by?: string;
};

export type RiskSettings = {
  expense_fragmentation_legal_limit: string;
  expense_fragmentation_minimum_count: number;
  expense_fragmentation_window_days: number;
  supplier_concentration_threshold: string;
  supplier_concentration_minimum_total_amount: string;
  abnormal_growth_threshold: string;
  abnormal_growth_minimum_history: number;
};

export type ListPersonsParams = {
  limit?: number;
  party?: string;
  stateCode?: string;
  name?: string;
  orderBy?: "expense_total" | "name" | "party" | "state";
};

export type PoliticalIngestionResult = {
  status: string;
  politicians_found?: number;
  politicians_saved?: number;
  expenses_found?: number;
  expenses_saved?: number;
  expense_year?: number;
  source_counts?: Record<string, number>;
  errors?: string[];
  job?: string;
  task_id?: string;
  requested_by?: string;
  params?: Record<string, unknown>;
};

type ApiErrorPayload = {
  detail?: unknown;
  message?: unknown;
};

function normalizeApiBaseUrl(value: string): string {
  const trimmed = value.replace(/\/$/, "");
  if (trimmed.endsWith("/api/v1") || trimmed.endsWith("/api/backend")) {
    return trimmed;
  }
  return `${trimmed}/api/v1`;
}

function getAuthToken(): string {
  if (typeof window === "undefined") {
    return process.env.ONGP_API_TOKEN ?? MOCK_AUTH_TOKEN;
  }

  return window.localStorage.getItem("ongp_token") || MOCK_AUTH_TOKEN;
}

function normalizePerson(item: Person): Person {
  return {
    ...item,
    full_name: item.full_name ?? "",
    normalized_name: item.normalized_name ?? item.full_name?.toLowerCase() ?? "",
    masked_cpf: item.masked_cpf ?? null,
    birth_year: item.birth_year ?? null,
    data_origin: item.data_origin ?? null,
    external_id: item.external_id ?? null,
    party_acronym: item.party_acronym ?? null,
    state_code: item.state_code ?? null,
    photo_url: item.photo_url ?? null,
    email: item.email ?? null,
    latest_expense_total: item.latest_expense_total ?? null,
    latest_expense_year: item.latest_expense_year ?? null,
  };
}

async function parseErrorPayload(response: Response): Promise<ApiErrorPayload | null> {
  try {
    return (await response.json()) as ApiErrorPayload;
  } catch {
    return null;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getAuthToken();

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      ...(init?.headers ?? {}),
    },
    cache: "no-store",
  });

  if (!response.ok) {
    const errorPayload = await parseErrorPayload(response);
    const detail = errorPayload?.detail ?? errorPayload?.message;
    throw new Error(
      detail
        ? `API request failed: ${response.status} ${JSON.stringify(detail)}`
        : `API request failed: ${response.status} ${response.statusText}`,
    );
  }

  return (await response.json()) as T;
}

export const api = {
  listCompanies: (limit = 50) => request<Company[]>(`/companies?limit=${limit}`),
  listPersons: async (params: number | ListPersonsParams = 50) => {
    const resolvedParams =
      typeof params === "number" ? { limit: params } : { limit: 50, ...params };
    const searchParams = new URLSearchParams({
      limit: String(resolvedParams.limit ?? 50),
      order_by: resolvedParams.orderBy ?? "expense_total",
    });
    if (resolvedParams.party) {
      searchParams.set("party", resolvedParams.party);
    }
    if (resolvedParams.stateCode) {
      searchParams.set("state_code", resolvedParams.stateCode);
    }
    if (resolvedParams.name) {
      searchParams.set("name", resolvedParams.name);
    }

    const persons = await request<Person[]>(`/persons?${searchParams.toString()}`);
    return persons.map(normalizePerson);
  },
  listContracts: (limit = 50) => request<Contract[]>(`/contracts?limit=${limit}`),
  listExpenses: (limit = 50) => request<Expense[]>(`/expenses?limit=${limit}`),
  listAlerts: (limit = 50) => request<RiskAlert[]>(`/alerts?limit=${limit}`),
  askCopilot: (question: string) =>
    request<CopilotResponse>("/copilot/chat", {
      method: "POST",
      body: JSON.stringify({ question }),
    }),
  getRiskSettings: () => request<RiskSettings>("/backoffice/risk-settings"),
  updateRiskSettings: (payload: Partial<RiskSettings>) =>
    request<RiskSettings>("/backoffice/risk-settings", {
      method: "PUT",
      body: JSON.stringify(payload),
    }),
  runPoliticalIngestion: (params: {
    limit?: number;
    page?: number;
    camaraPages?: number;
    year?: number;
    expensesPerPolitician?: number;
    includeSenate?: boolean;
    senateExpenses?: boolean;
  } = {}) => {
    const searchParams = new URLSearchParams({
      itens: String(params.limit ?? 100),
      pagina: String(params.page ?? 1),
      paginas_camara: String(params.camaraPages ?? 1),
      despesas_por_politico: String(params.expensesPerPolitician ?? 100),
      incluir_senado: String(params.includeSenate ?? true),
      despesas_senado: String(params.senateExpenses ?? false),
    });
    if (params.year) {
      searchParams.set("ano", String(params.year));
    }
    return request<PoliticalIngestionResult>(
      `/ingestion/politicians/run?${searchParams.toString()}`,
      { method: "POST" },
    );
  },
  getEntityGraph: (entityType: string, entityId: string) =>
    request<EntityGraph>(
      `/graphs/entity/${encodeURIComponent(entityType)}/${encodeURIComponent(entityId)}`,
    ),
};