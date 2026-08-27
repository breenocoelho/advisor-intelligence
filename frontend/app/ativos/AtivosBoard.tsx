"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import SortableTh from "../SortableTh";

type Asset = {
  id: string;
  name: string;
  asset_class: string;
  issuer: string | null;
  risk_rating: string | null;
  due_date: string | null;
  total_exposure: number;
  client_count: number;
};

type SortKey = "name" | "asset_class" | "risk_rating" | "total_exposure" | "client_count";

const RISK_ORDER: Record<string, number> = { Baixo: 0, Médio: 1, Alto: 2 };

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

const RISK_COLORS: Record<string, string> = {
  Baixo: "#3F7D5B",
  Médio: "#A6790A",
  Alto: "#B23A48",
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

export default function AtivosBoard({ assets }: { assets: Asset[] }) {
  const [classFilter, setClassFilter] = useState<Set<string>>(new Set());
  const [riskFilter, setRiskFilter] = useState<Set<string>>(new Set());
  const [sortKey, setSortKey] = useState<SortKey>("name");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");

  const availableClasses = useMemo(() => {
    const set = new Set(assets.map((a) => a.asset_class));
    return Array.from(set).sort();
  }, [assets]);

  const availableRisks = useMemo(() => {
    const set = new Set(assets.map((a) => a.risk_rating).filter(Boolean) as string[]);
    return Array.from(set).sort();
  }, [assets]);

  function handleSort(key: string) {
    if (key === sortKey) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key as SortKey);
      setSortDir(key === "name" || key === "asset_class" ? "asc" : "desc");
    }
  }

  const filtered = assets.filter((a) => {
    const matchesClass = classFilter.size === 0 || classFilter.has(a.asset_class);
    const matchesRisk = riskFilter.size === 0 || (a.risk_rating && riskFilter.has(a.risk_rating));
    return matchesClass && matchesRisk;
  });

  const sorted = [...filtered].sort((a, b) => {
    let cmp = 0;
    if (sortKey === "name") cmp = a.name.localeCompare(b.name);
    else if (sortKey === "asset_class") cmp = a.asset_class.localeCompare(b.asset_class);
    else if (sortKey === "risk_rating") {
      cmp = (RISK_ORDER[a.risk_rating ?? ""] ?? -1) - (RISK_ORDER[b.risk_rating ?? ""] ?? -1);
    } else if (sortKey === "total_exposure") cmp = a.total_exposure - b.total_exposure;
    else if (sortKey === "client_count") cmp = a.client_count - b.client_count;
    return sortDir === "asc" ? cmp : -cmp;
  });

  const hasActiveFilters = classFilter.size > 0 || riskFilter.size > 0;

  return (
    <div className="flex flex-col gap-8 lg:flex-row">
      <aside className="shrink-0 lg:w-56">
        <div className="lg:sticky lg:top-6">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-xs font-semibold uppercase tracking-wide text-[#14181F]/50">Filtros</h2>
            {hasActiveFilters && (
              <button
                onClick={() => {
                  setClassFilter(new Set());
                  setRiskFilter(new Set());
                }}
                className="text-xs font-medium text-[#14181F]/40 hover:text-[#14181F]/70"
              >
                Limpar
              </button>
            )}
          </div>
          <div className="space-y-5">
            <div>
              <p className="mb-2 text-xs font-medium uppercase tracking-wide text-[#14181F]/40">Classe</p>
              <div className="space-y-1.5">
                {availableClasses.map((c) => (
                  <label key={c} className="flex items-center gap-2 text-sm">
                    <input
                      type="checkbox"
                      checked={classFilter.has(c)}
                      onChange={() => setClassFilter((prev) => toggleInSet(prev, c))}
                      className="h-3.5 w-3.5 rounded border-[#14181F]/30"
                    />
                    {ASSET_CLASS_LABELS[c] ?? c}
                  </label>
                ))}
              </div>
            </div>
            {availableRisks.length > 0 && (
              <div>
                <p className="mb-2 text-xs font-medium uppercase tracking-wide text-[#14181F]/40">
                  Classificação de risco
                </p>
                <div className="space-y-1.5">
                  {availableRisks.map((r) => (
                    <label key={r} className="flex items-center gap-2 text-sm">
                      <input
                        type="checkbox"
                        checked={riskFilter.has(r)}
                        onChange={() => setRiskFilter((prev) => toggleInSet(prev, r))}
                        className="h-3.5 w-3.5 rounded border-[#14181F]/30"
                      />
                      {r}
                    </label>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </aside>

      <div className="min-w-0 flex-1">
        {sorted.length === 0 ? (
          <div className="rounded-lg border border-dashed border-[#14181F]/15 py-16 text-center">
            <p className="text-lg font-medium">Nenhum ativo com esses filtros.</p>
          </div>
        ) : (
          <div className="overflow-hidden card">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[#14181F]/10 text-left text-xs uppercase tracking-wide text-[#14181F]/40">
                  <SortableTh label="Ativo" sortKey="name" currentSort={sortKey} currentDir={sortDir} onSort={handleSort} />
                  <SortableTh label="Classe" sortKey="asset_class" currentSort={sortKey} currentDir={sortDir} onSort={handleSort} />
                  <SortableTh label="Risco" sortKey="risk_rating" currentSort={sortKey} currentDir={sortDir} onSort={handleSort} />
                  <SortableTh label="Exposição total" sortKey="total_exposure" currentSort={sortKey} currentDir={sortDir} onSort={handleSort} align="right" />
                  <SortableTh label="Clientes" sortKey="client_count" currentSort={sortKey} currentDir={sortDir} onSort={handleSort} align="right" />
                </tr>
              </thead>
              <tbody>
                {sorted.map((asset) => (
                  <tr
                    key={asset.id}
                    className="border-b border-[#14181F]/5 last:border-0 hover:bg-[#14181F]/[0.02]"
                  >
                    <td className="px-4 py-3">
                      <Link
                        href={`/ativos/${asset.id}`}
                        className="font-medium hover:underline underline-offset-2"
                      >
                        {asset.name}
                      </Link>
                      {asset.issuer && <p className="mt-0.5 text-xs text-[#14181F]/40">{asset.issuer}</p>}
                    </td>
                    <td className="px-4 py-3 text-[#14181F]/70">
                      {ASSET_CLASS_LABELS[asset.asset_class] ?? asset.asset_class}
                    </td>
                    <td className="px-4 py-3">
                      {asset.risk_rating ? (
                        <span
                          className="inline-flex rounded-full px-2 py-0.5 text-xs font-medium"
                          style={{
                            backgroundColor: `${RISK_COLORS[asset.risk_rating] ?? "#14181F"}1a`,
                            color: RISK_COLORS[asset.risk_rating] ?? "#14181F",
                          }}
                        >
                          {asset.risk_rating}
                        </span>
                      ) : (
                        <span className="text-[#14181F]/25">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-right font-mono tabular-nums">
                      {formatCurrency(asset.total_exposure)}
                    </td>
                    <td className="px-4 py-3 text-right font-mono tabular-nums text-[#14181F]/70">
                      {asset.client_count}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
