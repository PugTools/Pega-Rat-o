type RiskScoreBadgeProps = {
  score: string | number | null | undefined;
  compact?: boolean;
};

export function RiskScoreBadge({ score, compact = false }: RiskScoreBadgeProps) {
  const numericScore = normalizeScore(score);
  const tone = scoreTone(numericScore);

  return (
    <div className={compact ? "min-w-24" : "min-w-36"}>
      <div className="flex items-center justify-between gap-3">
        <span className={`text-xs font-semibold ${tone.text}`}>{tone.label}</span>
        <span className="font-mono text-xs font-semibold text-slate-700 dark:text-slate-200">
          {numericScore.toFixed(0)}
        </span>
      </div>
      <div className="mt-1 h-2 overflow-hidden rounded-full bg-slate-200 dark:bg-slate-800">
        <div
          className={`h-full rounded-full ${tone.bar}`}
          style={{ width: `${Math.max(0, Math.min(100, numericScore))}%` }}
        />
      </div>
    </div>
  );
}

function normalizeScore(score: string | number | null | undefined) {
  const parsed = Number(score ?? 0);
  if (!Number.isFinite(parsed)) {
    return 0;
  }
  return Math.max(0, Math.min(100, parsed));
}

function scoreTone(score: number) {
  if (score <= 30) {
    return {
      label: "Baixo",
      text: "text-emerald-700 dark:text-emerald-300",
      bar: "bg-emerald-500",
    };
  }
  if (score <= 60) {
    return {
      label: "Medio",
      text: "text-yellow-700 dark:text-yellow-300",
      bar: "bg-yellow-500",
    };
  }
  if (score <= 80) {
    return {
      label: "Alto",
      text: "text-orange-700 dark:text-orange-300",
      bar: "bg-orange-500",
    };
  }
  return {
    label: "Critico",
    text: "text-red-700 dark:text-red-300",
    bar: "bg-red-600",
  };
}
