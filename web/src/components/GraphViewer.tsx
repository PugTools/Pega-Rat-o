"use client";

import dynamic from "next/dynamic";
import { memo, useEffect, useMemo, useState } from "react";
import { api, type EntityGraph } from "@/lib/api";

const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), {
  ssr: false,
  loading: () => (
    <div className="grid h-full place-items-center p-6 text-sm text-slate-500">
      Carregando grafo...
    </div>
  ),
});

type GraphViewerProps = {
  entityType: string;
  entityId: string;
};

type ForceNode = {
  id: string;
  label: string;
  name: string;
  color: string;
  x?: number;
  y?: number;
};

type ForceLink = {
  source: string | ForceNode;
  target: string | ForceNode;
  type: string;
};

export const GraphViewer = memo(function GraphViewer({ entityType, entityId }: GraphViewerProps) {
  const [graph, setGraph] = useState<EntityGraph>({ nodes: [], edges: [] });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    setLoading(true);

    api
      .getEntityGraph(entityType, entityId)
      .then((payload) => {
        if (mounted) {
          setGraph(payload);
        }
      })
      .catch(() => {
        if (mounted) {
          setGraph({ nodes: [], edges: [] });
        }
      })
      .finally(() => {
        if (mounted) {
          setLoading(false);
        }
      });

    return () => {
      mounted = false;
    };
  }, [entityType, entityId]);

  const forceData = useMemo(
    () => ({
      nodes: graph.nodes.map<ForceNode>((node) => ({
        id: node.id,
        label: node.label,
        name: nodeName(node.properties, node.label),
        color: nodeColor(node.label),
      })),
      links: graph.edges.map<ForceLink>((edge) => ({
        source: edge.source,
        target: edge.target,
        type: edge.type,
      })),
    }),
    [graph],
  );

  return (
    <section className="rounded-lg border border-slate-200 bg-white shadow-sm">
      <div className="border-b border-slate-200 px-5 py-4">
        <h3 className="text-base font-semibold text-slate-950">
          Rede de Conexoes
        </h3>
        <p className="mt-1 text-sm text-slate-500">
          {entityType}:{entityId}
        </p>
      </div>

      <div className="h-[420px]">
        {loading ? (
          <div className="grid h-full place-items-center p-6">
            <div className="grid w-full max-w-sm gap-3">
              <div className="mx-auto h-16 w-16 animate-pulse rounded-full bg-slate-200" />
              <div className="h-3 animate-pulse rounded bg-slate-200" />
              <div className="mx-auto h-3 w-2/3 animate-pulse rounded bg-slate-200" />
            </div>
          </div>
        ) : forceData.nodes.length === 0 ? (
          <div className="flex h-full items-center justify-center text-sm text-slate-500">
            Nenhuma conexao encontrada.
          </div>
        ) : (
          <ForceGraph2D
            graphData={forceData}
            linkColor={() => "#94a3b8"}
            linkDirectionalArrowLength={4}
            linkDirectionalArrowRelPos={1}
            linkLabel={(link) => (link as ForceLink).type}
            nodeAutoColorBy="label"
            nodeCanvasObject={(node, ctx, globalScale) => {
              const graphNode = node as ForceNode;
              const label = graphNode.name;
              const fontSize = 12 / globalScale;
              ctx.beginPath();
              ctx.arc(graphNode.x ?? 0, graphNode.y ?? 0, 7, 0, 2 * Math.PI, false);
              ctx.fillStyle = graphNode.color;
              ctx.fill();
              ctx.font = `${fontSize}px Arial`;
              ctx.fillStyle = "#0f172a";
              ctx.fillText(label, (graphNode.x ?? 0) + 9, (graphNode.y ?? 0) + 4);
            }}
            nodeLabel={(node) => {
              const graphNode = node as ForceNode;
              return `${graphNode.label}: ${graphNode.name}`;
            }}
          />
        )}
      </div>
    </section>
  );
});

function nodeColor(label: string) {
  const colors: Record<string, string> = {
    Person: "#2563eb",
    Company: "#16a34a",
    Organization: "#7c3aed",
    Contract: "#d97706",
  };
  return colors[label] ?? "#64748b";
}

function nodeName(properties: Record<string, unknown>, fallback: string) {
  const value =
    properties.full_name ??
    properties.legal_name ??
    properties.name ??
    properties.contract_number ??
    properties.id ??
    fallback;
  return String(value);
}
