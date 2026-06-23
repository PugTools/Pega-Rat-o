import { DashboardIntelligence } from "@/components/DashboardIntelligence";

export default function AlertasPage() {
  return (
    <div className="mx-auto max-w-7xl">
      <div className="mb-6">
        <p className="text-sm font-medium text-slate-500">
          Monitoramento automatizado
        </p>
        <h2 className="mt-1 text-2xl font-semibold text-slate-950">Alertas</h2>
      </div>

      <DashboardIntelligence />
    </div>
  );
}
