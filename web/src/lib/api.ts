const rawApiBaseUrl =
  typeof window === "undefined"
    ? process.env.INTERNAL_API_BASE_URL ??
      absoluteUrlOrUndefined(process.env.NEXT_PUBLIC_API_BASE_URL) ??
      "http://127.0.0.1:8000/api/v1"
    : process.env.NEXT_PUBLIC_API_BASE_URL ?? "/api/backend";
const API_BASE_URL = normalizeApiBaseUrl(rawApiBaseUrl);
const MOCK_AUTH_TOKEN = "mock-token-ongp";

export type Company = {
  id: string;
  legal_name: string;
  trade_name?: string | null;
  cnpj: string;
  cnae?: string | null;
  city?: string | null;
  state_code?: string | null;
  registration_status?: string | null;
  created_at: string;
};

export type PublicRole = {
  id: string;
  person_id?: string;
  role_name: string;
  branch?: string | null;
  jurisdiction_level?: string | null;
  state_code?: string | null;
  municipality_code?: string | null;
  party_acronym?: string | null;
  organization_id?: string | null;
  start_date?: string | null;
  end_date?: string | null;
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
  declared_assets_value?: string | number | null;
  declared_assets_year?: number | null;
  salary_reference_value?: string | number | null;
  salary_reference_year?: number | null;
  salary_reference_source?: string | null;
  asset_salary_ratio?: string | number | null;
  created_at: string;
  roles?: PublicRole[];
};

export type PersonDetail = Person & {
  recent_expenses: Expense[];
  expense_total?: string | number | null;
};

export type Organization = {
  id: string;
  name: string;
  normalized_name: string;
  cnpj?: string | null;
  organization_type?: string | null;
  jurisdiction_level?: string | null;
  state_code?: string | null;
  municipality_code?: string | null;
};

export type Contract = {
  id: string;
  contract_number?: string | null;
  process_number?: string | null;
  supplier_company_id?: string | null;
  organization_id?: string | null;
  object?: string | null;
  modality?: string | null;
  status?: string | null;
  signed_at?: string | null;
  starts_at?: string | null;
  ends_at?: string | null;
  total_value?: string | number | null;
  created_at: string;
  supplier?: Company | null;
  organization?: Organization | null;
};

export type ContractDetail = Contract & {
  expenses: Expense[];
  expense_total?: string | number | null;
};

export type Expense = {
  id: string;
  organization_id?: string | null;
  company_id?: string | null;
  contract_id?: string | null;
  person_id?: string | null;
  expense_type?: string | null;
  description?: string | null;
  commitment_number?: string | null;
  liquidation_number?: string | null;
  payment_number?: string | null;
  amount: string | number;
  expense_date: string;
  fiscal_year: number;
  state_code?: string | null;
  municipality_code?: string | null;
  source_id?: string | null;
  raw_document_id?: string | null;
  supplier_company_id?: string | null;
  supplier_name?: string | null;
  supplier_cnpj?: string | null;
  document_url?: string | null;
  created_at?: string;
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
  source?: string;
};

export type SearchResult = {
  id: string;
  entity_type: "person" | "company" | "contract" | "organization" | string;
  label: string;
  subtitle?: string | null;
  href: string;
  score?: number | string | null;
  source?: Record<string, unknown>;
};

export type SearchResponse = {
  query: string;
  total: number;
  items: SearchResult[];
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
  roleName?: string;
  jurisdictionLevel?: string;
  municipalityCode?: string;
  orderBy?: "expense_total" | "name" | "party" | "state";
};

