"use client";

import {
  Activity,
  AlertCircle,
  CheckCircle2,
  Clock3,
  Database,
  Flame,
  Loader2,
  Play,
  Power,
  Radar,
  RefreshCw,
  Search,
  Server,
  Settings2,
  Terminal,
  Wifi,
  WifiOff,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { AdminCommandCenter } from "@/components/admin/AdminCommandCenter";
import { BackofficeSettings } from "@/components/BackofficeSettings";
import { PageHeader } from "@/components/ui/Primitives";

const API_BASE_URL = "/api/backend";

type AdminLog = {
  id: string;
  status: "success" | "warning" | "error" | "running" | string;
  title: string;
  message: string;
  technical_details: unknown;
  created_at: string;
};

type HealthService = {
  name: string;
  status: "ok" | "warning" | "error" | string;
  message: string;
  technical_details?: unknown;
};

type SystemHealth = {
  status: "success" | "degraded" | "error" | string;
  checked_at: string;
  services: HealthService[];
};

type ConnectionState = {
  status: "checking" | "online" | "degraded" | "offline";
  message: string;
  checkedAt?: string;
  technicalDetails?: unknown;
};

type ActionKey = "massive" | "politicians" | "politiciansFull" | "daily";

type AdminActionResponse = {
  status: string;
  job?: string;
  task_id?: string;
  politicians_found?: number;
  politicians_saved?: number;
  expenses_found?: number;
  expenses_saved?: number;
  contracts_found?: number;
  contracts_saved?: number;
  rows_collected?: number;
  nodes_synced?: number;
  sources_processed?: number;
  source_key?: string;
  source_counts?: Record<string, number>;
  message?: string;
  errors?: string[];
};

type IngestionSourceOption = {
  key: string;
  name: string;
  enabled: boolean;
  source_type: string;
  destination_model: string;
  base_url: string;
  category: string;
  auth_env?: string | null;
  auth_header?: string | null;
  requires_token: boolean;
  has_auth_token: boolean;
  can_enable: boolean;
  activation_notes: string[];
  endpoints: Record<string, string>;
};

type ActivationHelp = {
  registry_path: string;
  env_file: string;
  env_example: string;
  github_secrets: string[];
  steps: string[];
  production_note: string;
};

type IngestionSourcesResponse = {
  status: string;
  total: number;
  enabled: number;
  items: IngestionSourceOption[];
  activation_help: ActivationHelp;
};

type SourceActivationResponse = {
  status: string;
  message: string;
  source: IngestionSourceOption;
  activation_help: ActivationHelp;
};

class ApiRequestError extends Error {
  status?: number;
  payload?: unknown;

  constructor(message: string, status?: number, payload?: unknown) {
    super(message);
    this.name = "ApiRequestError";
    this.status = status;
    this.payload = payload;
  }
}

export default function AdminPage() {
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [logs, setLogs] = useState<AdminLog[]>([]);
  const [connection, setConnection] = useState<ConnectionState>({
    status: "checking",
    message: "Verificando conexao com a API...",
  });
  const [loading, setLoading] = useState(true);
  const [pollingEnabled, setPollingEnabled] = useState(true);
  const [expandedLogId, setExpandedLogId] = useState<string | null>(null);
  const [runningAction, setRunningAction] = useState<ActionKey | null>(null);
  const [lastResult, setLastResult] = useState<AdminActionResponse | null>(null);
  const [lastActionError, setLastActionError] = useState<unknown>(null);
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [sources, setSources] = useState<IngestionSourceOption[]>([]);
  const [selectedSourceKey, setSelectedSourceKey] = useState("all");
  const [sourcesLoading, setSourcesLoading] = useState(true);
  const [sourcesError, setSourcesError] = useState<string | null>(null);
  const [activationHelp, setActivationHelp] = useState<ActivationHelp | null>(null);
  const [sourceStatusFilter, setSourceStatusFilter] = useState<"all" | "enabled" | "disabled">("all");
  const [sourceSearch, setSourceSearch] = useState("");
  const [updatingSourceKey, setUpdatingSourceKey] = useState<string | null>(null);

  const servicesByName = useMemo(() => {
    const entries: Array<[string, HealthService]> =
      health?.services.map((service) => [service.name, service]) ?? [];
    return Object.fromEntries(entries) as Record<string, HealthService | undefined>;
  }, [health]);

  const activeTasks = useMemo(
    () => logs.filter((log) => log.status === "running").length,
    [logs],
  );
  const recentErrors = useMemo(
    () => logs.filter((log) => log.status === "error" || log.status === "warning").length,
    [logs],
  );
  const sourceStats = useMemo(() => {
    const realSources = sources.filter((source) => source.key !== "all");
    return {
      total: realSources.length,
      enabled: realSources.filter((source) => source.enabled).length,
      disabled: realSources.filter((source) => !source.enabled).length,
    };
  }, [sources]);

  const loadSources = useCallback(async () => {
    setSourcesLoading(true);
    setSourcesError(null);
    try {
      const payload = await adminRequest<IngestionSourcesResponse>(
        "/admin/ingestion/sources",
        undefined,
        10000,
      );
      const items = payload.items ?? [];
      setSources(items);
      setActivationHelp(payload.activation_help ?? null);
      setSelectedSourceKey((current) =>
        items.some((source) => source.key === current && source.enabled)
          ? current
          : "all",
      );
    } catch (error) {
      setSourcesError(humanErrorMessage(error));
      setSources([
        {
          key: "all",
          name: "Todas as fontes habilitadas",
          enabled: true,
          source_type: "batch",
          destination_model: "mixed",
          base_url: "sources_registry.json",
          category: "operacional",
          requires_token: false,
          has_auth_token: true,
          can_enable: false,
          activation_notes: ["Fallback local enquanto o backend nao respondeu."],
          endpoints: {},
        },
      ]);
      setSelectedSourceKey("all");
    } finally {
      setSourcesLoading(false);
    }
  }, []);

  const refreshAll = useCallback(async () => {
    setLoading(true);
    setConnection((current) => ({
      ...current,
      status: current.status === "offline" ? "checking" : current.status,
      message:
        current.status === "offline"
          ? "Tentando reconectar com a API..."
          : current.message,
    }));

    try {
      const healthPayload = await adminRequest<SystemHealth>(
        "/admin/system-health",
        undefined,
        8000,
      );
      setHealth(healthPayload);
      setConnection(connectionFromHealth(healthPayload));
    } catch (error) {
      setHealth(null);
      setLogs([frontendErrorLog(error)]);
      setConnection({
        status: "offline",
        message: humanErrorMessage(error),
        checkedAt: new Date().toISOString(),
        technicalDetails: serializeError(error),
      });
      setLoading(false);
      return;
    }

    try {
      const logsPayload = await adminRequest<{ logs: AdminLog[] }>(
        "/admin/system-logs",
        undefined,
        10000,
      );
      setLogs(logsPayload.logs ?? []);
    } catch (error) {
      setLogs([frontendErrorLog(error)]);
      setConnection((current) => ({
        ...current,
        status: current.status === "online" ? "degraded" : current.status,
        message: `API respondeu, mas os logs falharam: ${humanErrorMessage(error)}`,
        technicalDetails: serializeError(error),
      }));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshAll();
  }, [refreshAll]);

  useEffect(() => {
    loadSources();
  }, [loadSources]);

  useEffect(() => {
    if (!pollingEnabled) {
      return;
    }

    const interval = window.setInterval(refreshAll, 10000);
    return () => window.clearInterval(interval);
  }, [pollingEnabled, refreshAll]);

  async function runAction(action: ActionKey) {
    setRunningAction(action);
    setLastActionError(null);

    try {
      const payload = await adminRequest<AdminActionResponse>(
        ingestionPath(action),
        action === "massive"
          ? {
              method: "POST",
              body: JSON.stringify({ source_key: selectedSourceKey }),
            }
          : { method: "POST" },
        15000,
      );
      setLastResult(payload);
      if (action === "massive") {
        setToastMessage("Os robos de coleta foram iniciados em segundo plano.");
        window.setTimeout(() => setToastMessage(null), 6000);
      }
      await refreshAll();
      window.setTimeout(refreshAll, 2500);
    } catch (error) {
      setLastActionError(error);
      setLogs((current) => [frontendErrorLog(error, "Falha ao disparar tarefa"), ...current]);
    } finally {
      setRunningAction(null);
    }
  }

  async function toggleSource(source: IngestionSourceOption) {
    setUpdatingSourceKey(source.key);
    setLastActionError(null);
    try {
      const payload = await adminRequest<SourceActivationResponse>(
        `/admin/ingestion/sources/${encodeURIComponent(source.key)}`,
        {
          method: "PATCH",
          body: JSON.stringify({ enabled: !source.enabled }),
        },
        10000,
      );
      setSources((current) =>
        current.map((item) =>
          item.key === payload.source.key ? payload.source : item,
        ),
      );
      setActivationHelp(payload.activation_help ?? activationHelp);
      if (!payload.source.enabled && selectedSourceKey === payload.source.key) {
        setSelectedSourceKey("all");
      }
      setToastMessage(payload.message);
      window.setTimeout(() => setToastMessage(null), 6000);
      await refreshAll();
    } catch (error) {
      setLastActionError(error);
      setLogs((current) => [frontendErrorLog(error, "Falha ao alterar fonte"), ...current]);
    } finally {
      setUpdatingSourceKey(null);
    }
  }

  const actionsDisabled = connection.status === "offline" || runningAction !== null;

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <PageHeader
        actions={<ConnectionBadge connection={connection} loading={loading} />}
        description="Controle de ingestao, fontes, workers, logs e calibragem. Cada modulo mostra o estado operacional e a proxima acao possivel."
        eyebrow="Backoffice operacional"
        title="Administracao do Sistema"
      />

      <OperationalHud
        activeTasks={activeTasks}
        connection={connection}
        lastChecked={health?.checked_at ?? connection.checkedAt}
        recentErrors={recentErrors}
        servicesByName={servicesByName}
      />

      <AdminCommandCenter />

      {lastActionError ? <ActionError error={lastActionError} /> : null}
      {toastMessage ? <ToastSuccess message={toastMessage} /> : null}
      {lastResult ? <LastResultCard result={lastResult} /> : null}

      <MassiveIngestionPanel
        busy={runningAction === "massive"}
        disabled={actionsDisabled}
        selectedSourceKey={selectedSourceKey}
        sources={sources}
        sourcesError={sourcesError}
        sourcesLoading={sourcesLoading}
        onSelectSource={setSelectedSourceKey}
        onRun={() => runAction("massive")}
      />

      <SourcesActivationPanel
        activationHelp={activationHelp}
        filter={sourceStatusFilter}
        onFilterChange={setSourceStatusFilter}
        onRefresh={loadSources}
        onSearchChange={setSourceSearch}
        onToggleSource={toggleSource}
        search={sourceSearch}
        sources={sources}
        sourcesError={sourcesError}
        sourcesLoading={sourcesLoading}
        stats={sourceStats}
        updatingSourceKey={updatingSourceKey}
      />

      <section className="grid gap-4 lg:grid-cols-3">
        <ActionCard
          busy={runningAction === "politicians"}
          disabled={actionsDisabled}
          expected="Retorno imediato; coleta em fila."
          description="Carga rapida para popular a tela de politicos. Salva nomes, cargos, partidos e UF; enriquecimentos continuam no worker."
          onRun={() => runAction("politicians")}
          title="Atualizar politicos ativos"
        />
        <ActionCard
          busy={runningAction === "politiciansFull"}
          disabled={actionsDisabled}
          expected="Pode levar varios minutos."
          description="Carga pesada com TSE nacional, despesas parlamentares e patrimonio declarado quando a fonte permitir."
          onRun={() => runAction("politiciansFull")}
          title="Carga nacional completa"
        />
        <ActionCard
          busy={runningAction === "daily"}
          disabled={actionsDisabled}
          expected="Depende da CGU/ComprasGov."
          description="Dispara a coleta geral para contratos e despesas oficiais."
          onRun={() => runAction("daily")}
          title="Executar ingestao geral"
        />
      </section>

      <BackofficeSettings />

      <section className="rounded-lg border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-950">
        <div className="flex flex-col gap-3 border-b border-slate-200 px-5 py-4 dark:border-slate-800 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h3 className="text-base font-semibold text-slate-950 dark:text-white">
              Monitor de Logs
            </h3>
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
              Auto-refresh {pollingEnabled ? "ligado" : "pausado"} a cada 10 segundos
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              className="inline-flex items-center gap-2 rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800"
              onClick={() => setPollingEnabled((value) => !value)}
              type="button"
            >
              <Clock3 className="h-4 w-4" />
              {pollingEnabled ? "Pausar" : "Retomar"}
            </button>
            <button
              className="inline-flex items-center gap-2 rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800"
              disabled={loading}
              onClick={refreshAll}
              type="button"
            >
              <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
              Recarregar
            </button>
          </div>
        </div>

        <div className="divide-y divide-slate-100 dark:divide-slate-800">
          {loading && logs.length === 0 ? (
            <LogSkeleton />
          ) : (
            logs.map((log) => (
              <LogRow
                expanded={expandedLogId === log.id}
                key={log.id}
                log={log}
                onToggle={() =>
                  setExpandedLogId((current) => (current === log.id ? null : log.id))
                }
              />
            ))
          )}
        </div>
      </section>
    </div>
  );
}

function MassiveIngestionPanel({
  busy,
  disabled,
  selectedSourceKey,
  sources,
  sourcesError,
  sourcesLoading,
  onSelectSource,
  onRun,
}: {
  busy: boolean;
  disabled: boolean;
  selectedSourceKey: string;
  sources: IngestionSourceOption[];
  sourcesError: string | null;
  sourcesLoading: boolean;
  onSelectSource: (sourceKey: string) => void;
  onRun: () => void;
}) {
  const enabledCount = sources.filter((source) => source.enabled && source.key !== "all").length;
  const sourcesForSelect =
    sources.length > 0
      ? sources
      : [
          {
            key: "all",
            name: "Todas as fontes habilitadas",
            enabled: true,
            source_type: "batch",
            destination_model: "mixed",
            base_url: "sources_registry.json",
          },
        ];
  const selectedSource = sources.find((source) => source.key === selectedSourceKey);

  return (
    <section className="overflow-hidden rounded-lg border border-orange-200 bg-white shadow-sm dark:border-orange-900 dark:bg-slate-950">
      <div className="grid gap-0 lg:grid-cols-[1fr_auto]">
        <div className="p-5">
          <div className="flex items-start gap-3">
            <div className="rounded-md bg-orange-100 p-2 text-orange-700 dark:bg-orange-950 dark:text-orange-300">
              <Radar className="h-6 w-6" />
            </div>
            <div>
              <p className="text-sm font-semibold uppercase tracking-wide text-orange-700 dark:text-orange-300">
                Motor de Ingestao Massiva
              </p>
              <h3 className="mt-1 text-xl font-semibold text-slate-950 dark:text-white">
                Motor de Ingestao Massiva
              </h3>
              <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600 dark:text-slate-300">
                Dispara a fabrica de conectores para coletar fontes registradas,
                normalizar lotes e sincronizar entidades no Neo4j em segundo plano.
              </p>
              <div className="mt-5 grid gap-3 md:grid-cols-[minmax(0,1fr)_auto] md:items-end">
                <label className="block">
                  <span className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                    Fonte de dados
                  </span>
                  <select
                    className="mt-2 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-800 shadow-sm outline-none transition focus:border-orange-500 focus:ring-2 focus:ring-orange-500/20 disabled:cursor-not-allowed disabled:opacity-70 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100"
                    disabled={sourcesLoading || busy}
                    onChange={(event) => onSelectSource(event.target.value)}
                    value={selectedSourceKey}
                  >
                    {sourcesForSelect.map((source) => (
                      <option
                        disabled={!source.enabled}
                        key={source.key}
                        value={source.key}
                      >
                        {source.key === "all"
                          ? `${source.name} (${enabledCount || "carregando"} fontes)`
                          : `${source.key} - ${source.name}${source.enabled ? "" : " (desativada)"}`}
                      </option>
                    ))}
                  </select>
                </label>
                <div className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-600 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-300">
                  <p className="font-semibold text-slate-950 dark:text-white">
                    {sourcesLoading ? "Carregando fontes" : `${enabledCount} habilitada(s)`}
                  </p>
                  <p className="mt-1">
                    Selecionada: {selectedSource?.source_type ?? "batch"}
                  </p>
                </div>
              </div>
              {sourcesError ? (
                <p className="mt-3 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900 dark:border-amber-900 dark:bg-amber-950/40 dark:text-amber-200">
                  Nao foi possivel carregar o registry completo: {sourcesError}
                </p>
              ) : null}
            </div>
          </div>
        </div>
        <div className="flex items-center border-t border-orange-100 bg-orange-50 p-5 dark:border-orange-900 dark:bg-orange-950/30 lg:border-l lg:border-t-0">
          <button
            className="inline-flex w-full items-center justify-center gap-2 rounded-md bg-orange-600 px-5 py-3 text-sm font-semibold text-white shadow-sm hover:bg-orange-700 disabled:cursor-not-allowed disabled:opacity-70"
            disabled={disabled || busy || sourcesLoading}
            onClick={onRun}
            type="button"
          >
            {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Flame className="h-4 w-4" />}
            {busy ? "Iniciando varredura..." : "Iniciar Varredura"}
          </button>
        </div>
      </div>
    </section>
  );
}

function SourcesActivationPanel({
  activationHelp,
  filter,
  onFilterChange,
  onRefresh,
  onSearchChange,
  onToggleSource,
  search,
  sources,
  sourcesError,
  sourcesLoading,
  stats,
  updatingSourceKey,
}: {
  activationHelp: ActivationHelp | null;
  filter: "all" | "enabled" | "disabled";
  onFilterChange: (filter: "all" | "enabled" | "disabled") => void;
  onRefresh: () => void;
  onSearchChange: (value: string) => void;
  onToggleSource: (source: IngestionSourceOption) => void;
  search: string;
  sources: IngestionSourceOption[];
  sourcesError: string | null;
  sourcesLoading: boolean;
  stats: { total: number; enabled: number; disabled: number };
  updatingSourceKey: string | null;
}) {
  const normalizedSearch = search.trim().toLowerCase();
  const visibleSources = sources
    .filter((source) => source.key !== "all")
    .filter((source) => {
      if (filter === "enabled") {
        return source.enabled;
      }
      if (filter === "disabled") {
        return !source.enabled;
      }
      return true;
    })
    .filter((source) => {
      if (!normalizedSearch) {
        return true;
      }
      return [
        source.key,
        source.name,
        source.category,
        source.base_url,
        source.destination_model,
      ]
        .join(" ")
        .toLowerCase()
        .includes(normalizedSearch);
    });

  return (
    <section className="rounded-lg border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-950">
      <div className="border-b border-slate-200 p-5 dark:border-slate-800">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
          <div>
            <div className="flex items-center gap-3">
              <div className="rounded-md bg-slate-100 p-2 text-slate-700 dark:bg-slate-800 dark:text-slate-200">
                <Settings2 className="h-5 w-5" />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-slate-950 dark:text-white">
                  Fontes e ativacao de conectores
                </h3>
                <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600 dark:text-slate-300">
                  Aqui voce ve por que existem apenas {stats.enabled} fontes ativas,
                  quais estao pendentes e o que precisa configurar antes de colocar
                  uma nova fonte na varredura massiva.
                </p>
              </div>
            </div>
          </div>
          <div className="grid gap-2 sm:grid-cols-3">
            <SourceStat label="Total" value={stats.total} />
            <SourceStat label="Ativas" value={stats.enabled} tone="success" />
            <SourceStat label="Inativas" value={stats.disabled} tone="muted" />
          </div>
        </div>

        <div className="mt-5 grid gap-4 lg:grid-cols-[1fr_1fr]">
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-4 dark:border-slate-800 dark:bg-slate-900">
            <p className="text-sm font-semibold text-slate-950 dark:text-white">
              Como ativar uma fonte
            </p>
            <ol className="mt-3 space-y-2 text-sm leading-6 text-slate-600 dark:text-slate-300">
              {(activationHelp?.steps ?? [
                "Verifique as pendencias da fonte.",
                "Configure as credenciais no .env ou GitHub Secrets.",
                "Ative a fonte e execute a varredura.",
              ]).map((step) => (
                <li key={step}>{step}</li>
              ))}
            </ol>
          </div>
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-4 dark:border-slate-800 dark:bg-slate-900">
            <p className="text-sm font-semibold text-slate-950 dark:text-white">
              Onde colocar configuracoes
            </p>
            <div className="mt-3 grid gap-2 text-sm text-slate-600 dark:text-slate-300">
              <ConfigLine label="Registry" value={activationHelp?.registry_path ?? "api/app/modules/ingestion/sources_registry.json"} />
              <ConfigLine label="Ambiente" value={activationHelp?.env_file ?? ".env"} />
              <ConfigLine label="Exemplo" value={activationHelp?.env_example ?? ".env.example"} />
            </div>
            <div className="mt-4 rounded-md border border-slate-200 bg-white p-3 dark:border-slate-800 dark:bg-slate-950">
              <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">
                GitHub Secrets esperados
              </p>
              <div className="mt-2 flex flex-wrap gap-2">
                {(activationHelp?.github_secrets ?? ["CGU_API_KEY", "OPENAI_API_KEY", "GOOGLE_CLIENT_ID"]).map((secret) => (
                  <span
                    className="rounded bg-slate-100 px-2 py-1 font-mono text-[11px] text-slate-700 dark:bg-slate-800 dark:text-slate-200"
                    key={secret}
                  >
                    {secret}
                  </span>
                ))}
              </div>
            </div>
            <p className="mt-3 text-xs leading-5 text-slate-500 dark:text-slate-400">
              {activationHelp?.production_note ??
                "Em Docker/CI, versionar o registry atualizado para tornar a mudanca permanente."}
            </p>
          </div>
        </div>

        <div className="mt-5 flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div className="relative min-w-0 flex-1">
            <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
            <input
              className="w-full rounded-md border border-slate-300 bg-white py-2 pl-9 pr-3 text-sm text-slate-900 outline-none focus:border-slate-500 dark:border-slate-700 dark:bg-slate-900 dark:text-white"
              onChange={(event) => onSearchChange(event.target.value)}
              placeholder="Buscar por chave, nome, categoria, URL..."
              value={search}
            />
          </div>
          <div className="flex flex-wrap gap-2">
            {(["all", "enabled", "disabled"] as const).map((item) => (
              <button
                className={`rounded-md px-3 py-2 text-sm font-semibold transition ${
                  filter === item
                    ? "bg-slate-950 text-white dark:bg-white dark:text-slate-950"
                    : "border border-slate-300 text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
                }`}
                key={item}
                onClick={() => onFilterChange(item)}
                type="button"
              >
                {item === "all" ? "Todas" : item === "enabled" ? "Ativas" : "Inativas"}
              </button>
            ))}
            <button
              className="inline-flex items-center gap-2 rounded-md border border-slate-300 px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-60 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
              disabled={sourcesLoading}
              onClick={onRefresh}
              type="button"
            >
              <RefreshCw className={`h-4 w-4 ${sourcesLoading ? "animate-spin" : ""}`} />
              Atualizar fontes
            </button>
          </div>
        </div>

        {sourcesError ? (
          <p className="mt-3 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900 dark:border-amber-900 dark:bg-amber-950/40 dark:text-amber-200">
            {sourcesError}
          </p>
        ) : null}
      </div>

      <div className="max-h-[560px] overflow-y-auto">
        {sourcesLoading && visibleSources.length === 0 ? (
          <div className="space-y-3 p-5">
            {Array.from({ length: 5 }).map((_, index) => (
              <div
                className="h-24 animate-pulse rounded-lg bg-slate-100 dark:bg-slate-900"
                key={index}
              />
            ))}
          </div>
        ) : (
          <div className="divide-y divide-slate-100 dark:divide-slate-800">
            {visibleSources.map((source) => (
              <SourceRow
                key={source.key}
                onToggle={() => onToggleSource(source)}
                source={source}
                updating={updatingSourceKey === source.key}
              />
            ))}
            {!visibleSources.length ? (
              <div className="p-8 text-center text-sm text-slate-500 dark:text-slate-400">
                Nenhuma fonte encontrada neste filtro.
              </div>
            ) : null}
          </div>
        )}
      </div>
    </section>
  );
}

function SourceRow({
  onToggle,
  source,
  updating,
}: {
  onToggle: () => void;
  source: IngestionSourceOption;
  updating: boolean;
}) {
  const canActivate = source.enabled || source.can_enable;
  const notes = source.activation_notes ?? [];
  const primaryNote = notes[0] ?? "Sem pendencias registradas.";

  return (
    <article className="p-5">
      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_auto] xl:items-start">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span
              className={`rounded-full px-2 py-1 text-xs font-semibold ${
                source.enabled
                  ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-200"
                  : "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300"
              }`}
            >
              {source.enabled ? "Ativa" : "Inativa"}
            </span>
            <span className="rounded-full bg-slate-100 px-2 py-1 text-xs font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-300">
              {source.category}
            </span>
            {source.requires_token ? (
              <span
                className={`rounded-full px-2 py-1 text-xs font-medium ${
                  source.has_auth_token
                    ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-200"
                    : "bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-200"
                }`}
              >
                {source.has_auth_token ? "Credencial OK" : `Precisa ${source.auth_env ?? "token"}`}
              </span>
            ) : null}
          </div>
          <h4 className="mt-2 text-base font-semibold text-slate-950 dark:text-white">
            {source.name}
          </h4>
          <p className="mt-1 font-mono text-xs text-slate-500 dark:text-slate-400">
            {source.key}
          </p>
          <div className="mt-3 grid gap-2 text-xs text-slate-600 dark:text-slate-300 md:grid-cols-3">
            <ConfigLine label="Tipo" value={source.source_type} />
            <ConfigLine label="Modelo" value={source.destination_model} />
            <ConfigLine label="Auth" value={source.auth_env ?? "sem chave"} />
          </div>
          <p className="mt-3 truncate text-xs text-slate-500 dark:text-slate-400">
            {source.base_url}
          </p>
          <div className="mt-3 rounded-md border border-slate-200 bg-slate-50 p-3 text-xs leading-5 text-slate-600 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-300">
            <p className="font-semibold text-slate-800 dark:text-slate-100">
              Pendencias / orientacao
            </p>
            <p className="mt-1">{primaryNote}</p>
            {notes.length > 1 ? (
              <ul className="mt-2 list-inside list-disc space-y-1">
                {notes.slice(1).map((note) => (
                  <li key={note}>{note}</li>
                ))}
              </ul>
            ) : null}
          </div>
        </div>

        <div className="flex flex-col gap-2 xl:w-44">
          <button
            className={`inline-flex items-center justify-center gap-2 rounded-md px-4 py-2 text-sm font-semibold transition disabled:cursor-not-allowed disabled:opacity-60 ${
              source.enabled
                ? "border border-slate-300 text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
                : "bg-emerald-600 text-white hover:bg-emerald-700"
            }`}
            disabled={updating || !canActivate}
            onClick={onToggle}
            type="button"
          >
            {updating ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Power className="h-4 w-4" />
            )}
            {source.enabled ? "Desativar" : "Ativar"}
          </button>
          {!canActivate ? (
            <p className="text-xs leading-5 text-amber-700 dark:text-amber-300">
              Resolva as pendencias antes de ativar.
            </p>
          ) : null}
        </div>
      </div>
    </article>
  );
}

