"use client";

import {
  AlertCircle,
  CheckCircle2,
  Loader2,
  Play,
  RefreshCw,
  Terminal,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

const API_BASE_URL = "/api/backend";
const AUTH_HEADER = "Bearer mock-token-ongp";

type AdminLog = {
  id: string;
  status: "success" | "error" | "running" | string;
  title: string;
  message: string;
  technical_details: unknown;
  created_at: string;
};

type Toast = {
  type: "success" | "error";
  message: string;
};

type ActionKey = "politicians" | "daily";

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
  source_counts?: Record<string, number>;
  errors?: string[];
};

export default function AdminPage() {
  const [logs, setLogs] = useState<AdminLog[]>([]);
  const [loadingLogs, setLoadingLogs] = useState(true);
  const [expandedLogId, setExpandedLogId] = useState<string | null>(null);
  const [runningAction, setRunningAction] = useState<ActionKey | null>(null);
  const [toast, setToast] = useState<Toast | null>(null);
  const [lastResult, setLastResult] = useState<AdminActionResponse | null>(null);

  const systemSummary = useMemo(() => {
    const errors = logs.filter((log) => log.status === "error").length;
    return {
      errors,
      healthy: errors === 0,
    };
  }, [logs]);

  const loadLogs = useCallback(async () => {
    setLoadingLogs(true);
    try {
      const payload = await adminRequest<{ logs: AdminLog[] }>("/admin/system-logs");
      setLogs(payload.logs ?? []);
    } catch (error) {
      setLogs([
        {
          id: "frontend-log-fetch-error",
          status: "error",
          title: "Falha ao carregar logs",
          message: "A interface nao conseguiu consultar a API de administracao.",
          technical_details: serializeError(error),
          created_at: new Date().toISOString(),
        },
      ]);
    } finally {
      setLoadingLogs(false);
    }
  }, []);

  useEffect(() => {
    loadLogs();
    const interval = window.setInterval(loadLogs, 15000);
    return () => window.clearInterval(interval);
  }, [loadLogs]);

  async function runAction(action: ActionKey) {
    setRunningAction(action);
    setToast(null);

    try {
      const path =
        action === "politicians"
          ? "/ingestion/politicians/run?sync=true&itens=100&paginas_camara=6&despesas_por_politico=0&incluir_senado=true&incluir_tse=true&anos_tse=2024,2022&limite_tse_por_cargo=50"
          : "/ingestion/run?sync=true";
      const payload = await adminRequest<AdminActionResponse>(path, {
        method: "POST",
      });
      setLastResult(payload);
      setToast({
        type: "success",
        message: successMessage(action, payload),
      });
      await loadLogs();
      window.setTimeout(loadLogs, 2500);
    } catch (error) {
      setToast({
        type: "error",
        message: `Nao foi possivel iniciar a tarefa: ${errorMessage(error)}`,
      });
    } finally {
      setRunningAction(null);
    }
  }

  return (
    <div className="mx-auto max-w-7xl">
      <div className="mb-8 flex flex-col gap-4 border-b border-slate-200 pb-6 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-sm font-medium text-slate-500">Backoffice operacional</p>
          <h2 className="mt-1 text-2xl font-semibold text-slate-950">
            Administracao do Sistema
          </h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
            Dispare coletas oficiais e acompanhe tarefas, avisos e erros recentes em
            uma visao amigavel com detalhes tecnicos sob demanda.
          </p>
        </div>
        <div
          className={`w-fit rounded-md border px-3 py-2 text-xs font-semibold ${
            systemSummary.healthy
              ? "border-emerald-200 bg-emerald-50 text-emerald-800"
              : "border-red-200 bg-red-50 text-red-800"
          }`}
        >
          {systemSummary.healthy
            ? "Sistema sem erros recentes"
            : `${systemSummary.errors} erro(s) recente(s)`}
        </div>
      </div>

      {toast ? (
        <div
          className={`mb-6 rounded-lg border px-4 py-3 text-sm ${
            toast.type === "success"
              ? "border-emerald-200 bg-emerald-50 text-emerald-800"
              : "border-red-200 bg-red-50 text-red-800"
          }`}
          role="status"
        >
          {toast.message}
        </div>
      ) : null}

      <section className="grid gap-4 lg:grid-cols-2">
        <ActionCard
          busy={runningAction === "politicians"}
          description="Busca e salva deputados, senadores e eleitos do TSE por cargo, partido e UF para preencher os paineis de politicos."
          onRun={() => runAction("politicians")}
          title="Atualizar politicos ativos"
        />
        <ActionCard
          busy={runningAction === "daily"}
          description="Dispara a coleta geral do Portal da Transparencia para contratos e despesas."
          onRun={() => runAction("daily")}
          title="Executar Ingestao Geral"
        />
      </section>

      {lastResult ? <LastResultCard result={lastResult} /> : null}

      <section className="mt-6 rounded-lg border border-slate-200 bg-white shadow-sm">
        <div className="flex flex-col gap-3 border-b border-slate-200 px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h3 className="text-base font-semibold text-slate-950">
              Monitor de Logs
            </h3>
            <p className="mt-1 text-sm text-slate-500">
              Atualizacao automatica a cada 15 segundos
            </p>
          </div>
          <button
            className="inline-flex w-fit items-center gap-2 rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
            disabled={loadingLogs}
            onClick={loadLogs}
            type="button"
          >
            <RefreshCw className={`h-4 w-4 ${loadingLogs ? "animate-spin" : ""}`} />
            Recarregar
          </button>
        </div>

        <div className="divide-y divide-slate-100">
          {loadingLogs && logs.length === 0 ? (
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

function ActionCard({
  busy,
  description,
  onRun,
  title,
}: {
  busy: boolean;
  description: string;
  onRun: () => void;
  title: string;
}) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h3 className="text-base font-semibold text-slate-950">{title}</h3>
          <p className="mt-2 text-sm leading-6 text-slate-600">{description}</p>
        </div>
        <div className="rounded-md bg-slate-100 p-2 text-slate-700">
          <Play className="h-5 w-5" />
        </div>
      </div>
      <button
        className="mt-5 inline-flex items-center gap-2 rounded-md bg-slate-950 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-70"
        disabled={busy}
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
      <section className="mt-6 rounded-lg border border-emerald-200 bg-emerald-50 p-5 shadow-sm">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <p className="text-sm font-semibold text-emerald-800">
            Ultima execucao
          </p>
          <h3 className="mt-1 text-lg font-semibold text-slate-950">
            {result.status === "completed"
              ? result.contracts_saved !== undefined
                ? "Contratos e despesas sincronizados"
                : "Politicos ativos sincronizados"
              : "Tarefa enviada ao processamento"}
          </h3>
          <p className="mt-1 text-sm text-emerald-900">
            {successMessage(result.contracts_saved !== undefined ? "daily" : "politicians", result)}
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
      {camaraCount || senadoCount || tse2024Count || tse2022Count ? (
        <p className="mt-4 text-xs text-emerald-900">
          Fontes: Camara {camaraCount} registro(s), Senado {senadoCount} registro(s),
          TSE 2024 {tse2024Count} registro(s), TSE 2022 {tse2022Count} registro(s).
        </p>
      ) : null}
    </section>
  );
}

function ResultMetric({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-md border border-emerald-200 bg-white px-4 py-3 text-center">
      <p className="text-xl font-semibold text-slate-950">{value}</p>
      <p className="mt-1 text-xs font-medium text-slate-500">{label}</p>
    </div>
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
  const isError = log.status === "error";
  const isRunning = log.status === "running";

  return (
    <article className="px-5 py-4">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="flex gap-3">
          <div
            className={`mt-0.5 rounded-md p-2 ${
              isError
                ? "bg-red-50 text-red-700"
                : isRunning
                  ? "bg-amber-50 text-amber-700"
                  : "bg-emerald-50 text-emerald-700"
            }`}
          >
            {isError ? (
              <AlertCircle className="h-5 w-5" />
            ) : isRunning ? (
              <Loader2 className="h-5 w-5 animate-spin" />
            ) : (
              <CheckCircle2 className="h-5 w-5" />
            )}
          </div>
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <h4 className="font-semibold text-slate-950">{log.title}</h4>
              <span className="rounded-full bg-slate-100 px-2 py-1 text-xs font-medium text-slate-600">
                {statusLabel(log.status)}
              </span>
            </div>
            <p className="mt-1 text-sm leading-6 text-slate-600">{log.message}</p>
            <p className="mt-1 text-xs text-slate-400">{formatDate(log.created_at)}</p>
          </div>
        </div>
        <button
          className="inline-flex w-fit items-center gap-2 rounded-md border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
          onClick={onToggle}
          type="button"
        >
          <Terminal className="h-4 w-4" />
          Detalhes Tecnicos
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
          <div className="h-10 w-10 rounded-md bg-slate-200" />
          <div className="flex-1">
            <div className="h-4 w-56 rounded bg-slate-200" />
            <div className="mt-3 h-3 w-full max-w-xl rounded bg-slate-200" />
          </div>
        </div>
      ))}
    </div>
  );
}

async function adminRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      Authorization: AUTH_HEADER,
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }

  return (await response.json()) as T;
}

function serializeError(error: unknown) {
  if (error instanceof Error) {
    return { name: error.name, message: error.message, stack: error.stack };
  }
  return { error };
}

function errorMessage(error: unknown) {
  if (error instanceof Error) {
    return error.message;
  }
  return "erro desconhecido";
}

function successMessage(action: ActionKey, payload: AdminActionResponse) {
  if (action === "politicians" && payload.politicians_saved !== undefined) {
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

function statusLabel(status: string) {
  const labels: Record<string, string> = {
    success: "Sucesso",
    error: "Erro",
    running: "Em execucao",
  };
  return labels[status] ?? status;
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