export type ListContractsParams = {
  limit?: number;
  q?: string;
  status?: string;
  organizationId?: string;
  supplierCompanyId?: string;
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

function absoluteUrlOrUndefined(value: string | undefined): string | undefined {
  if (!value) {
    return undefined;
  }
  return value.startsWith("http://") || value.startsWith("https://")
    ? value
    : undefined;
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
    declared_assets_value: item.declared_assets_value ?? null,
    declared_assets_year: item.declared_assets_year ?? null,
    salary_reference_value: item.salary_reference_value ?? null,
    salary_reference_year: item.salary_reference_year ?? null,
    salary_reference_source: item.salary_reference_source ?? null,
    asset_salary_ratio: item.asset_salary_ratio ?? null,
    roles: item.roles ?? [],
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
    signal: init?.signal,
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
  getCompany: (id: string) => request<Company>(`/companies/${id}`),
  search: (query: string, limit = 8, signal?: AbortSignal) => {
    const params = new URLSearchParams({ q: query, limit: String(limit) });
    return request<SearchResponse>(`/search?${params.toString()}`, { signal });
  },
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
    if (resolvedParams.roleName) {
      searchParams.set("role_name", resolvedParams.roleName);
    }
    if (resolvedParams.jurisdictionLevel) {
      searchParams.set("jurisdiction_level", resolvedParams.jurisdictionLevel);
    }
    if (resolvedParams.municipalityCode) {
      searchParams.set("municipality_code", resolvedParams.municipalityCode);
    }

    const persons = await request<Person[]>(`/persons?${searchParams.toString()}`);
    return persons.map(normalizePerson);
  },
  getPerson: async (id: string) => normalizePerson(await request<PersonDetail>(`/persons/${id}`)) as PersonDetail,
  listContracts: (params: number | ListContractsParams = 50) => {
    const resolvedParams =
      typeof params === "number" ? { limit: params } : { limit: 50, ...params };
    const searchParams = new URLSearchParams({
      limit: String(resolvedParams.limit ?? 50),
    });
    if (resolvedParams.q) {
      searchParams.set("q", resolvedParams.q);
    }
    if (resolvedParams.status) {
      searchParams.set("status", resolvedParams.status);
    }
    if (resolvedParams.organizationId) {
      searchParams.set("organization_id", resolvedParams.organizationId);
    }
    if (resolvedParams.supplierCompanyId) {
      searchParams.set("supplier_company_id", resolvedParams.supplierCompanyId);
    }
    return request<Contract[]>(`/contracts?${searchParams.toString()}`);
  },
  getContract: (id: string) => request<ContractDetail>(`/contracts/${id}`),
  listExpenses: (limit = 50) => request<Expense[]>(`/expenses?limit=${limit}`),
  listAlerts: (limit = 50) => request<RiskAlert[]>(`/alerts?limit=${limit}`),
  listEntityAlerts: (entityType: string, entityId: string, limit = 50) =>
    request<RiskAlert[]>(
      `/alerts/entity/${encodeURIComponent(entityType)}/${encodeURIComponent(entityId)}?limit=${limit}`,
    ),
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
    includeTse?: boolean;
    tseYears?: string;
    tseLimitPerRole?: number;
    tseStateCode?: string;
    tseAssets?: boolean;
    syncGraph?: boolean;
  } = {}) => {
    const searchParams = new URLSearchParams({
      itens: String(params.limit ?? 100),
      pagina: String(params.page ?? 1),
      paginas_camara: String(params.camaraPages ?? 6),
      despesas_por_politico: String(params.expensesPerPolitician ?? 5),
      incluir_senado: String(params.includeSenate ?? true),
      despesas_senado: String(params.senateExpenses ?? false),
      incluir_tse: String(params.includeTse ?? true),
      anos_tse: params.tseYears ?? "2024,2022",
      limite_tse_por_cargo: String(params.tseLimitPerRole ?? 50),
      patrimonio_tse: String(params.tseAssets ?? false),
      sync_graph: String(params.syncGraph ?? false),
    });
    if (params.year) {
      searchParams.set("ano", String(params.year));
    }
    if (params.tseStateCode) {
      searchParams.set("uf_tse", params.tseStateCode);
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
