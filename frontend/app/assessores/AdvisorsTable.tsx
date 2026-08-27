"use client";

import { useState } from "react";
import Link from "next/link";

type Advisor = {
  id: string;
  name: string;
  aum: number;
  client_count: number;
  net_flow: number;
  aum_growth_pct: number | null;
};

type SortKey = "aum" | "client_count" | "net_flow" | "aum_growth_pct";

function formatCurrency(value: number): string {
  return value.toLocaleString("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 });
}

export default function AdvisorsTable({ advisors }: { advisors: Advisor[] }) {
  const [sortKey, setSortKey] = useState<SortKey>("aum");

  const sorted = [...advisors].sort((a, b) => (b[sortKey] ?? -Infinity) - (a[sortKey] ?? -Infinity));

  function headerButton(key: SortKey, label: string) {
    return (
      <button
        onClick={() => setSortKey(key)}
        className={`font-medium transition ${sortKey === key ? "text-[#14181F]" : "text-[#14181F]/40 hover:text-[#14181F]/70"}`}
      >
        {label} {sortKey === key && "↓"}
      </button>
    );
  }

  return (
    <div className="overflow-hidden card">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-[#14181F]/10 text-left text-xs uppercase tracking-wide text-[#14181F]/40">
            <th className="px-4 py-3 font-medium">Assessor</th>
            <th className="px-4 py-3 text-right">{headerButton("aum", "AUM")}</th>
            <th className="px-4 py-3 text-right">{headerButton("aum_growth_pct", "Crescimento")}</th>
            <th className="px-4 py-3 text-right">{headerButton("net_flow", "Net Flow")}</th>
            <th className="px-4 py-3 text-right">{headerButton("client_count", "Clientes")}</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((advisor) => (
            <tr key={advisor.id} className="border-b border-[#14181F]/5 last:border-0 hover:bg-[#14181F]/[0.02]">
              <td className="px-4 py-3">
                <Link href={`/assessores/${advisor.id}`} className="font-medium hover:underline underline-offset-2">
                  {advisor.name}
                </Link>
              </td>
              <td className="px-4 py-3 text-right font-mono tabular-nums">{formatCurrency(advisor.aum)}</td>
              <td className="px-4 py-3 text-right font-mono tabular-nums">
                {advisor.aum_growth_pct !== null ? (
                  <span style={{ color: advisor.aum_growth_pct >= 0 ? "#3F7D5B" : "#B23A48" }}>
                    {advisor.aum_growth_pct >= 0 ? "+" : ""}
                    {advisor.aum_growth_pct.toFixed(1)}%
                  </span>
                ) : (
                  "—"
                )}
              </td>
              <td className="px-4 py-3 text-right font-mono tabular-nums">
                <span style={{ color: advisor.net_flow >= 0 ? "#3F7D5B" : "#B23A48" }}>
                  {advisor.net_flow >= 0 ? "+" : "−"} {formatCurrency(Math.abs(advisor.net_flow))}
                </span>
              </td>
              <td className="px-4 py-3 text-right font-mono tabular-nums text-[#14181F]/70">{advisor.client_count}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
