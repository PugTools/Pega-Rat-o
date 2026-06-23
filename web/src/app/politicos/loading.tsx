import { PoliticoProfileSkeleton } from "@/components/PoliticoProfile";

export default function LoadingPoliticos() {
  return (
    <div className="mx-auto max-w-7xl">
      <div className="mb-6">
        <div className="h-4 w-44 animate-pulse rounded bg-slate-200" />
        <div className="mt-2 h-8 w-40 animate-pulse rounded bg-slate-200" />
      </div>
      <PoliticoProfileSkeleton />
    </div>
  );
}
