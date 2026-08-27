"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import SvgLineChart from "../../SvgLineChart";

type PricePoint = { value_date: string; unit_price: number };

function formatDateShort(value: string): string {
  return new Date(value).toLocaleDateString("pt-BR", { day: "2-digit", month: "short" });
}

function formatUnitPrice(value: number): string {
  return value.toLocaleString("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 4 });
}

export default function AssetPriceTrend({ assetId }: { assetId: string }) {
  const { getToken } = useAuth();
  const [points, setPoints] = useState<PricePoint[] | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      const token = await getToken();
      const headers: HeadersInit = token ? { Authorization: `Bearer ${token}` } : {};
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/assets/${assetId}/price-trend`, { headers });
      const data = res.ok ? await res.json() : [];
      if (!cancelled) setPoints(data);
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [assetId, getToken]);

  if (points === null) return null;
  if (points.length < 2) return null; // sem unidade (ex: COE/fundo) ou dados insuficientes

  const first = points[0].unit_price;
  const last = points[points.length - 1].unit_price;
  const changePct = first > 0 ? ((last - first) / first) * 100 : null;

  return (
    <section className="mb-10">
      <div className="mb-3 flex items-baseline justify-between">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-[#14181F]/70">
          Tendência — preço unitário
        </h2>
        {changePct !== null && (
          <span
            className="font-mono text-sm font-semibold tabular-nums"
            style={{ color: changePct >= 0 ? "#3F7D5B" : "#B23A48" }}
          >
            {changePct >= 0 ? "+" : ""}
            {changePct.toFixed(2)}%
          </span>
        )}
      </div>
      <p className="mb-3 text-xs text-[#14181F]/40">
        PL total dividido pela quantidade total em cada data — isola valorização/desvalorização de
        aporte/resgate, que mudam o PL sem mudar o preço da unidade.
      </p>
      <div className="card p-4">
        <SvgLineChart
          points={points.map((p) => ({ label: formatDateShort(p.value_date), value: p.unit_price }))}
          formatValue={formatUnitPrice}
        />
      </div>
    </section>
  );
}
