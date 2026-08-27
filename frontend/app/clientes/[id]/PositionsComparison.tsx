"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@clerk/nextjs";

type Position = {
  id: string;
  asset_id: string;
  asset_name: string;
  asset_class: string;
  market_value: number;
  issuer: string | null;
};

type Row = {
  assetId: string;
  assetName: string;
  assetClass: string;
  issuer: string | null;
  valueA: number | null;
  valueB: number | null;
};

const ASSET_CLASS_LABELS: Record<string, string> = {
  coe: "COE",
  funds: "Fundos de Investimento",
  fixedIncome: "Renda Fixa",
  checkingAccount: "Caixa / Disponível",
  pensionFunds: "Previdência",
  repo: "Compromissada",
  treasury: "Tesouro Direto",
  stock: "Ações",
  tradedFunds: "Fundos Imobiliários",
};

function formatCurrency(value: number | null): string {
  if (value === null) return "—";
  return value.toLocaleString("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 });
}

function formatDate(value: string): string {
  return new Date(value).toLocaleDateString("pt-BR");
}

export default function PositionsComparison({
  clientId,
  availableDates,
}: {
  clientId: string;
  availableDates: string[];
}) {
  const { getToken } = useAuth();
  const [dateA, setDateA] = useState(availableDates[0]);
  const [dateB, setDateB] = useState(availableDates[availableDates.length - 1]);
  const [rows, setRows] = useState<Row[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      try {
        const token = await getToken();
        const headers: HeadersInit = token ? { Authorization: `Bearer ${token}` } : {};

        const [resA, resB] = await Promise.all([
          fetch(`${process.env.NEXT_PUBLIC_API_URL}/clients/${clientId}/positions-at?date=${dateA}`, { headers }),
          fetch(`${process.env.NEXT_PUBLIC_API_URL}/clients/${clientId}/positions-at?date=${dateB}`, { headers }),
        ]);

        const posA: Position[] = resA.ok ? await resA.json() : [];
        const posB: Position[] = resB.ok ? await resB.json() : [];

        const byAsset = new Map<string, Row>();
        for (const p of posA) {
          byAsset.set(p.asset_id, {
            assetId: p.asset_id,
            assetName: p.asset_name,
            assetClass: p.asset_class,
            issuer: p.issuer,
            valueA: p.market_value,
            valueB: null,
          });
        }
        for (const p of posB) {
          const existing = byAsset.get(p.asset_id);
          if (existing) {
            existing.valueB = p.market_value;
          } else {
            byAsset.set(p.asset_id, {
              assetId: p.asset_id,
              assetName: p.asset_name,
              assetClass: p.asset_class,
              issuer: p.issuer,
              valueA: null,
              valueB: p.market_value,
            });
          }
        }

        const sorted = Array.from(byAsset.values()).sort(
          (a, b) => (b.valueB ?? b.valueA ?? 0) - (a.valueA ?? a.valueB ?? 0)
        );

        if (!cancelled) setRows(sorted);
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

  return (
    <section className="mb-10">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-[#14181F]/70">
          Comparar posições
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
        <p className="text-sm text-[#14181F]/50">Carregando comparação...</p>
      ) : rows.length === 0 ? (
        <p className="text-sm text-[#14181F]/50">Sem posições sincronizadas para essas datas.</p>
      ) : (
        <div className="overflow-hidden rounded-lg border border-[#14181F]/10 bg-white">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[#14181F]/10 text-left text-xs uppercase tracking-wide text-[#14181F]/40">
                <th className="px-4 py-3 font-medium">Ativo</th>
                <th className="px-4 py-3 font-medium">Classe</th>
                <th className="px-4 py-3 text-right font-medium">{formatDate(dateA)}</th>
                <th className="px-4 py-3 text-right font-medium">{formatDate(dateB)}</th>
                <th className="px-4 py-3 text-right font-medium">Δ</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => {
                const a = row.valueA ?? 0;
                const b = row.valueB ?? 0;
                const delta = b - a;
                const deltaPct = a > 0 ? (delta / a) * 100 : null;
                const deltaColor = delta > 0 ? "#3F7D5B" : delta < 0 ? "#B23A48" : "#14181F66";
                return (
                  <tr key={row.assetId} className="border-b border-[#14181F]/5 last:border-0">
                    <td className="px-4 py-3">
                      <p className="font-medium">{row.assetName}</p>
                      {row.issuer && <p className="text-xs text-[#14181F]/40">{row.issuer}</p>}
                      {row.valueA === null && (
                        <p className="text-xs text-[#3F7D5B]">novo em {formatDate(dateB)}</p>
                      )}
                      {row.valueB === null && (
                        <p className="text-xs text-[#B23A48]">encerrado após {formatDate(dateA)}</p>
                      )}
                    </td>
                    <td className="px-4 py-3 text-[#14181F]/70">
                      {ASSET_CLASS_LABELS[row.assetClass] ?? row.assetClass}
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
