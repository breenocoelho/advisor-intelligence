"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@clerk/nextjs";

export type ChangeItem = { label: string; direction: "up" | "down" | "neutral"; value_display: string };

const PERIODS = [
  { label: "30 dias", days: 30 },
  { label: "90 dias", days: 90 },
  { label: "6 meses", days: 182 },
  { label: "12 meses", days: 365 },
] as const;

export default function WhatChangedCard({ whatChangedUrl }: { whatChangedUrl: string }) {
  const { getToken } = useAuth();
  const [periodDays, setPeriodDays] = useState<number>(90);
  const [items, setItems] = useState<ChangeItem[] | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      try {
        const token = await getToken();
        const headers: HeadersInit = token ? { Authorization: `Bearer ${token}` } : {};

        const from = new Date();
        from.setDate(from.getDate() - periodDays);
        const params = new URLSearchParams({ from: from.toISOString().split("T")[0] });

        const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}${whatChangedUrl}?${params.toString()}`, { headers });
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
  }, [whatChangedUrl, periodDays, getToken]);

  return (
    <section className="mb-10">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-[#14181F]/70">What Changed?</h2>
        <div className="flex gap-1">
          {PERIODS.map((p) => (
            <button
              key={p.label}
              onClick={() => setPeriodDays(p.days)}
              className={`rounded-md px-2.5 py-1 text-xs font-medium transition ${
                periodDays === p.days
                  ? "bg-[#14181F] text-white"
                  : "border border-[#14181F]/15 text-[#14181F]/70 hover:bg-[#14181F]/5"
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <p className="text-sm text-[#14181F]/50">Carregando...</p>
      ) : !items || items.length === 0 ? (
        <p className="text-sm text-[#14181F]/50">Nenhuma mudança relevante no período.</p>
      ) : (
        <div className="card flex flex-wrap gap-3 p-4">
          {items.map((item, i) => (
            <div
              key={i}
              className="flex items-center gap-2 rounded-md border border-[#14181F]/10 px-3 py-2"
            >
              <span
                className="font-semibold"
                style={{ color: item.direction === "up" ? "#3F7D5B" : item.direction === "down" ? "#B23A48" : "#14181F66" }}
              >
                {item.direction === "up" ? "▲" : item.direction === "down" ? "▼" : "•"}
              </span>
              <span className="text-sm">
                <span className="font-medium">{item.label}</span>{" "}
                <span className="font-mono tabular-nums text-[#14181F]/70">{item.value_display}</span>
              </span>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