function SourceStat({
  label,
  tone = "default",
  value,
}: {
  label: string;
  tone?: "default" | "success" | "muted";
  value: number;
}) {
  const className =
    tone === "success"
      ? "border-emerald-200 bg-emerald-50 text-emerald-900 dark:border-emerald-900 dark:bg-emerald-950/40 dark:text-emerald-100"
      : tone === "muted"
        ? "border-slate-200 bg-slate-50 text-slate-700 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-200"
        : "border-slate-200 bg-white text-slate-900 dark:border-slate-800 dark:bg-slate-900 dark:text-white";
  return (
    <div className={`rounded-md border px-4 py-3 text-center ${className}`}>
      <p className="text-xl font-semibold">{value}</p>
      <p className="mt-1 text-xs font-medium opacity-75">{label}</p>
    </div>
  );
}

function ConfigLine({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0">
      <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">
        {label}
      </p>
      <p className="truncate font-mono text-xs text-slate-700 dark:text-slate-200">
        {value}
      </p>
    </div>
  );
}

function OperationalHud({
  activeTasks,
  connection,
  lastChecked,
  recentErrors,
  servicesByName,
}: {
  activeTasks: number;
  connection: ConnectionState;
  lastChecked?: string;
  recentErrors: number;
  servicesByName: Record<string, HealthService | undefined>;
}) {
  return (
    <section className="grid gap-3 md:grid-cols-2 xl:grid-cols-6">
      <StatusCard
        icon={connection.status === "offline" ? WifiOff : Wifi}
        label="Conexao"
        message={connection.message}
        status={connection.status}
        value={connectionLabel(connection.status)}
      />
      <ServiceCard icon={Server} label="API" service={servicesByName.api} />
      <ServiceCard icon={Database} label="Postgres" service={servicesByName.postgres} />
      <ServiceCard icon={Database} label="Redis" service={servicesByName.redis} />
      <ServiceCard icon={Activity} label="Celery" service={servicesByName.celery} />
      <StatusCard
        icon={recentErrors > 0 ? AlertCircle : CheckCircle2}
        label="Fila e logs"
        message={`${activeTasks} tarefa(s) em execucao; ${recentErrors} aviso(s)/erro(s) recente(s).`}
        status={recentErrors > 0 ? "degraded" : activeTasks > 0 ? "checking" : "online"}
        value={activeTasks > 0 ? `${activeTasks} ativa(s)` : "Estavel"}
      />
      <div className="md:col-span-2 xl:col-span-6">
        <p className="text-xs text-slate-500 dark:text-slate-400">
          Ultima verificacao: {lastChecked ? formatDate(lastChecked) : "aguardando"}
        </p>
      </div>
    </section>
  );
}

