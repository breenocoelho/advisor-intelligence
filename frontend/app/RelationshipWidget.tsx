"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

export type RelationshipItem = {
  id: string;
  name: string;
  days_since_contact: number | null;
  cadence_days: number;
  status: "overdue" | "approaching" | "ok";
};

export type RelationshipStatusFilter = "overdue" | "approaching" | "ok" | "problem" | null;

const PAGE_SIZE = 10;
const STATUS_ORDER: Record<string, number> = { overdue: 0, approaching: 1, ok: 2 };
const STATUS_ICON: Record<string, string> = { overdue: "🔴", approaching: "🟡", ok: "🟢" };

export default function RelationshipWidget({
  items,
  statusFilter,
  onStatusFilterChange,
}: {
  items: RelationshipItem[];
  statusFilter: RelationshipStatusFilter;
  onStatusFilterChange: (filter: RelationshipStatusFilter) => void;
}) {
  const [page, setPage] = useState(1);

  useEffect(() => {
    setPage(1);
  }, [statusFilter]);

  const overdue = items.filter((r) => r.status === "overdue");
  const approaching = items.filter((r) => r.status === "approaching");
  const upToDate = items.filter((r) => r.status === "ok");

  const filtered =
    !statusFilter ? items : statusFilter === "problem" ? items.filter((r) => r.status !== "ok") : items.filter((r) => r.status === statusFilter);
  const sorted = [...filtered].sort((a, b) => {
    if (STATUS_ORDER[a.status] !== STATUS_ORDER[b.status]) return STATUS_ORDER[a.status] - STATUS_ORDER[b.status];
    return (b.days_since_contact ?? 0) - (a.days_since_contact ?? 0);
  });

  const totalPages = Math.max(1, Math.ceil(sorted.length / PAGE_SIZE));
  const safePage = Math.min(page, totalPages);
  const paged = sorted.slice((safePage - 1) * PAGE_SIZE, safePage * PAGE_SIZE);

  function selectStatus(status: "overdue" | "approaching" | "ok") {
    onStatusFilterChange(statusFilter === status ? null : status);
  }

  return (
    <section className="card p-4">
      <div className="mb-3 flex items-center justify-between">
        <div className="flex flex-wrap gap-2 text-sm">
          <button
            onClick={() => selectStatus("overdue")}
            className={`rounded-md px-2 py-1 transition ${
              statusFilter === "overdue" || statusFilter === "problem"
                ? "bg-[#B23A48]/10 ring-1 ring-[#B23A48]/40"
                : "hover:bg-[#14181F]/5"
            }`}
          >
            🔴 {overdue.length} clients overdue
          </button>
          <button
            onClick={() => selectStatus("approaching")}
            className={`rounded-md px-2 py-1 transition ${
              statusFilter === "approaching" || statusFilter === "problem"
                ? "bg-[#A6790A]/10 ring-1 ring-[#A6790A]/40"
                : "hover:bg-[#14181F]/5"
            }`}
          >
            🟡 {approaching.length} clients approaching cadence
          </button>
          <button
            onClick={() => selectStatus("ok")}
            className={`rounded-md px-2 py-1 transition ${
              statusFilter === "ok" ? "bg-[#3F7D5B]/10 ring-1 ring-[#3F7D5B]/40" : "hover:bg-[#14181F]/5"
            }`}
          >
            🟢 {upToDate.length} clients up to date
          </button>
        </div>
        {statusFilter && (
          <button
            onClick={() => onStatusFilterChange(null)}
            className="shrink-0 text-xs font-medium text-[#14181F]/40 hover:text-[#14181F]/70"
          >
            Limpar filtro
          </button>
        )}
      </div>

      {sorted.length === 0 ? (
        <p className="text-sm text-[#14181F]/50">Nenhum cliente nesse filtro.</p>
      ) : (
        <>
          <ol className="grid min-h-[9.5rem] grid-cols-1 gap-x-6 gap-y-1.5 sm:grid-cols-2">
            {paged.map((r, i) => (
              <li key={r.id} className="flex items-center justify-between text-sm">
                <span className="min-w-0 truncate">
                  {(safePage - 1) * PAGE_SIZE + i + 1}.{" "}
                  <Link href={`/clientes/${r.id}`} className="font-medium hover:underline">
                    {r.name}
                  </Link>
                  <span className="ml-2">{STATUS_ICON[r.status]}</span>
                </span>
                <span className="shrink-0 font-mono text-xs tabular-nums text-[#14181F]/50">
                  {r.days_since_contact !== null ? `${r.days_since_contact} dias` : "sem contato"}
                </span>
              </li>
            ))}
          </ol>
          {totalPages > 1 && (
            <div className="mt-3 flex items-center justify-between border-t border-[#14181F]/10 pt-3">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={safePage <= 1}
                className="rounded-md border border-[#14181F]/15 px-2 py-1 text-xs font-medium text-[#14181F]/70 transition hover:bg-[#14181F]/5 disabled:opacity-40"
              >
                ← Anterior
              </button>
              <span className="font-mono text-xs tabular-nums text-[#14181F]/50">
                Página {safePage} de {totalPages}
              </span>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={safePage >= totalPages}
                className="rounded-md border border-[#14181F]/15 px-2 py-1 text-xs font-medium text-[#14181F]/70 transition hover:bg-[#14181F]/5 disabled:opacity-40"
              >
                Próxima →
              </button>
            </div>
          )}
        </>
      )}
    </section>
  );
}
