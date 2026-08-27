"use client";

import { Fragment, useState } from "react";
import Link from "next/link";

type ProductMixAssetItem = { asset_id: string; asset_name: string; value: number; pct_of_class: number };
type ProductMixItem = { asset_class: string; value: number; pct: number; assets: ProductMixAssetItem[] };

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

function formatCurrency(value: number): string {
  return value.toLocaleString("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 });
}

function toggleInSet<T>(set: Set<T>, value: T): Set<T> {
  const next = new Set(set);
  if (next.has(value)) next.delete(value);
  else next.add(value);
  return next;
}

export default function ProductMixTable({ items }: { items: ProductMixItem[] }) {
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  return (
    <div className="overflow-hidden card">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-[#14181F]/10 text-left text-xs uppercase tracking-wide text-[#14181F]/40">
            <th className="px-4 py-3 font-medium">Classe</th>
            <th className="px-4 py-3 text-right font-medium">AUM</th>
            <th className="px-4 py-3 text-right font-medium">% da carteira do assessor</th>
          </tr>
        </thead>
        <tbody>
          {items.map((row) => {
            const isExpanded = expanded.has(row.asset_class);
            return (
              <Fragment key={row.asset_class}>
                <tr
                  className="cursor-pointer border-b border-[#14181F]/5 last:border-0 hover:bg-[#14181F]/[0.02]"
                  onClick={() => row.assets.length > 0 && setExpanded((prev) => toggleInSet(prev, row.asset_class))}
                >
                  <td className="px-4 py-3 font-medium">
                    {row.assets.length > 0 && (
                      <span className={`mr-1.5 inline-block transition-transform ${isExpanded ? "rotate-90" : ""}`}>▸</span>
                    )}
                    {ASSET_CLASS_LABELS[row.asset_class] ?? row.asset_class}
                    {row.assets.length > 0 && (
                      <span className="ml-1.5 font-mono text-xs font-normal tabular-nums text-[#14181F]/40">
                        ({row.assets.length})
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-right font-mono tabular-nums">{formatCurrency(row.value)}</td>
                  <td className="px-4 py-3 text-right font-mono tabular-nums">{row.pct.toFixed(1)}%</td>
                </tr>
                {isExpanded &&
                  row.assets.map((asset) => (
                    <tr key={asset.asset_id} className="border-b border-[#14181F]/5 last:border-0 bg-[#14181F]/[0.015]">
                      <td className="px-4 py-2.5 pl-9">
                        <Link href={`/ativos/${asset.asset_id}`} className="hover:underline">
                          {asset.asset_name}
                        </Link>
                      </td>
                      <td className="px-4 py-2.5 text-right font-mono tabular-nums text-[#14181F]/70">
                        {formatCurrency(asset.value)}
                      </td>
                      <td className="px-4 py-2.5 text-right font-mono tabular-nums text-[#14181F]/50">
                        {asset.pct_of_class.toFixed(1)}% da classe
                      </td>
                    </tr>
                  ))}
              </Fragment>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