function ServiceCard({
  icon,
  label,
  service,
}: {
  icon: LucideIcon;
  label: string;
  service?: HealthService;
}) {
  const status = serviceStatusToConnection(service?.status);
  return (
    <StatusCard
      icon={icon}
      label={label}
      message={service?.message ?? "Ainda sem resposta desta camada."}
      status={status}
      value={serviceLabel(service?.status)}
    />
  );
}

function StatusCard({
  icon: Icon,
  label,
  message,
  status,
  value,
}: {
  icon: LucideIcon;
  label: string;
  message: string;
  status: ConnectionState["status"];
  value: string;
}) {
  const tone = statusTone(status);
  return (
    <article className={`rounded-lg border p-4 shadow-sm ${tone.container}`}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className={`text-xs font-semibold uppercase tracking-wide ${tone.muted}`}>
            {label}
          </p>
          <p className={`mt-1 text-lg font-semibold ${tone.text}`}>{value}</p>
        </div>
        <div className={`rounded-md p-2 ${tone.icon}`}>
          <Icon className="h-4 w-4" />
        </div>
      </div>
      <p className={`mt-3 line-clamp-3 text-xs leading-5 ${tone.muted}`}>{message}</p>
    </article>
  );
}

function ConnectionBadge({
  connection,
  loading,
}: {
  connection: ConnectionState;
  loading: boolean;
}) {
  const tone = statusTone(connection.status);
  return (
    <div className={`inline-flex w-fit items-center gap-2 rounded-md border px-3 py-2 text-xs font-semibold ${tone.badge}`}>
      {loading || connection.status === "checking" ? (
        <Loader2 className="h-4 w-4 animate-spin" />
      ) : connection.status === "offline" ? (
        <WifiOff className="h-4 w-4" />
      ) : (
        <CheckCircle2 className="h-4 w-4" />
      )}
      {connectionLabel(connection.status)}
    </div>
  );
}

