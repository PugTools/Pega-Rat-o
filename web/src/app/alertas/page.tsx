import { DashboardIntelligence } from "@/components/DashboardIntelligence";
import { PageHeader } from "@/components/ui/Primitives";

export default function AlertasPage() {
  return (
    <div className="mx-auto max-w-7xl">
      <PageHeader
        description="Fila de sinais de risco gerados por regras, grafo e enriquecimentos. Use categoria, severidade e status para priorizar a auditoria."
        eyebrow="Monitoramento automatizado"
        status={{ label: "Paginado por prioridade", tone: "success" }}
        title="Alertas"
      />

      <DashboardIntelligence />
    </div>
  );
}
