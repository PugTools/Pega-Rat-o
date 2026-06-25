"use client";

import Link from "next/link";
import { AlertTriangle, RotateCcw } from "lucide-react";

export default function PoliticoDetailError({
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <main className="mx-auto max-w-3xl">
      <div className="rounded-lg border border-red-200 bg-white p-6 shadow-sm dark:border-red-900/60 dark:bg-slate-900">
        <div className="flex gap-4">
          <div className="h-fit rounded-md bg-red-50 p-2 text-red-700 dark:bg-red-950/50 dark:text-red-300">
            <AlertTriangle className="h-5 w-5" aria-hidden="true" />
          </div>
          <div>
            <h1 className="text-xl font-semibold text-slate-950 dark:text-white">
              Nao foi possivel carregar este perfil
            </h1>
            <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">
              A API pode estar demorando ou temporariamente indisponivel. Tente
              novamente ou volte para a lista de politicos.
            </p>
            <div className="mt-5 flex flex-wrap gap-3">
              <button
                className="inline-flex items-center gap-2 rounded-md bg-slate-950 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800 dark:bg-white dark:text-slate-950 dark:hover:bg-slate-200"
                onClick={() => reset()}
                type="button"
              >
                <RotateCcw className="h-4 w-4" aria-hidden="true" />
                Tentar novamente
              </button>
              <Link
                className="inline-flex items-center rounded-md border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
                href="/politicos"
              >
                Voltar para politicos
              </Link>
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}
