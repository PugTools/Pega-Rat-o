import { ThemeToggle } from "@/components/layout/ThemeToggle";
import { GlobalSearch } from "@/components/GlobalSearch";
import { NavigationLinks } from "@/components/layout/NavigationLinks";

export function Navbar() {
  return (
    <header className="border-b border-slate-200 bg-white print:hidden dark:border-slate-800 dark:bg-slate-950 lg:hidden">
      <div className="flex items-center justify-between px-4 py-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
            ONGP
          </p>
          <h1 className="text-base font-semibold text-slate-950 dark:text-white">PEGA RATAO</h1>
        </div>
        <ThemeToggle />
      </div>
      <div className="px-4 pb-3">
        <GlobalSearch />
      </div>
      <NavigationLinks compact />
    </header>
  );
}
