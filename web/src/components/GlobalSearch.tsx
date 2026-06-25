"use client";

import Link from "next/link";
import { Search, X } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { api, type SearchResult } from "@/lib/api";

export function GlobalSearch() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);

  const normalizedQuery = useMemo(() => query.trim(), [query]);

  useEffect(() => {
    if (normalizedQuery.length < 2) {
      setResults([]);
      setError(null);
      setLoading(false);
      return;
    }

    let active = true;
    const controller = new AbortController();
    const timeout = window.setTimeout(async () => {
      setLoading(true);
      setError(null);
      try {
        const payload = await api.search(normalizedQuery, 8, controller.signal);
        if (!active) {
          return;
        }
        setResults(payload.items ?? []);
        setOpen(true);
      } catch {
        if (controller.signal.aborted) {
          return;
        }
        if (!active) {
          return;
        }
        setResults([]);
        setError("Busca indisponivel agora.");
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }, 250);

    return () => {
      active = false;
      controller.abort();
      window.clearTimeout(timeout);
    };
  }, [normalizedQuery]);

  useEffect(() => {
    function onClick(event: MouseEvent) {
      if (!containerRef.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    }
    window.addEventListener("mousedown", onClick);
    return () => window.removeEventListener("mousedown", onClick);
  }, []);

  return (
    <div className="relative w-full" ref={containerRef}>
      <div className="flex items-center gap-2 rounded-md border border-slate-300 bg-white px-3 py-2 shadow-sm focus-within:border-slate-500 dark:border-slate-700 dark:bg-slate-900 dark:focus-within:border-slate-500">
        <Search className="h-4 w-4 text-slate-400" />
        <input
          aria-label="Busca nacional"
          className="min-w-0 flex-1 bg-transparent text-sm text-slate-900 outline-none placeholder:text-slate-400 dark:text-white"
          onChange={(event) => setQuery(event.target.value)}
          onFocus={() => setOpen(true)}
          placeholder="Buscar politico, empresa, CNPJ..."
          value={query}
        />
        {query ? (
          <button
            aria-label="Limpar busca"
            className="rounded p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600 dark:hover:bg-slate-800 dark:hover:text-slate-200"
            onClick={() => {
              setQuery("");
              setOpen(false);
            }}
            type="button"
          >
            <X className="h-4 w-4" />
          </button>
        ) : null}
      </div>

      {open && normalizedQuery.length >= 2 ? (
        <div className="absolute left-0 right-0 z-50 mt-2 overflow-hidden rounded-lg border border-slate-200 bg-white shadow-xl dark:border-slate-800 dark:bg-slate-950">
          {loading ? (
            <div className="space-y-2 px-4 py-3" aria-live="polite">
              <div className="h-3 w-28 animate-pulse rounded bg-slate-200 dark:bg-slate-800" />
              <div className="h-3 w-48 animate-pulse rounded bg-slate-200 dark:bg-slate-800" />
            </div>
          ) : null}
          {error ? (
            <div className="px-4 py-3 text-sm text-red-600 dark:text-red-300">
              {error}
            </div>
          ) : null}
          {!loading && !error && results.length === 0 ? (
            <div className="px-4 py-3 text-sm text-slate-500 dark:text-slate-400">
              Nenhum resultado encontrado.
            </div>
          ) : null}
          {!error && results.length ? (
            <div className="max-h-96 divide-y divide-slate-100 overflow-y-auto dark:divide-slate-800">
              {results.map((item) => (
                <Link
                  className="block px-4 py-3 hover:bg-slate-50 dark:hover:bg-slate-900"
                  href={item.href}
                  key={`${item.entity_type}-${item.id}`}
                  onClick={() => setOpen(false)}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-semibold text-slate-950 dark:text-white">
                        {item.label}
                      </p>
                      <p className="mt-1 truncate text-xs text-slate-500 dark:text-slate-400">
                        {item.subtitle || entityLabel(item.entity_type)}
                      </p>
                    </div>
                    <span className="shrink-0 rounded-full bg-slate-100 px-2 py-1 text-xs font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                      {entityLabel(item.entity_type)}
                    </span>
                  </div>
                </Link>
              ))}
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

function entityLabel(value: string) {
  const labels: Record<string, string> = {
    person: "Politico",
    company: "Empresa",
    contract: "Contrato",
    organization: "Orgao",
  };
  return labels[value] ?? "Entidade";
}
