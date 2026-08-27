"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import SvgMultiLineChart from "../../SvgMultiLineChart";

type Benchmark = { key: string; name: string };
type BenchmarkPoint = { value_date: string; index_value: number };
type TrendPoint = { snapshot_date: string; aum: number | null };

function formatDateShort(value: string): string {
  return new Date(value).toLocaleDateString("pt-BR", { day: "2-digit", month: "short" });
}

function normalize(points: { date: string; value: number }[]): { label: string; value: number }[] {
  if (points.length === 0) return [];
  const base = points[0].value || 1;
  return points.map((p) => ({ label: formatDateShort(p.date), value: (p.value / base) * 100 }));
}

export default function AdvisorBenchmarkChart({ trend }: { trend: TrendPoint[] }) {
  const { getToken } = useAuth();
  const [benchmarks, setBenchmarks] = useState<Benchmark[]>([]);
  const [benchmarkKey, setBenchmarkKey] = useState("cdi");
  const [series, setSeries] = useState<BenchmarkPoint[]>([]);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      const token = await getToken();
      const headers: HeadersInit = token ? { Authorization: `Bearer ${token}` } : {};
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/benchmarks/`, { headers });
      const data = res.ok ? await res.json() : [];
      if (!cancelled) setBenchmarks(data);
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [getToken]);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      const token = await getToken();
      const headers: HeadersInit = token ? { Authorization: `Bearer ${token}` } : {};
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/benchmarks/${benchmarkKey}/series`, { headers });
      const data = res.ok ? await res.json() : [];
      if (!cancelled) setSeries(data);
    }
    if (benchmarkKey) load();
    return () => {
      cancelled = true;
    };
  }, [benchmarkKey, getToken]);

  const aumPoints = trend.filter((p) => p.aum !== null).map((p) => ({ date: p.snapshot_date, value: p.aum as number }));
  const benchmarkPoints = series.map((p) => ({ date: p.value_date, value: p.index_value }));
  const benchmarkName = benchmarks.find((b) => b.key === benchmarkKey)?.name ?? benchmarkKey;

  return (
    <section className="mb-10">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-[#14181F]/70">AUM Evolution vs. Benchmark</h2>
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
      <p className="mb-3 text-xs text-[#14181F]/40">Séries indexadas a 100 na primeira data do período.</p>
      <div className="card p-4">
        <SvgMultiLineChart
          series={[
            { name: "AUM", color: "#14181F", points: normalize(aumPoints) },
            { name: benchmarkName, color: "#A6790A", points: normalize(benchmarkPoints) },
          ]}
          formatValue={(v) => v.toFixed(1)}
        />
      </div>
    </section>
  );
}