function ActionCard({
  busy,
  description,
  disabled,
  expected,
  onRun,
  title,
}: {
  busy: boolean;
  description: string;
  disabled: boolean;
  expected: string;
  onRun: () => void;
  title: string;
}) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-950">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h3 className="text-base font-semibold text-slate-950 dark:text-white">
            {title}
          </h3>
          <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">
            {description}
          </p>
          <p className="mt-3 text-xs font-medium text-slate-500 dark:text-slate-400">
            {expected}
          </p>
        </div>
        <div className="rounded-md bg-slate-100 p-2 text-slate-700 dark:bg-slate-800 dark:text-slate-200">
          <Play className="h-5 w-5" />
        </div>
      </div>
      <button
        className="mt-5 inline-flex items-center gap-2 rounded-md bg-slate-950 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-70 dark:bg-white dark:text-slate-950 dark:hover:bg-slate-200"
        disabled={disabled || busy}
        onClick={onRun}
        type="button"
      >
        {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
        {busy ? "Enviando..." : "Disparar tarefa"}
      </button>
    </div>
  );
}

function LastResultCard({ result }: { result: AdminActionResponse }) {
  const camaraCount = result.source_counts?.["dados-abertos-camara"] ?? 0;
  const senadoCount = result.source_counts?.["dados-abertos-senado"] ?? 0;
  const tse2024Count = result.source_counts?.["dados-abertos-tse-2024"] ?? 0;
  const tse2022Count = result.source_counts?.["dados-abertos-tse-2022"] ?? 0;

  return (
    <section className="rounded-lg border border-emerald-200 bg-emerald-50 p-5 shadow-sm dark:border-emerald-900 dark:bg-emerald-950/40">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <p className="text-sm font-semibold text-emerald-800 dark:text-emerald-300">
            Ultima acao enviada
          </p>
          <h3 className="mt-1 text-lg font-semibold text-slate-950 dark:text-white">
            {result.status === "accepted"
              ? "Tarefa na fila de processamento"
              : "Execucao concluida"}
          </h3>
          <p className="mt-1 text-sm text-emerald-900 dark:text-emerald-200">
            {successMessage(
              result.job === "massive_ingestion"
                ? "massive"
                : result.contracts_saved !== undefined
                  ? "daily"
                  : "politicians",
              result,
            )}
          </p>
        </div>
        <div className="grid gap-3 sm:grid-cols-3">
          <ResultMetric
            label={result.contracts_found !== undefined ? "Contratos achados" : "Encontrados"}
            value={result.contracts_found ?? result.politicians_found ?? 0}
          />
          <ResultMetric
            label={result.contracts_saved !== undefined ? "Contratos salvos" : "Salvos"}
            value={result.contracts_saved ?? result.politicians_saved ?? 0}
          />
          <ResultMetric label="Avisos" value={result.errors?.length ?? 0} />
        </div>
      </div>
      {result.task_id ? (
        <p className="mt-4 text-xs text-emerald-900 dark:text-emerald-200">
          ID da tarefa: {result.task_id}
        </p>
      ) : null}
      {camaraCount || senadoCount || tse2024Count || tse2022Count ? (
        <p className="mt-2 text-xs text-emerald-900 dark:text-emerald-200">
          Fontes: Camara {camaraCount}, Senado {senadoCount}, TSE 2024 {tse2024Count},
          TSE 2022 {tse2022Count}.
        </p>
      ) : null}
    </section>
  );
}

