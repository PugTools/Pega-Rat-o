import { ThemeToggle } from "@/components/layout/ThemeToggle";
import { GlobalSearch } from "@/components/GlobalSearch";
import { NavigationLinks } from "@/components/layout/NavigationLinks";

export function Sidebar() {
  return (
    <aside className="hidden min-h-screen w-64 border-r border-slate-200 bg-white px-5 py-6 print:hidden dark:border-slate-800 dark:bg-slate-950 lg:block">
      <div className="mb-8 flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
            ONGP
          </p>
          <h1 className="mt-2 text-lg font-semibold text-slate-950 dark:text-white">PEGA RATAO</h1>
        </div>
        <ThemeToggle />
      </div>

      <div className="mb-6">
        <GlobalSearch />
      </div>

      <NavigationLinks />
    </aside>
  );
}
