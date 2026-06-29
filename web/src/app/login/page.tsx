"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Lock, Mail, ShieldCheck } from "lucide-react";

type LoginState = "idle" | "loading" | "error" | "success";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [nextPath, setNextPath] = useState("/admin");
  const [state, setState] = useState<LoginState>("idle");
  const [message, setMessage] = useState("");

  useEffect(() => {
    const requestedNext = new URLSearchParams(window.location.search).get("next");
    if (requestedNext?.startsWith("/") && !requestedNext.startsWith("//")) {
      setNextPath(requestedNext);
    }
  }, []);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setState("loading");
    setMessage("");

    try {
      const response = await fetch("/api/backend/auth/login", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        credentials: "include",
        body: JSON.stringify({ email, password }),
      });

      if (!response.ok) {
        const payload = await safeJson(response);
        throw new Error(
          readableError(payload) || "Nao foi possivel autenticar este usuario.",
        );
      }

      setState("success");
      setMessage("Acesso validado. Redirecionando para o painel seguro.");
      router.replace(nextPath);
      router.refresh();
    } catch (error) {
      setState("error");
      setMessage(error instanceof Error ? error.message : "Falha inesperada no login.");
    }
  }

  return (
    <main className="min-h-screen bg-slate-50 text-slate-950 dark:bg-slate-950 dark:text-white">
      <div className="mx-auto flex min-h-screen w-full max-w-md flex-col justify-center px-6">
        <div className="mb-8 flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-lg bg-slate-900 text-white dark:bg-white dark:text-slate-950">
            <ShieldCheck className="h-5 w-5" aria-hidden="true" />
          </div>
          <div>
            <h1 className="text-xl font-semibold tracking-tight">Acesso seguro ONGP</h1>
            <p className="text-sm text-slate-600 dark:text-slate-400">
              Entre para acessar areas administrativas e investigativas.
            </p>
          </div>
        </div>

        <form
          onSubmit={handleSubmit}
          className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900"
        >
          <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">
            E-mail
            <span className="mt-2 flex items-center gap-2 rounded-md border border-slate-200 bg-white px-3 py-2 dark:border-slate-700 dark:bg-slate-950">
              <Mail className="h-4 w-4 text-slate-400" aria-hidden="true" />
              <input
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                autoComplete="email"
                required
                className="w-full bg-transparent text-sm outline-none"
                placeholder="voce@orgao.gov.br"
              />
            </span>
          </label>

          <label className="mt-4 block text-sm font-medium text-slate-700 dark:text-slate-300">
            Senha
            <span className="mt-2 flex items-center gap-2 rounded-md border border-slate-200 bg-white px-3 py-2 dark:border-slate-700 dark:bg-slate-950">
              <Lock className="h-4 w-4 text-slate-400" aria-hidden="true" />
              <input
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                autoComplete="current-password"
                required
                className="w-full bg-transparent text-sm outline-none"
                placeholder="Sua senha"
              />
            </span>
          </label>

          {message ? (
            <p
              className={`mt-4 rounded-md px-3 py-2 text-sm ${
                state === "error"
                  ? "bg-red-50 text-red-700 dark:bg-red-950/40 dark:text-red-300"
                  : "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300"
              }`}
            >
              {message}
            </p>
          ) : null}

          <button
            type="submit"
            disabled={state === "loading"}
            className="mt-5 inline-flex w-full items-center justify-center rounded-md bg-slate-900 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-70 dark:bg-white dark:text-slate-950 dark:hover:bg-slate-200"
          >
            {state === "loading" ? "Validando..." : "Entrar com seguranca"}
          </button>
        </form>
      </div>
    </main>
  );
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
  return null;
}
