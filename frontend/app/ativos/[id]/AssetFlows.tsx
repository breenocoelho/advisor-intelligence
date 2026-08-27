"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import Link from "next/link";

type FlowItem = {
  client_id: string;
  client_name: string;
  quantity_start: number | null;
  quantity_end: number | null;
  quantity_delta: number | null;
  purchase_value: number;
  sale_value: number;
  net_value: number;
};

function formatCurrency(value: number): string {
  return value.toLocaleString("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 });
}

function formatQuantity(value: number | null): string {
  if (value === null) return "—";
  return value.toLocaleString("pt-BR", { maximumFractionDigits: 4 });
}

function formatDate(value: string): string {
  return new Date(value).toLocaleDateString("pt-BR");
}

export default function AssetFlows({ assetId, availableDates }: { assetId: string; availableDates: string[] }) {
  const { getToken } = useAuth();
  const [dateA, setDateA] = useState(availableDates[0]);
  const [dateB, setDateB] = useState(availableDates[availableDates.length - 1]);
  const [items, setItems] = useState<FlowItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      try {
        const token = await getToken();
        const headers: HeadersInit = token ? { Authorization: `Bearer ${token}` } : {};
        const res = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL}/assets/${assetId}/flows?from=${dateA}&to=${dateB}`,
          { headers }
        );
        const data = res.ok ? await res.json() : [];
        if (!cancelled) setItems(data.filter((i: FlowItem) => i.purchase_value || i.sale_value || i.quantity_delta));
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [assetId, dateA, dateB, getToken]);

  if (availableDates.length < 2) return null;

  const totalPurchase = items.reduce((sum, i) => sum + i.purchase_value, 0);
  const totalSale = items.reduce((sum, i) => sum + i.sale_value, 0);

  return (
    <section className="mb-10">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-[#14181F]/70">
          Compras e vendas por cliente
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

      {loading ? (
        <p className="text-sm text-[#14181F]/50">Carregando...</p>
      ) : items.length === 0 ? (
        <p className="text-sm text-[#14181F]/50">Nenhuma movimentação de clientes nesse período.</p>
      ) : (
        <div className="overflow-hidden card">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[#14181F]/10 text-left text-xs uppercase tracking-wide text-[#14181F]/40">
                <th className="px-4 py-3 font-medium">Cliente</th>
                <th className="px-4 py-3 text-right font-medium">Δ Quantidade</th>
                <th className="px-4 py-3 text-right font-medium">Aportes</th>
                <th className="px-4 py-3 text-right font-medium">Resgates</th>
                <th className="px-4 py-3 text-right font-medium">Líquido</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => {
                const color = item.net_value > 0 ? "#3F7D5B" : item.net_value < 0 ? "#B23A48" : "#14181F66";
                return (
                  <tr key={item.client_id} className="border-b border-[#14181F]/5 last:border-0">
                    <td className="px-4 py-3">
                      <Link href={`/clientes/${item.client_id}`} className="font-medium hover:underline">
                        {item.client_name}
                      </Link>
                    </td>
                    <td className="px-4 py-3 text-right font-mono tabular-nums text-[#14181F]/70">
                      {item.quantity_delta !== null && item.quantity_delta !== 0
                        ? `${item.quantity_delta > 0 ? "+" : ""}${formatQuantity(item.quantity_delta)}`
                        : "—"}
                    </td>
                    <td className="px-4 py-3 text-right font-mono tabular-nums" style={{ color: "#3F7D5B" }}>
                      {item.purchase_value > 0 ? `+ ${formatCurrency(item.purchase_value)}` : "—"}
                    </td>
                    <td className="px-4 py-3 text-right font-mono tabular-nums" style={{ color: "#B23A48" }}>
                      {item.sale_value > 0 ? `− ${formatCurrency(item.sale_value)}` : "—"}
                    </td>
                    <td className="px-4 py-3 text-right font-mono font-semibold tabular-nums" style={{ color }}>
                      {item.net_value !== 0 ? `${item.net_value > 0 ? "+" : "−"} ${formatCurrency(Math.abs(item.net_value))}` : "—"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
            <tfoot>
              <tr className="border-t border-[#14181F]/10 font-semibold">
                <td className="px-4 py-3">Total</td>
                <td className="px-4 py-3" />
                <td className="px-4 py-3 text-right font-mono tabular-nums">{formatCurrency(totalPurchase)}</td>
                <td className="px-4 py-3 text-right font-mono tabular-nums">{formatCurrency(totalSale)}</td>
                <td className="px-4 py-3 text-right font-mono tabular-nums">{formatCurrency(totalPurchase - totalSale)}</td>
              </tr>
            </tfoot>
          </table>
        </div>
      )}
    </section>
  );
}
