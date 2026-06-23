"use client";

import { Printer } from "lucide-react";

export function PrintReportButton({ label = "Imprimir relatorio" }: { label?: string }) {
  return (
    <button
      className="inline-flex items-center gap-2 rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 print:hidden"
      onClick={() => window.print()}
      type="button"
    >
      <Printer className="h-4 w-4" />
      {label}
    </button>
  );
}
