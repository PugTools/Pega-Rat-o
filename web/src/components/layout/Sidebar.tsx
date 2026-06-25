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

      <nav className="space-y-1">
        {navigation.map((item) => (
          <a
            className="block rounded-md px-3 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100 hover:text-slate-950 dark:text-slate-200 dark:hover:bg-slate-800 dark:hover:text-white"
            href={item.href}
            key={item.label}
          >
            {item.label}
          </a>
        ))}
      </nav>
    </aside>
  );
}
