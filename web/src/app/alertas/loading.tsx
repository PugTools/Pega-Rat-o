export default function LoadingAlertas() {
  return (
    <div className="mx-auto max-w-7xl animate-pulse">
      <div className="mb-6">
        <div className="h-4 w-52 rounded bg-slate-200" />
        <div className="mt-2 h-8 w-36 rounded bg-slate-200" />
      </div>
      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.15fr)_minmax(360px,0.85fr)]">
        <div className="h-96 rounded-lg border border-slate-200 bg-white" />
        <div className="h-96 rounded-lg border border-slate-200 bg-white" />
      </div>
    </div>
  );
}
