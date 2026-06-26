"use client";

import { useEffect, useState } from "react";
import { api, type RiskSettings } from "@/lib/api";
import { StatusCallout } from "@/components/ui/Primitives";

const fieldLabels: Record<keyof RiskSettings, string> = {
  expense_fragmentation_legal_limit: "Limite de fracionamento",
  expense_fragmentation_minimum_count: "Quantidade minima",
  expense_fragmentation_window_days: "Janela em dias",
  supplier_concentration_threshold: "Concentracao de fornecedor",
  supplier_concentration_minimum_total_amount: "Valor minimo concentracao",
  abnormal_growth_threshold: "Crescimento anormal",
  abnormal_growth_minimum_history: "Historico minimo",
};

export function BackofficeSettings() {
  const [settings, setSettings] = useState<RiskSettings | null>(null);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .getRiskSettings()
      .then((payload) => {
        setSettings(payload);
        setError(null);
      })
      .catch(() => {
        setError("API de calibragem indisponivel. Exibindo valores padrao para referencia.");
        setSettings({
          expense_fragmentation_legal_limit: "50000.00",
          expense_fragmentation_minimum_count: 3,
          expense_fragmentation_window_days: 30,
          supplier_concentration_threshold: "0.70",
          supplier_concentration_minimum_total_amount: "100000.00",
          abnormal_growth_threshold: "3.00",
          abnormal_growth_minimum_history: 3,
        });
      });
  }, []);

  async function save() {
    if (!settings) {
      return;
    }
    try {
      const updated = await api.updateRiskSettings(settings);
      setSettings(updated);
      setSaved(true);
      setError(null);
      window.setTimeout(() => setSaved(false), 2500);
    } catch {
      setError("Nao foi possivel salvar agora. Verifique autenticacao e disponibilidade da API.");
    }
  }

  if (!settings) {
    return (
      <section className="rounded-lg border border-slate-200 bg-white p-5 text-sm text-slate-500 shadow-sm dark:border-slate-800 dark:bg-slate-950 dark:text-slate-400">
        Carregando calibragem...
      </section>
    );
  }

  return (
    <section className="rounded-lg border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-950">
      <div className="border-b border-slate-200 px-5 py-4 dark:border-slate-800">
        <h3 className="text-base font-semibold text-slate-950 dark:text-white">
          Calibragem do Motor de Risco
        </h3>
        <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
          Ajustes operacionais aplicados em tempo de execucao
        </p>
      </div>
      {error ? (
        <div className="px-5 pt-5">
          <StatusCallout message={error} title="Atencao" tone="warning" />
        </div>
      ) : null}
      <div className="grid gap-4 p-5 md:grid-cols-2">
        {(Object.keys(settings) as Array<keyof RiskSettings>).map((key) => (
          <label className="block" key={key}>
            <span className="text-sm font-medium text-slate-700 dark:text-slate-200">{fieldLabels[key]}</span>
            <input
              className="mt-2 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-slate-500 dark:border-slate-700 dark:bg-slate-900 dark:text-white"
              onChange={(event) =>
                setSettings((current) =>
                  current
                    ? {
                        ...current,
                        [key]:
                          typeof current[key] === "number"
                            ? Number(event.target.value)
                            : event.target.value,
                      }
                    : current,
                )
              }
              value={settings[key]}
            />
          </label>
        ))}
      </div>
      <div className="flex items-center justify-between border-t border-slate-200 px-5 py-4 dark:border-slate-800">
        <span className="text-sm text-slate-500 dark:text-slate-400">
          {saved ? "Configuracoes salvas." : "Alteracoes exigem token autenticado."}
        </span>
        <button
          className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white dark:bg-white dark:text-slate-950"
          onClick={save}
          type="button"
        >
          Salvar
        </button>
      </div>
    </section>
  );
}
