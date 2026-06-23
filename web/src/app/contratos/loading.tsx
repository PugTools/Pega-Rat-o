export default function LoadingContratos() {
  return (
    <div className="mx-auto max-w-7xl animate-pulse">
      <div className="mb-6">
        <div className="h-4 w-56 rounded bg-slate-200" />
        <div className="mt-2 h-8 w-44 rounded bg-slate-200" />
      </div>
      <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
        {Array.from({ length: 7 }).map((_, index) => (
          <div
            className="grid grid-cols-4 gap-4 border-b border-slate-100 px-4 py-4 last:border-b-0"
            key={index}
          >
            <div className="h-4 rounded bg-slate-200" />
            <div className="h-4 rounded bg-slate-200" />
            <div className="h-4 rounded bg-slate-200" />
            <div className="h-4 rounded bg-slate-200" />
          </div>
        ))}
      </div>
    </div>
  );
}
