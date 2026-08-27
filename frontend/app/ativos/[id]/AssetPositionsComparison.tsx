"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import Link from "next/link";
import SortableTh from "../../SortableTh";

type SortKey = "clientName" | "valueA" | "valueB" | "delta";

type ClientPosition = {
  client_id: string;
  client_name: string;
  market_value: number;
  quantity: number | null;
  pct_of_client_aum: number | null;
};

type Row = {
  clientId: string;
  clientName: string;
  valueA: number | null;
  valueB: number | null;
};

function formatCurrency(value: number | null): string {
  if (value === null) return "—";
  return value.toLocaleString("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 });
}

function formatDate(value: string): string {
  return new Date(value).toLocaleDateString("pt-BR");
}

export default function AssetPositionsComparison({
  assetId,
  availableDates,
}: {
  assetId: string;
  availableDates: string[];
}) {
  const { getToken } = useAuth();
  const [dateA, setDateA] = useState(availableDates[0]);
  const [dateB, setDateB] = useState(availableDates[availableDates.length - 1]);
  const [rows, setRows] = useState<Row[]>([]);
  const [loading, setLoading] = useState(true);
  const [sortKey, setSortKey] = useState<SortKey>("valueB");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      try {
        const token = await getToken();
        const headers: HeadersInit = token ? { Authorization: `Bearer ${token}` } : {};

        const [resA, resB] = await Promise.all([
          fetch(`${process.env.NEXT_PUBLIC_API_URL}/assets/${assetId}/positions-at?date=${dateA}`, { headers }),
          fetch(`${process.env.NEXT_PUBLIC_API_URL}/assets/${assetId}/positions-at?date=${dateB}`, { headers }),
        ]);

        const posA: ClientPosition[] = resA.ok ? await resA.json() : [];
        const posB: ClientPosition[] = resB.ok ? await resB.json() : [];

        const byClient = new Map<string, Row>();
        for (const p of posA) {
          byClient.set(p.client_id, {
            clientId: p.client_id,
            clientName: p.client_name,
            valueA: p.market_value,
            valueB: null,
          });
        }
        for (const p of posB) {
          const existing = byClient.get(p.client_id);
          if (existing) {
            existing.valueB = p.market_value;
          } else {
            byClient.set(p.client_id, {
              clientId: p.client_id,
              clientName: p.client_name,
              valueA: null,
              valueB: p.market_value,
            });
          }
        }

        if (!cancelled) setRows(Array.from(byClient.values()));
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [assetId, dateA, dateB, getToken]);

  if (availableDates.length === 0) return null;

  function handleSort(key: string) {
    if (key === sortKey) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key as SortKey);
      setSortDir(key === "clientName" ? "asc" : "desc");
    }
  }

  const sortedRows = [...rows].sort((a, b) => {
    let cmp = 0;
    if (sortKey === "clientName") cmp = a.clientName.localeCompare(b.clientName);
    else if (sortKey === "valueA") cmp = (a.valueA ?? 0) - (b.valueA ?? 0);
    else if (sortKey === "valueB") cmp = (a.valueB ?? 0) - (b.valueB ?? 0);
    else if (sortKey === "delta") cmp = (a.valueB ?? 0) - (a.valueA ?? 0) - ((b.valueB ?? 0) - (b.valueA ?? 0));
    return sortDir === "asc" ? cmp : -cmp;
  });

  return (
    <section className="mb-10">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-[#14181F]/70">
          Posições por cliente ({rows.length})
        </h2>
        <div className="flex items-center gap-2 text-sm">
          <select
            value={dateA}
            onChange={(e) => setDateA(e.target.value)}
            className="rounded-md border border-[#14181F]/15 px-2 py-1 font-mono text-xs tabular-nums focus:outline-none focus:ring-2 focus:ring-[#14181F]/20"
          >
            {availableDates.map((d) => (
              <option key={d} value={d}>
                {formatDate(d)}
              </option>
            ))}
          </select>
          <span className="text-[#14181F]/40">vs</span>
          <select
            value={dateB}
            onChange={(e) => setDateB(e.target.value)}
            className="rounded-md border border-[#14181F]/15 px-2 py-1 font-mono text-xs tabular-nums focus:outline-none focus:ring-2 focus:ring-[#14181F]/20"
          >
            {availableDates.map((d) => (
              <option key={d} value={d}>
                {formatDate(d)}
              </option>
            ))}
          </select>
        </div>
      </div>

      {loading ? (
        <p className="text-sm text-[#14181F]/50">Carregando posições...</p>
      ) : rows.length === 0 ? (
        <p className="text-sm text-[#14181F]/50">Nenhum cliente com posição nesse ativo.</p>
      ) : (
        <div className="overflow-hidden card">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[#14181F]/10 text-left text-xs uppercase tracking-wide text-[#14181F]/40">
                <SortableTh label="Cliente" sortKey="clientName" currentSort={sortKey} currentDir={sortDir} onSort={handleSort} />
                <SortableTh label={`PL (${formatDate(dateA)})`} sortKey="valueA" currentSort={sortKey} currentDir={sortDir} onSort={handleSort} align="right" />
                <SortableTh label={`PL (${formatDate(dateB)})`} sortKey="valueB" currentSort={sortKey} currentDir={sortDir} onSort={handleSort} align="right" />
                <SortableTh label="Δ" sortKey="delta" currentSort={sortKey} currentDir={sortDir} onSort={handleSort} align="right" />
              </tr>
            </thead>
            <tbody>
              {sortedRows.map((row) => {
                const a = row.valueA ?? 0;
                const b = row.valueB ?? 0;
                const delta = b - a;
                const deltaPct = a > 0 ? (delta / a) * 100 : null;
                const deltaColor = delta > 0 ? "#3F7D5B" : delta < 0 ? "#B23A48" : "#14181F66";
                return (
                  <tr key={row.clientId} className="border-b border-[#14181F]/5 last:border-0">
                    <td className="px-4 py-3">
                      <Link href={`/clientes/${row.clientId}`} className="font-medium hover:underline">
                        {row.clientName}
                      </Link>
                      {row.valueA === null && (
                        <p className="text-xs text-[#3F7D5B]">novo em {formatDate(dateB)}</p>
                      )}
                      {row.valueB === null && (
                        <p className="text-xs text-[#B23A48]">encerrado após {formatDate(dateA)}</p>
                      )}
                    </td>
                    <td className="px-4 py-3 text-right font-mono tabular-nums">
                      {formatCurrency(row.valueA)}
                    </td>
                    <td className="px-4 py-3 text-right font-mono tabular-nums">
                      {formatCurrency(row.valueB)}
                    </td>
                    <td className="px-4 py-3 text-right font-mono tabular-nums" style={{ color: deltaColor }}>
                      {delta === 0 ? "—" : `${delta > 0 ? "+" : "−"} ${formatCurrency(Math.abs(delta))}`}
                      {deltaPct !== null && (
                        <span className="ml-1 text-xs opacity-70">
                          ({delta >= 0 ? "+" : "−"}{Math.abs(deltaPct).toFixed(1)}%)
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
