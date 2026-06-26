import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

type Tone = "neutral" | "success" | "warning" | "danger";

const toneClasses: Record<Tone, string> = {
  neutral:
    "border-slate-200 bg-white text-slate-900 dark:border-slate-800 dark:bg-slate-950 dark:text-white",
  success:
    "border-emerald-200 bg-emerald-50 text-emerald-900 dark:border-emerald-900 dark:bg-emerald-950/40 dark:text-emerald-100",
  warning:
    "border-amber-200 bg-amber-50 text-amber-900 dark:border-amber-900 dark:bg-amber-950/40 dark:text-amber-100",
  danger:
    "border-red-200 bg-red-50 text-red-900 dark:border-red-900 dark:bg-red-950/40 dark:text-red-100",
};

export function PageHeader({
  actions,
  description,
  eyebrow,
  status,
  title,
}: {
  actions?: ReactNode;
  description?: string;
  eyebrow?: string;
  status?: { label: string; tone?: Tone };
  title: string;
}) {
  return (
    <header className="mb-6 border-b border-slate-200 pb-5 dark:border-slate-800">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div className="min-w-0">
          {eyebrow ? (
            <p className="text-sm font-medium text-slate-500 dark:text-slate-400">
              {eyebrow}
            </p>
          ) : null}
          <h2 className="mt-1 text-2xl font-semibold tracking-tight text-slate-950 dark:text-white">
            {title}
          </h2>
          {description ? (
            <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600 dark:text-slate-300">
              {description}
            </p>
          ) : null}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {status ? (
            <span
              className={`w-fit rounded-md border px-3 py-2 text-xs font-semibold ${
                toneClasses[status.tone ?? "neutral"]
              }`}
            >
              {status.label}
            </span>
          ) : null}
          {actions}
        </div>
      </div>
    </header>
  );
}

export function ModuleCard({
  actions,
  children,
  description,
  icon: Icon,
  title,
}: {
  actions?: ReactNode;
  children: ReactNode;
  description?: string;
  icon?: LucideIcon;
  title?: string;
}) {
  return (
    <section className="rounded-lg border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-950">
      {title || description || Icon || actions ? (
        <div className="flex flex-col gap-3 border-b border-slate-200 px-5 py-4 dark:border-slate-800 sm:flex-row sm:items-start sm:justify-between">
          <div className="flex min-w-0 gap-3">
            {Icon ? (
              <div className="mt-0.5 rounded-md bg-slate-100 p-2 text-slate-700 dark:bg-slate-800 dark:text-slate-200">
                <Icon className="h-4 w-4" />
              </div>
            ) : null}
            <div className="min-w-0">
              {title ? (
                <h3 className="text-base font-semibold text-slate-950 dark:text-white">
                  {title}
                </h3>
              ) : null}
              {description ? (
                <p className="mt-1 text-sm leading-6 text-slate-500 dark:text-slate-400">
                  {description}
                </p>
              ) : null}
            </div>
          </div>
          {actions}
        </div>
      ) : null}
      <div className="p-5">{children}</div>
    </section>
  );
}

export function MetricTile({
  detail,
  icon: Icon,
  label,
  tone = "neutral",
  value,
}: {
  detail?: string;
  icon?: LucideIcon;
  label: string;
  tone?: Tone;
  value: string;
}) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-950">
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm font-medium text-slate-500 dark:text-slate-400">{label}</p>
        {Icon ? (
          <div className={`rounded-md border p-2 ${toneClasses[tone]}`}>
            <Icon className="h-4 w-4" />
          </div>
        ) : null}
      </div>
      <p className="mt-3 text-2xl font-semibold text-slate-950 dark:text-white">
        {value}
      </p>
      {detail ? (
        <p className="mt-1 text-xs leading-5 text-slate-500 dark:text-slate-400">
          {detail}
        </p>
      ) : null}
    </div>
  );
}

export function StatusCallout({
  message,
  title,
  tone = "neutral",
}: {
  message: string;
  title: string;
  tone?: Tone;
}) {
  return (
    <div className={`rounded-lg border px-4 py-3 text-sm ${toneClasses[tone]}`}>
      <p className="font-semibold">{title}</p>
      <p className="mt-1 leading-6 opacity-85">{message}</p>
    </div>
  );
}
