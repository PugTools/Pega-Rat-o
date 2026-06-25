"use client";

import { ExternalLink, FileSearch, ShieldAlert } from "lucide-react";
import { memo, useMemo, useState } from "react";
import type { RiskAlert } from "@/lib/api";
import { RiskScoreBadge } from "@/components/RiskScoreBadge";

type RiskAlertCardProps = {
  alert: RiskAlert;
};

export const RiskAlertCard = memo(function RiskAlertCard({ alert }: RiskAlertCardProps) {
  const [expanded, setExpanded] = useState(false);
  const evidence = useMemo(() => normalizeEvidence(alert.evidence), [alert.evidence]);
  const evidenceUrl = useMemo(() => findEvidenceUrl(evidence), [evidence]);
  const evidenceText = useMemo(() => safeJson(evidence), [evidence]);
  const title = String(alert.title ?? "").trim() || "Sinal de risco para auditoria";
  const explanation =
    String(alert.explanation ?? "").trim() ||
    "O motor de risco apontou uma conexao relevante para auditoria.";

  return (
    <article className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-950">
      <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
        <div className="flex gap-3">
          <div className="rounded-md bg-red-50 p-2 text-red-700 dark:bg-red-950/50 dark:text-red-300">
            <ShieldAlert className="h-5 w-5" />
          </div>
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h4 className="font-semibold text-slate-950 dark:text-white">
                {title}
              </h4>
              <span className="rounded-full bg-slate-100 px-2 py-1 text-xs font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                {severityLabel(alert.severity)}
              </span>
            </div>
            <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">
              <span className="font-semibold text-slate-800 dark:text-slate-100">
                Explicabilidade da IA:
              </span>{" "}
              {explanation}
            </p>
          </div>
        </div>
        <RiskScoreBadge score={alert.score} />
      </div>

      {expanded ? (
        <pre className="mt-4 max-h-80 overflow-auto rounded-lg bg-slate-950 p-4 text-xs leading-6 text-slate-100">
          {evidenceText}
        </pre>
      ) : null}

      <div className="mt-4 flex flex-wrap justify-end gap-2">
        <button
          className="inline-flex items-center gap-2 rounded-md border border-slate-300 px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-900"
          onClick={() => setExpanded((value) => !value)}
          type="button"
        >
          <FileSearch className="h-4 w-4" />
          Ver Evidencias
        </button>
        {evidenceUrl ? (
          <a
            className="inline-flex items-center gap-2 rounded-md border border-slate-300 px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-900"
            href={evidenceUrl}
            rel="noreferrer"
            target="_blank"
          >
            <ExternalLink className="h-4 w-4" />
            Ver Nota Fiscal
          </a>
        ) : null}
      </div>
    </article>
  );
});

function severityLabel(value: string) {
  const labels: Record<string, string> = {
    critical: "Critico",
    high: "Alto",
    medium: "Medio",
    low: "Baixo",
  };
  const normalized = String(value || "").toLowerCase();
  return labels[normalized] ?? normalized || "Risco";
}

function normalizeEvidence(value: unknown): Record<string, unknown> {
  if (!value) {
    return {};
  }
  if (typeof value === "object" && !Array.isArray(value)) {
    return value as Record<string, unknown>;
  }
  return { value };
}

function safeJson(value: unknown) {
  try {
    return JSON.stringify(value ?? {}, null, 2);
  } catch {
    return JSON.stringify({ error: "Evidencia indisponivel para serializacao" }, null, 2);
  }
}

function findEvidenceUrl(evidence: Record<string, unknown>) {
  if (!evidence) {
    return null;
  }
  for (const key of ["document_url", "official_url", "url", "source_url", "nota_fiscal_url"]) {
    const value = evidence[key];
    if (typeof value === "string" && value.startsWith("http")) {
      return value;
    }
  }
  return null;
}
