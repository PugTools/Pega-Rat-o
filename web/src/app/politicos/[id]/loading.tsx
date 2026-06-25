export default function PoliticoDetailLoading() {
  return (
    <main className="mx-auto max-w-5xl animate-pulse">
      <div className="mb-6 flex items-end justify-between border-b border-slate-200 pb-5 dark:border-slate-800">
        <div>
          <div className="h-4 w-36 rounded bg-slate-200 dark:bg-slate-800" />
          <div className="mt-3 h-8 w-64 rounded bg-slate-200 dark:bg-slate-800" />
        </div>
        <div className="h-10 w-36 rounded bg-slate-200 dark:bg-slate-800" />
      </div>

      <section className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <div className="flex gap-5">
          <div className="h-28 w-28 rounded-lg bg-slate-200 dark:bg-slate-800" />
          <div className="flex-1">
            <div className="h-4 w-40 rounded bg-slate-200 dark:bg-slate-800" />
            <div className="mt-3 h-9 w-96 max-w-full rounded bg-slate-200 dark:bg-slate-800" />
            <div className="mt-4 flex gap-2">
              <div className="h-7 w-24 rounded bg-slate-200 dark:bg-slate-800" />
              <div className="h-7 w-20 rounded bg-slate-200 dark:bg-slate-800" />
              <div className="h-7 w-28 rounded bg-slate-200 dark:bg-slate-800" />
            </div>
          </div>
        </div>
      </section>

      <section className="mt-5 grid gap-4 md:grid-cols-3">
        {Array.from({ length: 3 }).map((_, index) => (
          <div
            className="h-28 rounded-lg border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900"
            key={index}
          />
        ))}
      </section>

      <section className="mt-5 grid gap-4">
        {Array.from({ length: 3 }).map((_, index) => (
          <div
            className="h-36 rounded-lg border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900"
            key={index}
          />
        ))}
      </section>
    </main>
  );
}
