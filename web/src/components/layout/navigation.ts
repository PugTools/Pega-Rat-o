import {
  Bell,
  Building2,
  Gauge,
  Info,
  Settings,
  Users,
} from "lucide-react";

export const navigationGroups = [
  {
    label: "Visao",
    items: [{ label: "Dashboard", href: "/", icon: Gauge }],
  },
  {
    label: "Investigacao",
    items: [
      { label: "Politicos", href: "/politicos", icon: Users },
      { label: "Contratos", href: "/contratos", icon: Building2 },
      { label: "Alertas", href: "/alertas", icon: Bell },
    ],
  },
  {
    label: "Sistema",
    items: [
      { label: "Admin", href: "/admin", icon: Settings },
      { label: "Sobre", href: "/sobre", icon: Info },
    ],
  },
];
