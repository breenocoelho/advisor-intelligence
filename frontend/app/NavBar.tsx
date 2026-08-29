"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { UserButton } from "@clerk/nextjs";

const NAV_ITEMS = [
  { href: "/", label: "Today" },
  { href: "/clientes", label: "Clientes" },
  { href: "/ativos", label: "Ativos" },
  { href: "/assessores", label: "Assessores" },
  { href: "/oportunidades", label: "Oportunidades" },
  { href: "/escritorio", label: "Escritório" },
  { href: "/tarefas", label: "Tarefas" },
  { href: "/alertas", label: "Histórico" },
  { href: "/config/thresholds", label: "Config" },
];

export default function NavBar() {
  const pathname = usePathname();

  return (
    <nav className="border-b border-[#14181F]/10 bg-white">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-3">
        <div className="flex items-center gap-6">
          <span className="font-display text-sm font-semibold tracking-tight">
            Advisor Intelligence
          </span>
          <div className="flex items-center gap-1">
            {NAV_ITEMS.map((item) => {
              const isActive =
                item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`rounded-md px-3 py-1.5 text-sm font-medium transition ${
                    isActive
                      ? "bg-[#14181F] text-white"
                      : "text-[#14181F]/60 hover:bg-[#14181F]/5 hover:text-[#14181F]"
                  }`}
                >
                  {item.label}
                </Link>
              );
            })}
          </div>
        </div>
        <UserButton />
      </div>
    </nav>
  );
}