"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@clerk/nextjs";

type AttributionItem = {
  asset_id: string;
  asset_name: string;
  asset_class: string;
  value_start: number;
  value_end: number;
  net_flow: number;
  performance_value: number;
  contribution_pct: number;
};

function formatCurrency(value: number): string {
  return value.toLocaleString("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 });
}

function formatDate(value: string): string {
  return new Date(value).toLocaleDateString("pt-BR");
}

export default function PerformanceAttribution({
  clientId,
  availableDates,
}: {
  clientId: string;
  availableDates: string[];
}) {
  const { getToken } = useAuth();
  const [dateA, setDateA] = useState(availableDates[0]);
  const [dateB, setDateB] = useState(availableDates[availableDates.length - 1]);
  const [items, setItems] = useState<AttributionItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      try {
        const token = await getToken();
        const headers: HeadersInit = token ? { Authorization: `Bearer ${token}` } : {};
        const res = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL}/clients/${clientId}/performance-attribution?from=${dateA}&to=${dateB}`,
          { headers }
        );
        const data = res.ok ? await res.json() : [];
        if (!cancelled) setItems(data);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [clientId, dateA, dateB, getToken]);

  if (availableDates.length < 2) return null;

  const totalContribution = items.reduce((sum, i) => sum + i.contribution_pct, 0);

  return (
    <section>
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-[#14181F]/70">Performance Attribution</h2>
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
          <span className="text-[#14181F]/40">→</span>
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
      <p className="mb-3 text-xs text-[#14181F]/40">
        Contribuição de cada ativo para a variação do patrimônio no período, descontando aportes/resgates
        registrados. Heurística simples — não é um cálculo de atribuição formal.
      </p>

      {loading ? (
        <p className="text-sm text-[#14181F]/50">Carregando...</p>
      ) : items.length === 0 ? (
        <p className="text-sm text-[#14181F]/50">Sem posições suficientes para calcular no período.</p>
      ) : (
        <div className="overflow-hidden card">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[#14181F]/10 text-left text-xs uppercase tracking-wide text-[#14181F]/40">
                <th className="px-4 py-3 font-medium">Ativo</th>
                <th className="px-4 py-3 text-right font-medium">Variação de valor</th>
                <th className="px-4 py-3 text-right font-medium">Fluxo (aporte/resgate)</th>
                <th className="px-4 py-3 text-right font-medium">Performance</th>
                <th className="px-4 py-3 text-right font-medium">Contribuição</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => {
                const valueChange = item.value_end - item.value_start;
                const color = item.contribution_pct > 0 ? "#3F7D5B" : item.contribution_pct < 0 ? "#B23A48" : "#14181F66";
                return (
                  <tr key={item.asset_id} className="border-b border-[#14181F]/5 last:border-0">
                    <td className="px-4 py-3 font-medium">{item.asset_name}</td>
                    <td className="px-4 py-3 text-right font-mono tabular-nums text-[#14181F]/70">
                      {valueChange >= 0 ? "+" : "−"} {formatCurrency(Math.abs(valueChange))}
                    </td>
                    <td className="px-4 py-3 text-right font-mono tabular-nums text-[#14181F]/50">
                      {item.net_flow === 0 ? "—" : `${item.net_flow > 0 ? "+" : "−"} ${formatCurrency(Math.abs(item.net_flow))}`}
                    </td>
                    <td className="px-4 py-3 text-right font-mono tabular-nums">
                      {item.performance_value >= 0 ? "+" : "−"} {formatCurrency(Math.abs(item.performance_value))}
                    </td>
                    <td className="px-4 py-3 text-right font-mono font-semibold tabular-nums" style={{ color }}>
                      {item.contribution_pct > 0 ? "+" : ""}
                      {item.contribution_pct.toFixed(2)}pp
                    </td>
                  </tr>
                );
              })}
            </tbody>
            <tfoot>
              <tr className="border-t border-[#14181F]/10 font-semibold">
                <td className="px-4 py-3" colSpan={4}>
                  Total
                </td>
                <td className="px-4 py-3 text-right font-mono tabular-nums">
                  {totalContribution > 0 ? "+" : ""}
                  {totalContribution.toFixed(2)}pp
                </td>
              </tr>
            </tfoot>
          </table>
        </div>
      )}
    </section>
  );
}
