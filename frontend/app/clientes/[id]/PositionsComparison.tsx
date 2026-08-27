"use client";

import { Fragment, useEffect, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import SortableTh from "../../SortableTh";

type Position = {
  id: string;
  asset_id: string;
  asset_name: string;
  asset_class: string;
  market_value: number;
  quantity: number | null;
  issuer: string | null;
  due_date: string | null;
  rate: number | null;
  index_description: string | null;
  manager_name: string | null;
  risk_rating: string | null;
};

type Row = {
  assetId: string;
  assetName: string;
  assetClass: string;
  issuer: string | null;
  dueDate: string | null;
  quantityA: number | null;
  quantityB: number | null;
  rate: number | null;
  indexDescription: string | null;
  managerName: string | null;
  riskRating: string | null;
  valueA: number | null;
  valueB: number | null;
};

type SortKey = "assetName" | "dueDate" | "valueA" | "valueB" | "pct" | "delta";

type ColumnKey = "quantity" | "dueDate" | "issuer" | "manager" | "index" | "risk";

const COLUMN_LABELS: Record<ColumnKey, string> = {
  quantity: "Quantidade",
  dueDate: "Vencimento",
  issuer: "Emissor",
  manager: "Gestora",
  index: "Indexador / Taxa",
  risk: "Classificação de risco",
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

function formatQuantity(value: number | null): string {
  if (value === null) return "—";
  return value.toLocaleString("pt-BR", { maximumFractionDigits: 4 });
}

function formatDate(value: string): string {
  return new Date(value).toLocaleDateString("pt-BR");
}

function toggleInSet<T>(set: Set<T>, value: T): Set<T> {
  const next = new Set(set);
  if (next.has(value)) next.delete(value);
  else next.add(value);
  return next;
}

export default function PositionsComparison({
  clientId,
  availableDates,
}: {
  clientId: string;
  availableDates: string[];
}) {
  const { getToken } = useAuth();
  const latestDate = availableDates[availableDates.length - 1];
  const [compareMode, setCompareMode] = useState(false);
  const [dateA, setDateA] = useState(availableDates[0]);
  const [dateB, setDateB] = useState(latestDate);
  const [rows, setRows] = useState<Row[]>([]);
  const [loading, setLoading] = useState(true);
  const [collapsedClasses, setCollapsedClasses] = useState<Set<string>>(new Set());
  const [sortKey, setSortKey] = useState<SortKey>("assetName");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");
  const [columns, setColumns] = useState<Set<ColumnKey>>(new Set(["quantity"]));
  const [showColumnPicker, setShowColumnPicker] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      try {
        const token = await getToken();
        const headers: HeadersInit = token ? { Authorization: `Bearer ${token}` } : {};

        const requests = [
          fetch(`${process.env.NEXT_PUBLIC_API_URL}/clients/${clientId}/positions-at?date=${dateB}`, { headers }),
        ];
        if (compareMode) {
          requests.push(
            fetch(`${process.env.NEXT_PUBLIC_API_URL}/clients/${clientId}/positions-at?date=${dateA}`, { headers })
          );
        }
        const [resB, resA] = await Promise.all(requests);

        const posB: Position[] = resB.ok ? await resB.json() : [];
        const posA: Position[] = compareMode && resA?.ok ? await resA.json() : [];

        const byAsset = new Map<string, Row>();
        for (const p of posA) {
          byAsset.set(p.asset_id, {
            assetId: p.asset_id,
            assetName: p.asset_name,
            assetClass: p.asset_class,
            issuer: p.issuer,
            dueDate: p.due_date,
            quantityA: p.quantity,
            quantityB: null,
            rate: p.rate,
            indexDescription: p.index_description,
            managerName: p.manager_name,
            riskRating: p.risk_rating,
            valueA: p.market_value,
            valueB: null,
          });
        }
        for (const p of posB) {
          const existing = byAsset.get(p.asset_id);
          if (existing) {
            existing.valueB = p.market_value;
            existing.quantityB = p.quantity;
            existing.dueDate = p.due_date ?? existing.dueDate;
            existing.rate = p.rate ?? existing.rate;
            existing.indexDescription = p.index_description ?? existing.indexDescription;
            existing.managerName = p.manager_name ?? existing.managerName;
            existing.riskRating = p.risk_rating ?? existing.riskRating;
          } else {
            byAsset.set(p.asset_id, {
              assetId: p.asset_id,
              assetName: p.asset_name,
              assetClass: p.asset_class,
              issuer: p.issuer,
              dueDate: p.due_date,
              quantityA: null,
              quantityB: p.quantity,
              rate: p.rate,
              indexDescription: p.index_description,
              managerName: p.manager_name,
              riskRating: p.risk_rating,
              valueA: null,
              valueB: p.market_value,
            });
          }
        }

        if (!cancelled) setRows(Array.from(byAsset.values()));
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [clientId, dateA, dateB, compareMode, getToken]);

  if (availableDates.length === 0) return null;

  const totalA = rows.reduce((sum, r) => sum + (r.valueA ?? 0), 0);
  const totalB = rows.reduce((sum, r) => sum + (r.valueB ?? 0), 0);

  function pctOf(row: Row): number | null {
    if (row.valueB !== null && totalB > 0) return (row.valueB / totalB) * 100;
    if (row.valueA !== null && totalA > 0) return (row.valueA / totalA) * 100;
    return null;
  }

  function handleSort(key: string) {
    if (key === sortKey) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key as SortKey);
      setSortDir(key === "assetName" ? "asc" : "desc");
    }
  }

  function compareRows(a: Row, b: Row): number {
    let cmp = 0;
    if (sortKey === "assetName") cmp = a.assetName.localeCompare(b.assetName);
    else if (sortKey === "dueDate") cmp = (a.dueDate ?? "").localeCompare(b.dueDate ?? "");
    else if (sortKey === "valueA") cmp = (a.valueA ?? 0) - (b.valueA ?? 0);
    else if (sortKey === "valueB") cmp = (a.valueB ?? 0) - (b.valueB ?? 0);
    else if (sortKey === "pct") cmp = (pctOf(a) ?? 0) - (pctOf(b) ?? 0);
    else if (sortKey === "delta") cmp = (a.valueB ?? 0) - (a.valueA ?? 0) - ((b.valueB ?? 0) - (b.valueA ?? 0));
    return sortDir === "asc" ? cmp : -cmp;
  }

  // agrupa por classe de ativo; grupos ordenados por valor total desc,
  // linhas dentro de cada grupo respeitam o sort ativo (default alfabetico)
  const groupsMap = new Map<string, Row[]>();
  for (const row of rows) {
    const list = groupsMap.get(row.assetClass) ?? [];
    list.push(row);
    groupsMap.set(row.assetClass, list);
  }
  const groups = Array.from(groupsMap.entries())
    .map(([assetClass, groupRows]) => {
      const groupTotalA = groupRows.reduce((sum, r) => sum + (r.valueA ?? 0), 0);
      const groupTotalB = groupRows.reduce((sum, r) => sum + (r.valueB ?? 0), 0);
      return {
        assetClass,
        rows: [...groupRows].sort(compareRows),
        totalA: groupTotalA,
        totalB: groupTotalB,
      };
    })
    .sort((a, b) => (b.totalB || b.totalA) - (a.totalB || a.totalA));

  const extraColCount = columns.size;

  return (
    <section className="mb-10">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-[#14181F]/70">
          Posições ({rows.length})
        </h2>
        <div className="flex flex-wrap items-center gap-2 text-sm">
          <div className="relative">
            <button
              onClick={() => setShowColumnPicker((v) => !v)}
              className="rounded-md border border-[#14181F]/15 px-2.5 py-1 text-xs font-medium text-[#14181F]/70 transition hover:bg-[#14181F]/5"
            >
              + Colunas
            </button>
            {showColumnPicker && (
              <div className="absolute right-0 top-full z-20 mt-1 w-56 rounded-lg border border-[#14181F]/10 bg-white p-2 shadow-lg">
                {(Object.keys(COLUMN_LABELS) as ColumnKey[]).map((key) => (
                  <label key={key} className="flex items-center gap-2 rounded px-2 py-1.5 text-sm hover:bg-[#14181F]/5">
                    <input
                      type="checkbox"
                      checked={columns.has(key)}
                      onChange={() => setColumns((prev) => toggleInSet(prev, key))}
                      className="h-3.5 w-3.5 rounded border-[#14181F]/30"
                    />
                    {COLUMN_LABELS[key]}
                  </label>
                ))}
              </div>
            )}
          </div>
          <label className="flex items-center gap-1.5 text-xs font-medium text-[#14181F]/70">
            <input
              type="checkbox"
              checked={compareMode}
              onChange={(e) => setCompareMode(e.target.checked)}
              className="h-3.5 w-3.5 rounded border-[#14181F]/30"
            />
            Comparar com outra data
          </label>
          {compareMode && (
            <>
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
            </>
          )}
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
        <p className="text-sm text-[#14181F]/50">Carregando posições...</p>
      ) : rows.length === 0 ? (
        <p className="text-sm text-[#14181F]/50">Nenhuma posição sincronizada.</p>
      ) : (
        <div className="overflow-x-auto card">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[#14181F]/10 text-left text-xs uppercase tracking-wide text-[#14181F]/40">
                <SortableTh label="Ativo" sortKey="assetName" currentSort={sortKey} currentDir={sortDir} onSort={handleSort} />
                <th className="px-4 py-3 font-medium">Classe</th>
                {columns.has("dueDate") && (
                  <SortableTh label="Vencimento" sortKey="dueDate" currentSort={sortKey} currentDir={sortDir} onSort={handleSort} />
                )}
                {columns.has("quantity") && <th className="px-4 py-3 text-right font-medium">Quantidade</th>}
                {columns.has("issuer") && <th className="px-4 py-3 font-medium">Emissor</th>}
                {columns.has("manager") && <th className="px-4 py-3 font-medium">Gestora</th>}
                {columns.has("index") && <th className="px-4 py-3 font-medium">Indexador / Taxa</th>}
                {columns.has("risk") && <th className="px-4 py-3 font-medium">Risco</th>}
                {compareMode && (
                  <SortableTh label={`PL (${formatDate(dateA)})`} sortKey="valueA" currentSort={sortKey} currentDir={sortDir} onSort={handleSort} align="right" />
                )}
                <SortableTh label={compareMode ? `PL (${formatDate(dateB)})` : "PL"} sortKey="valueB" currentSort={sortKey} currentDir={sortDir} onSort={handleSort} align="right" />
                <SortableTh label="% carteira" sortKey="pct" currentSort={sortKey} currentDir={sortDir} onSort={handleSort} align="right" />
                {compareMode && (
                  <SortableTh label="Δ" sortKey="delta" currentSort={sortKey} currentDir={sortDir} onSort={handleSort} align="right" />
                )}
              </tr>
            </thead>
            <tbody>
              {groups.map((group) => {
                const collapsed = collapsedClasses.has(group.assetClass);
                const groupDelta = group.totalB - group.totalA;
                const groupDeltaColor = groupDelta > 0 ? "#3F7D5B" : groupDelta < 0 ? "#B23A48" : "#14181F66";
                const groupPct = totalB > 0 ? (group.totalB / totalB) * 100 : totalA > 0 ? (group.totalA / totalA) * 100 : null;
                return (
                  <Fragment key={group.assetClass}>
                    <tr
                      className="cursor-pointer border-b border-[#14181F]/10 bg-[#14181F]/[0.025] hover:bg-[#14181F]/5"
                      onClick={() => setCollapsedClasses((prev) => toggleInSet(prev, group.assetClass))}
                    >
                      <td className="px-4 py-2.5 font-semibold" colSpan={2 + extraColCount}>
                        <span className={`inline-block transition-transform ${collapsed ? "" : "rotate-90"}`}>▸</span>{" "}
                        {ASSET_CLASS_LABELS[group.assetClass] ?? group.assetClass}
                        <span className="ml-1.5 font-mono text-xs font-normal tabular-nums text-[#14181F]/40">
                          ({group.rows.length})
                        </span>
                      </td>
                      {compareMode && (
                        <td className="px-4 py-2.5 text-right font-mono font-semibold tabular-nums">
                          {formatCurrency(group.totalA)}
                        </td>
                      )}
                      <td className="px-4 py-2.5 text-right font-mono font-semibold tabular-nums">
                        {formatCurrency(group.totalB)}
                      </td>
                      <td className="px-4 py-2.5 text-right font-mono font-semibold tabular-nums text-[#14181F]/60">
                        {groupPct !== null ? `${groupPct.toFixed(1)}%` : "—"}
                      </td>
                      {compareMode && (
                        <td className="px-4 py-2.5 text-right font-mono font-semibold tabular-nums" style={{ color: groupDeltaColor }}>
                          {groupDelta === 0 ? "—" : `${groupDelta > 0 ? "+" : "−"} ${formatCurrency(Math.abs(groupDelta))}`}
                        </td>
                      )}
                    </tr>
                    {!collapsed &&
                      group.rows.map((row) => {
                        const a = row.valueA ?? 0;
                        const b = row.valueB ?? 0;
                        const delta = b - a;
                        const deltaPct = a > 0 ? (delta / a) * 100 : null;
                        const deltaColor = delta > 0 ? "#3F7D5B" : delta < 0 ? "#B23A48" : "#14181F66";
                        const pct = pctOf(row);
                        return (
                          <tr key={row.assetId} className="border-b border-[#14181F]/5 last:border-0">
                            <td className="px-4 py-3 pl-8">
                              <p className="font-medium">{row.assetName}</p>
                              {!columns.has("issuer") && row.issuer && (
                                <p className="text-xs text-[#14181F]/40">{row.issuer}</p>
                              )}
                              {compareMode && row.valueA === null && (
                                <p className="text-xs text-[#3F7D5B]">novo em {formatDate(dateB)}</p>
                              )}
                              {compareMode && row.valueB === null && (
                                <p className="text-xs text-[#B23A48]">encerrado após {formatDate(dateA)}</p>
                              )}
                            </td>
                            <td className="px-4 py-3 text-[#14181F]/70">
                              {ASSET_CLASS_LABELS[row.assetClass] ?? row.assetClass}
                            </td>
                            {columns.has("dueDate") && (
                              <td className="px-4 py-3 font-mono text-[#14181F]/70">
                                {row.dueDate ? formatDate(row.dueDate) : "—"}
                              </td>
                            )}
                            {columns.has("quantity") && (
                              <td className="px-4 py-3 text-right font-mono tabular-nums text-[#14181F]/70">
                                {formatQuantity(compareMode ? row.quantityB ?? row.quantityA : row.quantityB)}
                              </td>
                            )}
                            {columns.has("issuer") && (
                              <td className="px-4 py-3 text-[#14181F]/70">{row.issuer ?? "—"}</td>
                            )}
                            {columns.has("manager") && (
                              <td className="px-4 py-3 text-[#14181F]/70">{row.managerName ?? "—"}</td>
                            )}
                            {columns.has("index") && (
                              <td className="px-4 py-3 text-[#14181F]/70">
                                {row.indexDescription ?? (row.rate !== null ? `${row.rate}%` : "—")}
                              </td>
                            )}
                            {columns.has("risk") && (
                              <td className="px-4 py-3 text-[#14181F]/70">{row.riskRating ?? "—"}</td>
                            )}
                            {compareMode && (
                              <td className="px-4 py-3 text-right font-mono tabular-nums">
                                {formatCurrency(row.valueA)}
                              </td>
                            )}
                            <td className="px-4 py-3 text-right font-mono tabular-nums">
                              {formatCurrency(row.valueB)}
                            </td>
                            <td className="px-4 py-3 text-right font-mono tabular-nums text-[#14181F]/50">
                              {pct !== null ? `${pct.toFixed(1)}%` : "—"}
                            </td>
                            {compareMode && (
                              <td className="px-4 py-3 text-right font-mono tabular-nums" style={{ color: deltaColor }}>
                                {delta === 0 ? "—" : `${delta > 0 ? "+" : "−"} ${formatCurrency(Math.abs(delta))}`}
                                {deltaPct !== null && (
                                  <span className="ml-1 text-xs opacity-70">
                                    ({delta >= 0 ? "+" : "−"}{Math.abs(deltaPct).toFixed(1)}%)
                                  </span>
                                )}
                              </td>
                            )}
                          </tr>
                        );
                      })}
                  </Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
