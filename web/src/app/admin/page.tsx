"use client";

import { AlertCircle, CheckCircle2, Loader2, Play, RefreshCw, Terminal } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

const rawApiBaseUrl =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1";
const API_BASE_URL = rawApiBaseUrl.endsWith("/api/v1")
  ? rawApiBaseUrl
  : `${rawApiBaseUrl.replace(/\/$/, "")}/api/v1`;
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

export default function AdminPage() {
  const [logs, setLogs] = useState<AdminLog[]>([]);
  const [loadingLogs, setLoadingLogs] = useState(true);
  const [expandedLogId, setExpandedLogId] = useState<string | null>(null);
  const [runningAction, setRunningAction] = useState<ActionKey | null>(null);
  const [toast, setToast] = useState<Toast | null>(null);

  const systemSummary = useMemo(() => {
    const errors = logs.filter((log) => log.status === "error").length;
    const running = logs.filter((log) => log.status === "running").length;
    return {
      errors,
      running,
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
          message: "A interface não conseguiu consultar a API de administração.",
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
          ? "/ingestion/politicians/run?itens=100&paginas_camara=1&despesas_por_politico=100&incluir_senado=true"
          : "/ingestion/run";
      const payload = await adminRequest<Record<string, unknown>>(path, { method: "POST" });
      setToast({
        type: "success",
        message: `Tarefa enviada com sucesso: ${String(payload.task_id ?? "sem id")}`,
      });
      await loadLogs();
    } catch (error) {
      setToast({
        type: "error",
        message: `Não foi possível iniciar a tarefa: ${errorMessage(error)}`,
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
            Administração do Sistema
          </h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
            Dispare coletas oficiais e acompanhe tarefas, avisos e erros recentes em
            uma visão amigável com detalhes técnicos sob demanda.
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
          description="Busca deputados, senadores, partidos, UF e gastos parlamentares disponíveis."
          onRun={() => runAction("politicians")}
          title="Sincronizar Câmara/Senado"
        />
        <ActionCard
          busy={runningAction === "daily"}
          description="Dispara a coleta geral do Portal da Transparência para contratos e despesas."
          onRun={() => runAction("daily")}
          title="Executar Ingestão Geral"
        />
      </section>

      <section className="mt-6 rounded-lg border border-slate-200 bg-white shadow-sm">
        <div className="flex flex-col gap-3 border-b border-slate-200 px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h3 className="text-base font-semibold text-slate-950">
              Monitor de Logs
            </h3>
            <p className="mt-1 text-sm text-slate-500">
              Atualização automática a cada 15 segundos
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
          Detalhes Técnicos
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

function statusLabel(status: string) {
  const labels: Record<string, string> = {
    success: "Sucesso",
    error: "Erro",
    running: "Em execução",
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