function ToastSuccess({ message }: { message: string }) {
  return (
    <section className="rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-900 shadow-sm dark:border-emerald-900 dark:bg-emerald-950/40 dark:text-emerald-200">
      <div className="flex gap-3">
        <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0" />
        <div>
          <p className="font-semibold">Ignicao confirmada</p>
          <p className="mt-1">{message}</p>
        </div>
      </div>
    </section>
  );
}

function ResultMetric({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-md border border-emerald-200 bg-white px-4 py-3 text-center dark:border-emerald-900 dark:bg-slate-950">
      <p className="text-xl font-semibold text-slate-950 dark:text-white">{value}</p>
      <p className="mt-1 text-xs font-medium text-slate-500 dark:text-slate-400">
        {label}
      </p>
    </div>
  );
}

function ActionError({ error }: { error: unknown }) {
  return (
    <section className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-900 shadow-sm dark:border-red-900 dark:bg-red-950/40 dark:text-red-200">
      <div className="flex gap-3">
        <AlertCircle className="mt-0.5 h-5 w-5 shrink-0" />
        <div>
          <p className="font-semibold">Nao foi possivel disparar a tarefa</p>
          <p className="mt-1">{humanErrorMessage(error)}</p>
        </div>
      </div>
    </section>
  );
}

function LogRow({
  expanded,
  log,
  onToggle,
}: {
  expanded: boolean;
  log: AdminLog;
  onToggle: () => void;
}) {
  const tone = logTone(log.status);
  const isRunning = log.status === "running";

  return (
    <article className="px-5 py-4">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="flex gap-3">
          <div className={`mt-0.5 rounded-md p-2 ${tone.icon}`}>
            {log.status === "error" ? (
              <AlertCircle className="h-5 w-5" />
            ) : log.status === "warning" ? (
              <AlertCircle className="h-5 w-5" />
            ) : isRunning ? (
              <Loader2 className="h-5 w-5 animate-spin" />
            ) : (
              <CheckCircle2 className="h-5 w-5" />
            )}
          </div>
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <h4 className="font-semibold text-slate-950 dark:text-white">{log.title}</h4>
              <span className={`rounded-full px-2 py-1 text-xs font-medium ${tone.badge}`}>
                {statusLabel(log.status)}
              </span>
            </div>
            <p className="mt-1 text-sm leading-6 text-slate-600 dark:text-slate-300">
              {log.message}
            </p>
            <p className="mt-1 text-xs text-slate-400">{formatDate(log.created_at)}</p>
          </div>
        </div>
        <button
          className="inline-flex w-fit items-center gap-2 rounded-md border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-900"
          onClick={onToggle}
          type="button"
        >
          <Terminal className="h-4 w-4" />
          Detalhes tecnicos
        </button>
      </div>

      {expanded ? (
        <pre className="mt-4 max-h-80 overflow-auto rounded-lg bg-slate-950 p-4 text-xs leading-6 text-slate-100">
          {JSON.stringify(log.technical_details, null, 2)}
        </pre>
      ) : null}
    </article>
  );
}

