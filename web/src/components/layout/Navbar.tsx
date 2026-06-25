import { ThemeToggle } from "@/components/layout/ThemeToggle";
import { GlobalSearch } from "@/components/GlobalSearch";

const navigation = [
  { label: "Dashboard", href: "/" },
  { label: "Politicos", href: "/politicos" },
  { label: "Contratos", href: "/contratos" },
  { label: "Alertas", href: "/alertas" },
  { label: "Sobre", href: "/sobre" },
  { label: "Admin", href: "/admin" },
];

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
      <nav className="flex gap-1 overflow-x-auto px-3 pb-3">
        {navigation.map((item) => (
          <a
            className="shrink-0 rounded-md px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-slate-800"
            href={item.href}
            key={item.label}
          >
            {item.label}
          </a>
        ))}
      </nav>
    </header>
  );
}
