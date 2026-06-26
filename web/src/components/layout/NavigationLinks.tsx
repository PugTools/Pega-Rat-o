"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { navigationGroups } from "@/components/layout/navigation";

export function NavigationLinks({ compact = false }: { compact?: boolean }) {
  const pathname = usePathname();

  if (compact) {
    return (
      <nav className="flex gap-1 overflow-x-auto px-3 pb-3">
        {navigationGroups.flatMap((group) =>
          group.items.map((item) => {
            const Icon = item.icon;
            const active = isActive(pathname, item.href);
            return (
              <Link
                className={`inline-flex shrink-0 items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition ${
                  active
                    ? "bg-slate-950 text-white dark:bg-white dark:text-slate-950"
                    : "text-slate-700 hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-slate-800"
                }`}
                href={item.href}
                key={item.href}
              >
                <Icon className="h-4 w-4" />
                {item.label}
              </Link>
            );
          }),
        )}
      </nav>
    );
  }

  return (
    <nav className="space-y-6">
      {navigationGroups.map((group) => (
        <div key={group.label}>
          <p className="mb-2 px-3 text-[11px] font-semibold uppercase tracking-wide text-slate-400">
            {group.label}
          </p>
          <div className="space-y-1">
            {group.items.map((item) => {
              const Icon = item.icon;
              const active = isActive(pathname, item.href);
              return (
                <Link
                  className={`flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition ${
                    active
                      ? "bg-slate-950 text-white dark:bg-white dark:text-slate-950"
                      : "text-slate-700 hover:bg-slate-100 hover:text-slate-950 dark:text-slate-200 dark:hover:bg-slate-800 dark:hover:text-white"
                  }`}
                  href={item.href}
                  key={item.href}
                >
                  <Icon className="h-4 w-4" />
                  {item.label}
                </Link>
              );
            })}
          </div>
        </div>
      ))}
    </nav>
  );
}

function isActive(pathname: string, href: string) {
  if (href === "/") {
    return pathname === "/";
  }
  return pathname === href || pathname.startsWith(`${href}/`);
}
