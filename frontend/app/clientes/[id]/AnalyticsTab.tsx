"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import SvgLineChart from "../../SvgLineChart";
import SvgMultiLineChart from "../../SvgMultiLineChart";
import SortableTh from "../../SortableTh";

type PortfolioSortKey = "asset_class" | "pct_start" | "pct_end" | "delta_pp";

type SnapshotPoint = { snapshot_date: string; aum: number | null };
type PortfolioEvolutionItem = { asset_class: string; pct_start: number; pct_end: number; delta_pp: number };
type AssetClassSeries = { asset_class: string; points: SnapshotPoint[] };
type CashAnalytics = { current: number; average: number; max: number; pct_of_aum_current: number | null };
type FlowAnalytics = { gross_inflow: number; gross_outflow: number; net_flow: number };

type Analytics = {
  aum_trend: SnapshotPoint[];
  aum_change_pct: number | null;
  portfolio_evolution: PortfolioEvolutionItem[];
  class_series: AssetClassSeries[];
  cash_analytics: CashAnalytics | null;
  flow_analytics: FlowAnalytics | null;
};

const CLASS_COLORS = ["#14181F", "#3E5C76", "#A6790A", "#3F7D5B", "#B23A48", "#7A5CB0", "#0E7C86", "#C77C2E"];

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

const PERIODS = [
  { label: "30 dias", days: 30 },
  { label: "90 dias", days: 90 },
  { label: "6 meses", days: 182 },
  { label: "12 meses", days: 365 },
  { label: "Tudo", days: null },
] as const;

