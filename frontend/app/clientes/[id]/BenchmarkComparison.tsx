"use client";

import { useEffect, useMemo, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import SvgMultiLineChart from "../../SvgMultiLineChart";

type Benchmark = { key: string; name: string };
type BenchmarkPoint = { value_date: string; index_value: number };
type ValueTrendPoint = { value_date: string; value: number };
type Position = { asset_id: string; asset_name: string; asset_class: string };

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

function formatDateShort(value: string): string {
  return new Date(value).toLocaleDateString("pt-BR", { day: "2-digit", month: "short" });
}

function periodReturnPct(points: BenchmarkPoint[]): number | null {
  if (points.length < 2) return null;
  const first = points[0].index_value;
  const last = points[points.length - 1].index_value;
  if (first <= 0) return null;
  return ((last - first) / first) * 100;
}

function normalize(points: { value_date: string; value: number }[]): { label: string; value: number }[] {
  if (points.length === 0) return [];
  const base = points[0].value || 1;
  return points.map((p) => ({ label: formatDateShort(p.value_date), value: (p.value / base) * 100 }));
}

export default function BenchmarkComparison({
  clientId,
  latestDate,
}: {
  clientId: string;
  latestDate: string;
}) {
  const { getToken } = useAuth();
  const [benchmarks, setBenchmarks] = useState<Benchmark[]>([]);
  const [benchmarkSeriesByKey, setBenchmarkSeriesByKey] = useState<Record<string, BenchmarkPoint[]>>({});
  const [positions, setPositions] = useState<Position[]>([]);
  const [scope, setScope] = useState<"aum" | "class" | "asset">("aum");
  const [scopeKey, setScopeKey] = useState<string>("");
  const [benchmarkKey, setBenchmarkKey] = useState<string>("cdi");
  const [valueTrend, setValueTrend] = useState<ValueTrendPoint[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function loadStatic() {
      const token = await getToken();
      const headers: HeadersInit = token ? { Authorization: `Bearer ${token}` } : {};
      const [benchRes, posRes] = await Promise.all([
        fetch(`${process.env.NEXT_PUBLIC_API_URL}/benchmarks/`, { headers }),
        fetch(`${process.env.NEXT_PUBLIC_API_URL}/clients/${clientId}/positions-at?date=${latestDate}`, { headers }),
      ]);
      const benchData: Benchmark[] = benchRes.ok ? await benchRes.json() : [];
      const posData: Position[] = posRes.ok ? await posRes.json() : [];
      if (cancelled) return;
      setBenchmarks(benchData);
      setPositions(posData);

      const seriesEntries = await Promise.all(
        benchData.map(async (b) => {
          const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/benchmarks/${b.key}/series`, { headers });
          const data: BenchmarkPoint[] = res.ok ? await res.json() : [];
          return [b.key, data] as const;
        })
      );
      if (!cancelled) setBenchmarkSeriesByKey(Object.fromEntries(seriesEntries));
    }

    loadStatic();
    return () => {
      cancelled = true;
    };
  }, [clientId, latestDate, getToken]);

  useEffect(() => {
    let cancelled = false;

    async function loadTrend() {
      setLoading(true);
      try {
        const token = await getToken();
        const headers: HeadersInit = token ? { Authorization: `Bearer ${token}` } : {};
        const params = new URLSearchParams({ scope });
        if (scope !== "aum" && scopeKey) params.set("key", scopeKey);
        const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/clients/${clientId}/value-trend?${params.toString()}`, {
          headers,
        });
        const data = res.ok ? await res.json() : [];
        if (!cancelled) setValueTrend(data);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    if (scope === "aum" || scopeKey) loadTrend();
    return () => {
      cancelled = true;
    };
  }, [clientId, scope, scopeKey, getToken]);

  const classOptions = useMemo(() => Array.from(new Set(positions.map((p) => p.asset_class))).sort(), [positions]);
  const assetOptions = useMemo(
    () => Array.from(new Map(positions.map((p) => [p.asset_id, p.asset_name])).entries()),
    [positions]
  );

  const chartSeries = [
    {
      name: scope === "aum" ? "AUM total" : scope === "class" ? ASSET_CLASS_LABELS[scopeKey] ?? scopeKey : assetOptions.find(([id]) => id === scopeKey)?.[1] ?? "Ativo",
      color: "#14181F",
      points: normalize(valueTrend),
    },
  ];
  const benchmarkPoints = benchmarkSeriesByKey[benchmarkKey] ?? [];
  if (benchmarkPoints.length > 0) {
    const benchmarkName = benchmarks.find((b) => b.key === benchmarkKey)?.name ?? benchmarkKey;
    chartSeries.push({
      name: benchmarkName,
      color: "#A6790A",
      points: normalize(benchmarkPoints.map((p) => ({ value_date: p.value_date, value: p.index_value }))),
    });
  }

  return (
    <div className="space-y-6">
      <section>
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-[#14181F]/70">
          Benchmarks (mercado brasileiro)
        </h2>
        <div className="overflow-hidden card">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[#14181F]/10 text-left text-xs uppercase tracking-wide text-[#14181F]/40">
                <th className="px-4 py-3 font-medium">Benchmark</th>
                <th className="px-4 py-3 text-right font-medium">Retorno no período</th>
              </tr>
            </thead>
            <tbody>
              {benchmarks.map((b) => {
                const ret = periodReturnPct(benchmarkSeriesByKey[b.key] ?? []);
                return (
                  <tr key={b.key} className="border-b border-[#14181F]/5 last:border-0">
                    <td className="px-4 py-3 font-medium">{b.name}</td>
                    <td className="px-4 py-3 text-right font-mono tabular-nums">
                      {ret !== null ? `${ret >= 0 ? "+" : ""}${ret.toFixed(2)}%` : "—"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>

      <section>
        <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-[#14181F]/70">
            Evolução vs. Benchmark
          </h2>
          <div className="flex flex-wrap items-center gap-2 text-sm">
            <select
              value={scope}
              onChange={(e) => {
                const next = e.target.value as "aum" | "class" | "asset";
                setScope(next);
                setScopeKey(next === "class" ? classOptions[0] ?? "" : next === "asset" ? assetOptions[0]?.[0] ?? "" : "");
              }}
              className="rounded-md border border-[#14181F]/15 px-2 py-1 text-xs focus:outline-none focus:ring-2 focus:ring-[#14181F]/20"
            >
              <option value="aum">AUM total</option>
              <option value="class">Classe de ativo</option>
              <option value="asset">Ativo específico</option>
            </select>
            {scope === "class" && (
              <select
                value={scopeKey}
                onChange={(e) => setScopeKey(e.target.value)}
                className="rounded-md border border-[#14181F]/15 px-2 py-1 text-xs focus:outline-none focus:ring-2 focus:ring-[#14181F]/20"
              >
                {classOptions.map((c) => (
                  <option key={c} value={c}>
                    {ASSET_CLASS_LABELS[c] ?? c}
                  </option>
                ))}
              </select>
            )}
            {scope === "asset" && (
              <select
                value={scopeKey}
                onChange={(e) => setScopeKey(e.target.value)}
                className="rounded-md border border-[#14181F]/15 px-2 py-1 text-xs focus:outline-none focus:ring-2 focus:ring-[#14181F]/20"
              >
                {assetOptions.map(([id, name]) => (
                  <option key={id} value={id}>
                    {name}
                  </option>
                ))}
              </select>
            )}
            <span className="text-[#14181F]/40">vs</span>
            <select
              value={benchmarkKey}
              onChange={(e) => setBenchmarkKey(e.target.value)}
              className="rounded-md border border-[#14181F]/15 px-2 py-1 text-xs focus:outline-none focus:ring-2 focus:ring-[#14181F]/20"
            >
              {benchmarks.map((b) => (
                <option key={b.key} value={b.key}>
                  {b.name}
                </option>
              ))}
            </select>
          </div>
        </div>
        <p className="mb-3 text-xs text-[#14181F]/40">Séries indexadas a 100 na primeira data do período, para comparação direta.</p>
        <div className="card p-4">
          {loading ? (
            <p className="text-sm text-[#14181F]/50">Carregando...</p>
          ) : (
            <SvgMultiLineChart series={chartSeries} formatValue={(v) => v.toFixed(1)} />
          )}
        </div>
      </section>
    </div>
  );
}
