"use client";

import {
  Ban,
  CheckCircle2,
  KeyRound,
  Lightbulb,
  Loader2,
  RefreshCw,
  Shield,
  UserCog,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

const API_BASE_URL = "/api/backend";

type TabKey = "suggestions" | "users" | "security";

type Overview = {
  cards?: {
    users?: number;
    active_users?: number;
    open_suggestions?: number;
    blocked_ips?: number;
    sources_total?: number;
    sources_enabled?: number;
    recent_errors?: number;
  };
};

type AdminUser = {
  id: string;
  email: string;
  name: string;
  active: boolean;
  mfa_enabled: boolean;
  roles: string[];
  created_at?: string | null;
};

type Suggestion = {
  id: string;
  title: string;
  description: string;
  category: string;
  priority: "low" | "medium" | "high" | "critical" | string;
  status: "open" | "reviewing" | "planned" | "done" | "rejected" | string;
  created_by_email?: string | null;
  assigned_to_email?: string | null;
  created_at?: string | null;
};

type BlockedIp = {
  ip_address: string;
  reason: string;
  blocked_by?: string;
  blocked_at?: string;
};

export function AdminCommandCenter() {
  const [activeTab, setActiveTab] = useState<TabKey>("suggestions");
  const [overview, setOverview] = useState<Overview | null>(null);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [blockedIps, setBlockedIps] = useState<BlockedIp[]>([]);
  const [loading, setLoading] = useState(true);
  const [busyKey, setBusyKey] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [overviewPayload, suggestionsPayload, usersPayload, blockedPayload] =
        await Promise.all([
          adminRequest<Overview>("/admin/overview"),
          adminRequest<{ items: Suggestion[] }>("/admin/suggestions"),
          adminRequest<{ items: AdminUser[] }>("/admin/users").catch((requestError) => {
            if (isForbidden(requestError)) {
              return { items: [] };
            }
            throw requestError;
          }),
          adminRequest<{ items: BlockedIp[] }>("/admin/security/blocked-ips").catch((requestError) => {
            if (isForbidden(requestError)) {
              return { items: [] };
            }
            throw requestError;
          }),
        ]);
      setOverview(overviewPayload);
      setSuggestions(suggestionsPayload.items ?? []);
      setUsers(usersPayload.items ?? []);
      setBlockedIps(blockedPayload.items ?? []);
    } catch (requestError) {
      setError(readableError(requestError));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const stats = useMemo(
    () => [
      {
        label: "Usuarios",
        value: overview?.cards?.users ?? users.length,
        hint: `${overview?.cards?.active_users ?? users.filter((user) => user.active).length} ativos`,
      },
      {
        label: "Sugestoes abertas",
        value: overview?.cards?.open_suggestions ?? suggestions.filter((item) => item.status === "open").length,
        hint: "Triagem administrativa",
      },
      {
        label: "IPs bloqueados",
        value: overview?.cards?.blocked_ips ?? blockedIps.length,
        hint: "Bloqueio manual Redis",
      },
      {
        label: "Fontes ativas",
        value: overview?.cards?.sources_enabled ?? 0,
        hint: `${overview?.cards?.sources_total ?? 0} cadastradas`,
      },
    ],
    [blockedIps.length, overview, suggestions, users],
  );

  async function createSuggestion(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const payload = {
      title: String(form.get("title") ?? ""),
      description: String(form.get("description") ?? ""),
      category: String(form.get("category") ?? "operacional"),
      priority: String(form.get("priority") ?? "medium"),
    };
    await runMutation("suggestion-create", async () => {
      await adminRequest("/admin/suggestions", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      event.currentTarget.reset();
      setMessage("Sugestao registrada para acompanhamento do admin.");
      await refresh();
    });
  }

  async function updateSuggestionStatus(id: string, nextStatus: string) {
    await runMutation(`suggestion-${id}`, async () => {
      await adminRequest(`/admin/suggestions/${encodeURIComponent(id)}`, {
        method: "PATCH",
        body: JSON.stringify({ status: nextStatus }),
      });
      setMessage("Status da sugestao atualizado.");
      await refresh();
    });
  }

  async function toggleUser(user: AdminUser) {
    await runMutation(`user-${user.id}`, async () => {
      await adminRequest(`/admin/users/${encodeURIComponent(user.id)}`, {
        method: "PATCH",
        body: JSON.stringify({ active: !user.active }),
      });
      setMessage(user.active ? "Usuario desativado." : "Usuario ativado.");
      await refresh();
    });
  }

  async function resetPassword(user: AdminUser) {
    const newPassword = window.prompt(
      `Nova senha para ${user.email}. Deixe em branco para gerar senha temporaria.`,
    );
    if (newPassword === null) {
      return;
    }
    await runMutation(`password-${user.id}`, async () => {
      const payload = await adminRequest<{ temporary_password?: string | null; message?: string }>(
        `/admin/users/${encodeURIComponent(user.id)}/reset-password`,
        {
          method: "POST",
          body: JSON.stringify(newPassword ? { new_password: newPassword } : {}),
        },
      );
      setMessage(
        payload.temporary_password
          ? `Senha temporaria gerada: ${payload.temporary_password}`
          : "Senha redefinida com sucesso.",
      );
    });
  }

  async function blockIp(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const payload = {
      ip_address: String(form.get("ip_address") ?? ""),
      reason: String(form.get("reason") ?? "Bloqueio manual pelo administrador."),
    };
    await runMutation("block-ip", async () => {
      await adminRequest("/admin/security/blocked-ips", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      event.currentTarget.reset();
      setMessage("IP bloqueado. Novas chamadas desse IP receberao 403.");
      await refresh();
    });
  }

  async function unblockIp(ipAddress: string) {
    await runMutation(`unblock-${ipAddress}`, async () => {
      await adminRequest(`/admin/security/blocked-ips?ip_address=${encodeURIComponent(ipAddress)}`, {
        method: "DELETE",
      });
      setMessage("IP removido da lista de bloqueio.");
      await refresh();
    });
  }

  async function runMutation(key: string, callback: () => Promise<void>) {
    setBusyKey(key);
    setError(null);
    setMessage(null);
    try {
      await callback();
    } catch (requestError) {
      setError(readableError(requestError));
    } finally {
      setBusyKey(null);
    }
  }

  return (
    <section className="rounded-lg border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-950">
      <div className="border-b border-slate-200 p-5 dark:border-slate-800">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="flex gap-3">
            <div className="h-fit rounded-md bg-slate-100 p-2 text-slate-700 dark:bg-slate-800 dark:text-slate-200">
              <Shield className="h-5 w-5" />
            </div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                Area exclusiva do administrador
              </p>
              <h3 className="mt-1 text-lg font-semibold text-slate-950 dark:text-white">
                Centro de comando do sistema
              </h3>
              <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600 dark:text-slate-300">
                Sugestoes operacionais, contas, reset de senha, bloqueio de IPs e leitura
                rapida do estado interno em um so lugar.
              </p>
            </div>
          </div>
          <button
            className="inline-flex items-center justify-center gap-2 rounded-md border border-slate-300 px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-60 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
            disabled={loading}
            onClick={() => void refresh()}
            type="button"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
            Atualizar centro
          </button>
        </div>

        <div className="mt-5 grid gap-3 md:grid-cols-4">
          {stats.map((item) => (
            <div
              className="rounded-md border border-slate-200 bg-slate-50 px-4 py-3 dark:border-slate-800 dark:bg-slate-900"
              key={item.label}
            >
              <p className="text-2xl font-semibold text-slate-950 dark:text-white">{item.value}</p>
              <p className="mt-1 text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                {item.label}
              </p>
              <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">{item.hint}</p>
            </div>
          ))}
        </div>

        {message ? (
          <div className="mt-4 flex gap-2 rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-800 dark:border-emerald-900 dark:bg-emerald-950/40 dark:text-emerald-200">
            <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
            <span>{message}</span>
          </div>
        ) : null}
        {error ? (
          <div className="mt-4 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800 dark:border-red-900 dark:bg-red-950/40 dark:text-red-200">
            {error}
          </div>
        ) : null}
      </div>

      <div className="border-b border-slate-200 px-5 pt-4 dark:border-slate-800">
        <div className="flex flex-wrap gap-2">
          <TabButton active={activeTab === "suggestions"} icon={Lightbulb} onClick={() => setActiveTab("suggestions")}>
            Sugestoes
          </TabButton>
          <TabButton active={activeTab === "users"} icon={UserCog} onClick={() => setActiveTab("users")}>
            Usuarios e senhas
          </TabButton>
          <TabButton active={activeTab === "security"} icon={Ban} onClick={() => setActiveTab("security")}>
            IPs bloqueados
          </TabButton>
        </div>
      </div>

      <div className="p-5">
        {loading ? (
          <div className="grid gap-3 md:grid-cols-3">
            {Array.from({ length: 3 }).map((_, index) => (
              <div className="h-32 animate-pulse rounded-lg bg-slate-100 dark:bg-slate-900" key={index} />
            ))}
          </div>
        ) : null}

        {!loading && activeTab === "suggestions" ? (
          <SuggestionsTab
            busyKey={busyKey}
            onCreate={createSuggestion}
            onUpdateStatus={updateSuggestionStatus}
            suggestions={suggestions}
          />
        ) : null}
        {!loading && activeTab === "users" ? (
          <UsersTab
            busyKey={busyKey}
            onResetPassword={resetPassword}
            onToggleUser={toggleUser}
            users={users}
          />
        ) : null}
        {!loading && activeTab === "security" ? (
          <SecurityTab
            blockedIps={blockedIps}
            busyKey={busyKey}
            onBlock={blockIp}
            onUnblock={unblockIp}
          />
        ) : null}
      </div>
    </section>
  );
}

function SuggestionsTab({
  busyKey,
  onCreate,
  onUpdateStatus,
  suggestions,
}: {
  busyKey: string | null;
  onCreate: (event: FormEvent<HTMLFormElement>) => void;
  onUpdateStatus: (id: string, status: string) => void;
  suggestions: Suggestion[];
}) {
  return (
    <div className="grid gap-5 xl:grid-cols-[360px_1fr]">
      <form className="rounded-lg border border-slate-200 bg-slate-50 p-4 dark:border-slate-800 dark:bg-slate-900" onSubmit={onCreate}>
        <p className="text-sm font-semibold text-slate-950 dark:text-white">Nova sugestao administrativa</p>
        <input className="mt-3 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-950" name="title" placeholder="Titulo curto" required />
        <textarea className="mt-3 min-h-28 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-950" name="description" placeholder="Descreva a sugestao, risco ou melhoria" required />
        <div className="mt-3 grid gap-3 sm:grid-cols-2">
          <input className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-950" name="category" placeholder="Categoria" defaultValue="operacional" />
          <select className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-950" name="priority" defaultValue="medium">
            <option value="low">Baixa</option>
            <option value="medium">Media</option>
            <option value="high">Alta</option>
            <option value="critical">Critica</option>
          </select>
        </div>
        <button className="mt-4 inline-flex items-center gap-2 rounded-md bg-slate-950 px-4 py-2 text-sm font-semibold text-white disabled:opacity-60 dark:bg-white dark:text-slate-950" disabled={busyKey === "suggestion-create"} type="submit">
          {busyKey === "suggestion-create" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Lightbulb className="h-4 w-4" />}
          Registrar sugestao
        </button>
      </form>

      <div className="divide-y divide-slate-100 rounded-lg border border-slate-200 dark:divide-slate-800 dark:border-slate-800">
        {suggestions.length ? suggestions.map((suggestion) => (
          <article className="p-4" key={suggestion.id}>
            <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
              <div>
                <div className="flex flex-wrap gap-2">
                  <Badge>{suggestion.priority}</Badge>
                  <Badge>{suggestion.status}</Badge>
                  <Badge>{suggestion.category}</Badge>
                </div>
                <h4 className="mt-2 font-semibold text-slate-950 dark:text-white">{suggestion.title}</h4>
                <p className="mt-1 text-sm leading-6 text-slate-600 dark:text-slate-300">{suggestion.description}</p>
                <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">Criada por {suggestion.created_by_email ?? "sistema"}</p>
              </div>
              <select className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-950" value={suggestion.status} onChange={(event) => onUpdateStatus(suggestion.id, event.target.value)}>
                <option value="open">Aberta</option>
                <option value="reviewing">Em analise</option>
                <option value="planned">Planejada</option>
                <option value="done">Concluida</option>
                <option value="rejected">Rejeitada</option>
              </select>
            </div>
          </article>
        )) : <EmptyState text="Nenhuma sugestao cadastrada ainda." />}
      </div>
    </div>
  );
}

function UsersTab({
  busyKey,
  onResetPassword,
  onToggleUser,
  users,
}: {
  busyKey: string | null;
  onResetPassword: (user: AdminUser) => void;
  onToggleUser: (user: AdminUser) => void;
  users: AdminUser[];
}) {
  if (!users.length) {
    return <EmptyState text="Usuarios indisponiveis para esta conta. Apenas system_admin pode ver e alterar usuarios." />;
  }

  return (
    <div className="overflow-hidden rounded-lg border border-slate-200 dark:border-slate-800">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-slate-200 text-sm dark:divide-slate-800">
          <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500 dark:bg-slate-900 dark:text-slate-400">
            <tr>
              <th className="px-4 py-3">Usuario</th>
              <th className="px-4 py-3">Roles</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3 text-right">Acoes</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
            {users.map((user) => (
              <tr key={user.id}>
                <td className="px-4 py-3">
                  <p className="font-semibold text-slate-950 dark:text-white">{user.name}</p>
                  <p className="text-xs text-slate-500">{user.email}</p>
                </td>
                <td className="px-4 py-3">
                  <div className="flex flex-wrap gap-1">
                    {user.roles.map((role) => <Badge key={role}>{role}</Badge>)}
                  </div>
                </td>
                <td className="px-4 py-3">{user.active ? "Ativo" : "Inativo"}</td>
                <td className="px-4 py-3">
                  <div className="flex justify-end gap-2">
                    <button className="rounded-md border border-slate-300 px-3 py-2 font-semibold dark:border-slate-700" disabled={busyKey === `user-${user.id}`} onClick={() => onToggleUser(user)} type="button">
                      {user.active ? "Desativar" : "Ativar"}
                    </button>
                    <button className="inline-flex items-center gap-2 rounded-md bg-slate-950 px-3 py-2 font-semibold text-white dark:bg-white dark:text-slate-950" disabled={busyKey === `password-${user.id}`} onClick={() => onResetPassword(user)} type="button">
                      <KeyRound className="h-4 w-4" />
                      Resetar senha
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function SecurityTab({
  blockedIps,
  busyKey,
  onBlock,
  onUnblock,
}: {
  blockedIps: BlockedIp[];
  busyKey: string | null;
  onBlock: (event: FormEvent<HTMLFormElement>) => void;
  onUnblock: (ipAddress: string) => void;
}) {
  return (
    <div className="grid gap-5 xl:grid-cols-[360px_1fr]">
      <form className="rounded-lg border border-slate-200 bg-slate-50 p-4 dark:border-slate-800 dark:bg-slate-900" onSubmit={onBlock}>
        <p className="text-sm font-semibold text-slate-950 dark:text-white">Bloquear IP manualmente</p>
        <input className="mt-3 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-950" name="ip_address" placeholder="Ex: 203.0.113.10" required />
        <textarea className="mt-3 min-h-24 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-950" name="reason" placeholder="Motivo do bloqueio" />
        <button className="mt-4 inline-flex items-center gap-2 rounded-md bg-red-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-60" disabled={busyKey === "block-ip"} type="submit">
          {busyKey === "block-ip" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Ban className="h-4 w-4" />}
          Bloquear IP
        </button>
      </form>

      <div className="divide-y divide-slate-100 rounded-lg border border-slate-200 dark:divide-slate-800 dark:border-slate-800">
        {blockedIps.length ? blockedIps.map((entry) => (
          <article className="flex flex-col gap-3 p-4 lg:flex-row lg:items-center lg:justify-between" key={entry.ip_address}>
            <div>
              <p className="font-mono text-sm font-semibold text-slate-950 dark:text-white">{entry.ip_address}</p>
              <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">{entry.reason}</p>
              <p className="mt-1 text-xs text-slate-500">Bloqueado por {entry.blocked_by ?? "admin"} em {entry.blocked_at ? new Date(entry.blocked_at).toLocaleString("pt-BR") : "data desconhecida"}</p>
            </div>
            <button className="rounded-md border border-slate-300 px-3 py-2 text-sm font-semibold dark:border-slate-700" disabled={busyKey === `unblock-${entry.ip_address}`} onClick={() => onUnblock(entry.ip_address)} type="button">
              Desbloquear
            </button>
          </article>
        )) : <EmptyState text="Nenhum IP bloqueado manualmente." />}
      </div>
    </div>
  );
}

function TabButton({
  active,
  children,
  icon: Icon,
  onClick,
}: {
  active: boolean;
  children: string;
  icon: LucideIcon;
  onClick: () => void;
}) {
  return (
    <button
      className={`inline-flex items-center gap-2 rounded-t-md px-3 py-2 text-sm font-semibold ${
        active
          ? "bg-slate-950 text-white dark:bg-white dark:text-slate-950"
          : "text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-900"
      }`}
      onClick={onClick}
      type="button"
    >
      <Icon className="h-4 w-4" />
      {children}
    </button>
  );
}

function Badge({ children }: { children: string }) {
  return (
    <span className="rounded-full bg-slate-100 px-2 py-1 text-xs font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-300">
      {children}
    </span>
  );
}

function EmptyState({ text }: { text: string }) {
  return (
    <div className="p-8 text-center text-sm text-slate-500 dark:text-slate-400">
      {text}
    </div>
  );
}

async function adminRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  headers.set("Content-Type", "application/json");

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers,
    credentials: "include",
    cache: "no-store",
  });
  if (!response.ok) {
    const payload = await safeJson(response);
    throw new Error(`${response.status} ${readableError(payload) ?? response.statusText}`);
  }
  return (await response.json()) as T;
}

async function safeJson(response: Response) {
  try {
    return await response.json();
  } catch {
    return null;
  }
}

function readableError(payload: unknown) {
  if (!payload || typeof payload !== "object") {
    return null;
  }
  const detail = "detail" in payload ? payload.detail : null;
  if (typeof detail === "string") {
    return detail;
  }
  if (detail && typeof detail === "object" && "message" in detail) {
    return String(detail.message);
  }
  return null;
}

function isForbidden(error: unknown) {
  return error instanceof Error && error.message.includes("403");
}