function LogSkeleton() {
  return (
    <div className="space-y-4 p-5">
      {Array.from({ length: 4 }).map((_, index) => (
        <div className="flex animate-pulse gap-3" key={index}>
          <div className="h-10 w-10 rounded-md bg-slate-200 dark:bg-slate-800" />
          <div className="flex-1">
            <div className="h-4 w-56 rounded bg-slate-200 dark:bg-slate-800" />
            <div className="mt-3 h-3 w-full max-w-xl rounded bg-slate-200 dark:bg-slate-800" />
          </div>
        </div>
      ))}
    </div>
  );
}

async function adminRequest<T>(
  path: string,
  init?: RequestInit,
  timeoutMs = 12000,
): Promise<T> {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), timeoutMs);
  const headers = new Headers(init?.headers);
  headers.set("Content-Type", "application/json");

  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      signal: controller.signal,
      headers,
      credentials: "include",
      cache: "no-store",
    });

    if (!response.ok) {
      const payload = await parseResponseBody(response);
      if (response.status === 401) {
        throw new ApiRequestError(
          "Sessao expirada ou token invalido. Entre novamente para acionar o motor.",
          response.status,
          payload,
        );
      }
      throw new ApiRequestError(
        messageFromErrorPayload(payload) ?? `${response.status} ${response.statusText}`,
        response.status,
        payload,
      );
    }

    return (await response.json()) as T;
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new ApiRequestError(
        "Tempo esgotado ao conversar com a API. A stack pode estar subindo ou reiniciando.",
      );
    }
    throw error;
  } finally {
    window.clearTimeout(timeout);
  }
}