function formatCurrency(value: number): string {
  return value.toLocaleString("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 });
}

function formatDateShort(value: string): string {
  return new Date(value).toLocaleDateString("pt-BR", { day: "2-digit", month: "short" });
}

export default function AnalyticsTab({ clientId }: { clientId: string }) {
  const { getToken } = useAuth();
  const [periodDays, setPeriodDays] = useState<number | null>(null);
  const [analytics, setAnalytics] = useState<Analytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [portfolioSortKey, setPortfolioSortKey] = useState<PortfolioSortKey>("delta_pp");
  const [portfolioSortDir, setPortfolioSortDir] = useState<"asc" | "desc">("desc");

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      try {
        const token = await getToken();
        const headers: HeadersInit = token ? { Authorization: `Bearer ${token}` } : {};

        const params = new URLSearchParams();
        if (periodDays !== null) {
          const from = new Date();
          from.setDate(from.getDate() - periodDays);
          params.set("from", from.toISOString().split("T")[0]);
        }

        const res = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL}/clients/${clientId}/analytics?${params.toString()}`,
          { headers }
        );
        const data = res.ok ? await res.json() : null;
        if (!cancelled) setAnalytics(data);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [clientId, periodDays, getToken]);

  function handlePortfolioSort(key: string) {
    if (key === portfolioSortKey) {
      setPortfolioSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setPortfolioSortKey(key as PortfolioSortKey);
      setPortfolioSortDir(key === "asset_class" ? "asc" : "desc");
    }
  }

  const sortedPortfolioEvolution = analytics
    ? [...analytics.portfolio_evolution].sort((a, b) => {
        let cmp = 0;
        if (portfolioSortKey === "asset_class") cmp = a.asset_class.localeCompare(b.asset_class);
        else if (portfolioSortKey === "delta_pp") cmp = Math.abs(a.delta_pp) - Math.abs(b.delta_pp);
        else cmp = a[portfolioSortKey] - b[portfolioSortKey];
        return portfolioSortDir === "asc" ? cmp : -cmp;
      })
    : [];

  return (
    <div>
      <div className="mb-6 flex flex-wrap items-center gap-2">
        {PERIODS.map((p) => (
          <button
            key={p.label}
            onClick={() => setPeriodDays(p.days)}
            className={`rounded-md px-3 py-1.5 text-xs font-medium transition ${
              periodDays === p.days
                ? "bg-[#14181F] text-white"
                : "border border-[#14181F]/15 text-[#14181F]/70 hover:bg-[#14181F]/5"
            }`}
          >
            {p.label}
          </button>
        ))}
      </div>

      {loading || !analytics ? (
        <p className="text-sm text-[#14181F]/50">Carregando analytics...</p>
      ) : (
        <div className="space-y-10">
          {/* AUM Evolution */}
          <section>
            <div className="mb-3 flex items-baseline justify-between">
              <h2 className="text-sm font-semibold uppercase tracking-wide text-[#14181F]/70">AUM Evolution</h2>
              {analytics.aum_change_pct !== null && (
                <span
                  className="font-mono text-sm font-semibold tabular-nums"
                  style={{ color: analytics.aum_change_pct >= 0 ? "#3F7D5B" : "#B23A48" }}
                >
                  {analytics.aum_change_pct >= 0 ? "+" : ""}
                  {analytics.aum_change_pct.toFixed(1)}%
                </span>
              )}
            </div>
            <div className="card p-4">
              <SvgLineChart
                points={analytics.aum_trend
                  .filter((p) => p.aum !== null)
                  .map((p) => ({ label: formatDateShort(p.snapshot_date), value: p.aum as number }))}
                formatValue={formatCurrency}
              />
            </div>
          </section>

          {/* Portfolio Evolution */}
          {analytics.portfolio_evolution.length > 0 && (
            <section>
              <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-[#14181F]/70">
                Portfolio Evolution
              </h2>
              {analytics.class_series.length > 0 && (
                <div className="card mb-3 p-4">
                  <SvgMultiLineChart
                    series={analytics.class_series.map((cs, i) => ({
                      name: ASSET_CLASS_LABELS[cs.asset_class] ?? cs.asset_class,
                      color: CLASS_COLORS[i % CLASS_COLORS.length],
                      points: cs.points
                        .filter((p) => p.aum !== null)
                        .map((p) => ({ label: formatDateShort(p.snapshot_date), value: p.aum as number })),
                    }))}
                    formatValue={formatCurrency}
                  />
                </div>
              )}
              <div className="overflow-hidden card">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-[#14181F]/10 text-left text-xs uppercase tracking-wide text-[#14181F]/40">
                      <SortableTh label="Classe" sortKey="asset_class" currentSort={portfolioSortKey} currentDir={portfolioSortDir} onSort={handlePortfolioSort} />
                      <SortableTh label="Início do período" sortKey="pct_start" currentSort={portfolioSortKey} currentDir={portfolioSortDir} onSort={handlePortfolioSort} align="right" />
                      <SortableTh label="Hoje" sortKey="pct_end" currentSort={portfolioSortKey} currentDir={portfolioSortDir} onSort={handlePortfolioSort} align="right" />
                      <SortableTh label="Δ (pp)" sortKey="delta_pp" currentSort={portfolioSortKey} currentDir={portfolioSortDir} onSort={handlePortfolioSort} align="right" />
                    </tr>
                  </thead>
                  <tbody>
                    {sortedPortfolioEvolution.map((row) => {
                      const relevant = Math.abs(row.delta_pp) >= 5;
                      const deltaColor = row.delta_pp > 0 ? "#3F7D5B" : row.delta_pp < 0 ? "#B23A48" : "#14181F66";
                      return (
                        <tr key={row.asset_class} className="border-b border-[#14181F]/5 last:border-0">
                          <td className="px-4 py-3">
                            {ASSET_CLASS_LABELS[row.asset_class] ?? row.asset_class}
                            {relevant && (
                              <span className="ml-2 rounded-full bg-[#A6790A]/10 px-2 py-0.5 text-xs font-medium text-[#A6790A]">
                                mudança relevante
                              </span>
                            )}
                          </td>
                          <td className="px-4 py-3 text-right font-mono tabular-nums">{row.pct_start.toFixed(1)}%</td>
                          <td className="px-4 py-3 text-right font-mono tabular-nums">{row.pct_end.toFixed(1)}%</td>
                          <td className="px-4 py-3 text-right font-mono font-semibold tabular-nums" style={{ color: deltaColor }}>
                            {row.delta_pp > 0 ? "+" : ""}
                            {row.delta_pp.toFixed(1)}pp
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </section>
          )}

          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
            {/* Cash Analytics */}
            {analytics.cash_analytics && (
              <section>
                <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-[#14181F]/70">
                  Cash Analytics
                </h2>
                <div className="card grid grid-cols-2 gap-4 p-4">
                  <div>
                    <p className="text-xs uppercase tracking-wide text-[#14181F]/40">Atual</p>
                    <p className="mt-1 font-mono text-lg font-semibold tabular-nums">
                      {formatCurrency(analytics.cash_analytics.current)}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs uppercase tracking-wide text-[#14181F]/40">% do AUM</p>
                    <p className="mt-1 font-mono text-lg font-semibold tabular-nums">
                      {analytics.cash_analytics.pct_of_aum_current !== null
                        ? `${analytics.cash_analytics.pct_of_aum_current.toFixed(1)}%`
                        : "—"}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs uppercase tracking-wide text-[#14181F]/40">Média no período</p>
                    <p className="mt-1 font-mono text-sm tabular-nums text-[#14181F]/70">
                      {formatCurrency(analytics.cash_analytics.average)}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs uppercase tracking-wide text-[#14181F]/40">Máximo no período</p>
                    <p className="mt-1 font-mono text-sm tabular-nums text-[#14181F]/70">
                      {formatCurrency(analytics.cash_analytics.max)}
                    </p>
                  </div>
                </div>
              </section>
            )}

            {/* Flow Analytics */}
            {analytics.flow_analytics && (
              <section>
                <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-[#14181F]/70">
                  Flow Analytics
                </h2>
                <div className="card grid grid-cols-1 gap-4 p-4">
                  <div className="flex items-center justify-between">
                    <p className="text-xs uppercase tracking-wide text-[#14181F]/40">Gross Inflow</p>
                    <p className="font-mono text-sm font-semibold tabular-nums" style={{ color: "#3F7D5B" }}>
                      + {formatCurrency(analytics.flow_analytics.gross_inflow)}
                    </p>
                  </div>
                  <div className="flex items-center justify-between">
                    <p className="text-xs uppercase tracking-wide text-[#14181F]/40">Gross Outflow</p>
                    <p className="font-mono text-sm font-semibold tabular-nums" style={{ color: "#B23A48" }}>
                      − {formatCurrency(analytics.flow_analytics.gross_outflow)}
                    </p>
                  </div>
                  <div className="flex items-center justify-between border-t border-[#14181F]/10 pt-3">
                    <p className="text-xs font-medium uppercase tracking-wide text-[#14181F]/50">Net Flow</p>
                    <p
                      className="font-mono text-sm font-semibold tabular-nums"
                      style={{ color: analytics.flow_analytics.net_flow >= 0 ? "#3F7D5B" : "#B23A48" }}
                    >
                      {analytics.flow_analytics.net_flow >= 0 ? "+" : "−"}{" "}
                      {formatCurrency(Math.abs(analytics.flow_analytics.net_flow))}
                    </p>
                  </div>
                </div>
              </section>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