async function parseResponseBody(response: Response) {
  try {
    return await response.json();
  } catch {
    return null;
  }
}

function ingestionPath(action: ActionKey) {
  if (action === "massive") {
    return "/admin/ingestion/run";
  }

  if (action === "politicians") {
    return "/ingestion/politicians/run?itens=100&paginas_camara=6&despesas_por_politico=5&incluir_senado=true&despesas_senado=false&incluir_tse=true&anos_tse=2024,2022&limite_tse_por_cargo=50&patrimonio_tse=false&sync_graph=false";
  }

  if (action === "politiciansFull") {
    return "/ingestion/politicians/run?itens=100&paginas_camara=6&despesas_por_politico=20&incluir_senado=true&despesas_senado=true&incluir_tse=true&anos_tse=2024,2022&limite_tse_por_cargo=0&patrimonio_tse=true&sync_graph=false";
  }

  return "/ingestion/run";
}

function connectionFromHealth(health: SystemHealth): ConnectionState {
  if (health.status === "success") {
    return {
      status: "online",
      message: "API, banco, Redis e worker responderam.",
      checkedAt: health.checked_at,
    };
  }

  if (health.status === "degraded") {
    return {
      status: "degraded",
      message: "API respondeu, mas algum servico auxiliar precisa de atencao.",
      checkedAt: health.checked_at,
      technicalDetails: health,
    };
  }

  return {
    status: "offline",
    message: "API respondeu com estado critico.",
    checkedAt: health.checked_at,
    technicalDetails: health,
  };
}

function frontendErrorLog(error: unknown, title = "Falha de comunicacao") {
  return {
    id: `frontend-${Date.now()}`,
    status: "error",
    title,
    message: humanErrorMessage(error),
    technical_details: serializeError(error),
    created_at: new Date().toISOString(),
  };
}

function serializeError(error: unknown) {
  if (error instanceof ApiRequestError) {
    return {
      name: error.name,
      message: error.message,
      status: error.status,
      payload: error.payload,
      stack: error.stack,
    };
  }
  if (error instanceof Error) {
    return { name: error.name, message: error.message, stack: error.stack };
  }
  return { error };
}

function humanErrorMessage(error: unknown) {
  if (error instanceof ApiRequestError) {
    return error.message;
  }
  if (error instanceof TypeError && error.message.toLowerCase().includes("failed to fetch")) {
    return "O navegador nao conseguiu chamar a rota /api/backend. Verifique se a porta 3000 esta aberta e se o container web nao reiniciou.";
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "Erro desconhecido ao consultar o sistema.";
}

function messageFromErrorPayload(payload: unknown) {
  if (!payload || typeof payload !== "object") {
    return null;
  }
  const detail = "detail" in payload ? (payload as { detail?: unknown }).detail : null;
  if (typeof detail === "string") {
    return detail;
  }
  return null;
}

function successMessage(action: ActionKey, payload: AdminActionResponse) {
  if (payload.status === "accepted") {
    return `Tarefa enviada para a fila. ID: ${payload.task_id ?? "sem id"}. Acompanhe no monitor de logs.`;
  }

  if (action === "massive") {
    const warningText = payload.errors?.length ? ` com ${payload.errors.length} aviso(s)` : "";
    return `${payload.sources_processed ?? 0} fonte(s), ${payload.rows_collected ?? 0} registro(s) coletados e ${payload.nodes_synced ?? 0} no grafo${warningText}.`;
  }

  if (
    (action === "politicians" || action === "politiciansFull") &&
    payload.politicians_saved !== undefined
  ) {
    const found = payload.politicians_found ?? payload.politicians_saved;
    const warnings = payload.errors?.length ?? 0;
    const warningText = warnings ? ` com ${warnings} aviso(s)` : "";
    return `${payload.politicians_saved} de ${found} politicos ativos salvos${warningText}.`;
  }

  if (action === "daily" && payload.contracts_saved !== undefined) {
    const warningText = payload.errors?.length ? ` com ${payload.errors.length} aviso(s)` : "";
    return `${payload.contracts_saved} contrato(s) e ${payload.expenses_saved ?? 0} despesa(s) salvos${warningText}.`;
  }

  return `Tarefa enviada com sucesso: ${payload.task_id ?? "sem id"}`;
}

function serviceStatusToConnection(status?: string): ConnectionState["status"] {
  if (status === "ok") {
    return "online";
  }
  if (status === "warning") {
    return "degraded";
  }
  if (status === "error") {
    return "offline";
  }
  return "checking";
}

function serviceLabel(status?: string) {
  const labels: Record<string, string> = {
    ok: "OK",
    warning: "Atencao",
    error: "Erro",
  };
  return status ? labels[status] ?? status : "Aguardando";
}

function connectionLabel(status: ConnectionState["status"]) {
  const labels: Record<ConnectionState["status"], string> = {
    checking: "Verificando",
    online: "Online",
    degraded: "Atencao",
    offline: "Offline",
  };
  return labels[status];
}

function statusLabel(status: string) {
  const labels: Record<string, string> = {
    success: "Sucesso",
    warning: "Com avisos",
    error: "Erro",
    running: "Em execucao",
  };
  return labels[status] ?? status;
}

function statusTone(status: ConnectionState["status"]) {
  if (status === "online") {
    return {
      badge: "border-emerald-200 bg-emerald-50 text-emerald-800 dark:border-emerald-900 dark:bg-emerald-950 dark:text-emerald-200",
      container: "border-emerald-200 bg-emerald-50 dark:border-emerald-900 dark:bg-emerald-950/30",
      icon: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900 dark:text-emerald-200",
      muted: "text-emerald-700 dark:text-emerald-300",
      text: "text-emerald-950 dark:text-emerald-100",
    };
  }

  if (status === "degraded" || status === "checking") {
    return {
      badge: "border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-900 dark:bg-amber-950 dark:text-amber-200",
      container: "border-amber-200 bg-amber-50 dark:border-amber-900 dark:bg-amber-950/30",
      icon: "bg-amber-100 text-amber-700 dark:bg-amber-900 dark:text-amber-200",
      muted: "text-amber-700 dark:text-amber-300",
      text: "text-amber-950 dark:text-amber-100",
    };
  }

  return {
    badge: "border-red-200 bg-red-50 text-red-800 dark:border-red-900 dark:bg-red-950 dark:text-red-200",
    container: "border-red-200 bg-red-50 dark:border-red-900 dark:bg-red-950/30",
    icon: "bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-200",
    muted: "text-red-700 dark:text-red-300",
    text: "text-red-950 dark:text-red-100",
  };
}

function logTone(status: string) {
  if (status === "error") {
    return {
      badge: "bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-200",
      icon: "bg-red-50 text-red-700 dark:bg-red-950 dark:text-red-200",
    };
  }
  if (status === "running") {
    return {
      badge: "bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-200",
      icon: "bg-amber-50 text-amber-700 dark:bg-amber-950 dark:text-amber-200",
    };
  }
  if (status === "warning") {
    return {
      badge: "bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-200",
      icon: "bg-amber-50 text-amber-700 dark:bg-amber-950 dark:text-amber-200",
    };
  }
  return {
    badge: "bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-200",
    icon: "bg-emerald-50 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-200",
  };
}

function formatDate(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "short",
    timeStyle: "medium",
  }).format(date);
}
