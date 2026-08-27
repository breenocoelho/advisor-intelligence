"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import SortableTh from "../SortableTh";
import ScoreTooltip, { type ScoreBreakdownItem } from "../ScoreTooltip";

type Client = {
  id: string;
  xp_client_id: string | null;
  name: string;
  aum: number | null;
  suitability: string | null;
  advisor_name: string | null;
  priority_score: number;
  health_score: number | null;
  health_score_breakdown: ScoreBreakdownItem[];
  relationship_score: number | null;
  relationship_score_band: string | null;
  relationship_score_breakdown: ScoreBreakdownItem[];
};

type SortKey =
  | "name"
  | "advisor_name"
  | "suitability"
  | "aum"
  | "health_score"
  | "relationship_score"
  | "priority_score";

function formatCurrency(value: number | null): string {
  if (value === null) return "—";
  return value.toLocaleString("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 });
}

function formatSuitability(value: string | null): string {
  if (!value) return "—";
  return value.charAt(0) + value.slice(1).toLowerCase();
}

function toggleInSet<T>(set: Set<T>, value: T): Set<T> {
  const next = new Set(set);
  if (next.has(value)) next.delete(value);
  else next.add(value);
  return next;
}

export default function ClientesTable({ clients }: { clients: Client[] }) {
  const [search, setSearch] = useState("");
  const [advisorFilter, setAdvisorFilter] = useState<Set<string>>(new Set());
  const [suitabilityFilter, setSuitabilityFilter] = useState<Set<string>>(new Set());
  const [sortKey, setSortKey] = useState<SortKey>("priority_score");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");

  const advisors = useMemo(() => {
    const set = new Set(clients.map((c) => c.advisor_name).filter(Boolean) as string[]);
    return Array.from(set).sort();
  }, [clients]);

  const suitabilities = useMemo(() => {
    const set = new Set(clients.map((c) => c.suitability).filter(Boolean) as string[]);
    return Array.from(set).sort();
  }, [clients]);

  function handleSort(key: string) {
    if (key === sortKey) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key as SortKey);
      setSortDir(key === "name" ? "asc" : "desc");
    }
  }

  const filtered = clients.filter((c) => {
    const matchesSearch =
      search.trim() === "" ||
      c.name.toLowerCase().includes(search.toLowerCase()) ||
      (c.xp_client_id ?? "").includes(search);
    const matchesAdvisor = advisorFilter.size === 0 || (c.advisor_name && advisorFilter.has(c.advisor_name));
    const matchesSuitability = suitabilityFilter.size === 0 || (c.suitability && suitabilityFilter.has(c.suitability));
    return matchesSearch && matchesAdvisor && matchesSuitability;
  });

  const sorted = [...filtered].sort((a, b) => {
    let cmp = 0;
    if (sortKey === "name") cmp = a.name.localeCompare(b.name);
    else if (sortKey === "advisor_name") cmp = (a.advisor_name ?? "").localeCompare(b.advisor_name ?? "");
    else if (sortKey === "suitability") cmp = (a.suitability ?? "").localeCompare(b.suitability ?? "");
    else if (sortKey === "aum") cmp = (a.aum ?? 0) - (b.aum ?? 0);
    else if (sortKey === "health_score") cmp = (a.health_score ?? -1) - (b.health_score ?? -1);
    else if (sortKey === "relationship_score") cmp = (a.relationship_score ?? -1) - (b.relationship_score ?? -1);
    else if (sortKey === "priority_score") cmp = a.priority_score - b.priority_score;
    return sortDir === "asc" ? cmp : -cmp;
  });

  const hasActiveFilters = advisorFilter.size > 0 || suitabilityFilter.size > 0;

  return (
    <div className="flex flex-col gap-8 lg:flex-row">
      <aside className="shrink-0 lg:w-56">
        <div className="lg:sticky lg:top-6">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-xs font-semibold uppercase tracking-wide text-[#14181F]/50">Filtros</h2>
            {hasActiveFilters && (
              <button
                onClick={() => {
                  setAdvisorFilter(new Set());
                  setSuitabilityFilter(new Set());
                }}
                className="text-xs font-medium text-[#14181F]/40 hover:text-[#14181F]/70"
              >
                Limpar
              </button>
            )}
          </div>
          <div className="space-y-5">
            <div>
              <p className="mb-2 text-xs font-medium uppercase tracking-wide text-[#14181F]/40">Assessor</p>
              <div className="space-y-1.5">
                {advisors.map((a) => (
                  <label key={a} className="flex items-center gap-2 text-sm">
                    <input
                      type="checkbox"
                      checked={advisorFilter.has(a)}
                      onChange={() => setAdvisorFilter((prev) => toggleInSet(prev, a))}
                      className="h-3.5 w-3.5 rounded border-[#14181F]/30"
                    />
                    {a}
                  </label>
                ))}
              </div>
            </div>
            <div>
              <p className="mb-2 text-xs font-medium uppercase tracking-wide text-[#14181F]/40">Suitability</p>
              <div className="space-y-1.5">
                {suitabilities.map((s) => (
                  <label key={s} className="flex items-center gap-2 text-sm">
                    <input
                      type="checkbox"
                      checked={suitabilityFilter.has(s)}
                      onChange={() => setSuitabilityFilter((prev) => toggleInSet(prev, s))}
                      className="h-3.5 w-3.5 rounded border-[#14181F]/30"
                    />
                    {formatSuitability(s)}
                  </label>
                ))}
              </div>
            </div>
          </div>
        </div>
      </aside>

      <div className="min-w-0 flex-1">
        <input
          type="text"
          placeholder="Buscar por nome ou código..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="mb-4 w-full rounded-md border border-[#14181F]/15 bg-white px-3 py-2 text-sm placeholder:text-[#14181F]/30 focus:outline-none focus:ring-2 focus:ring-[#14181F]/20 sm:max-w-xs"
        />

        {sorted.length === 0 ? (
          <div className="rounded-lg border border-dashed border-[#14181F]/15 py-16 text-center">
            <p className="text-lg font-medium">Nenhum cliente encontrado.</p>
          </div>
        ) : (
          <div className="overflow-hidden card">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[#14181F]/10 text-left text-xs uppercase tracking-wide text-[#14181F]/40">
                  <SortableTh label="Cliente" sortKey="name" currentSort={sortKey} currentDir={sortDir} onSort={handleSort} />
                  <SortableTh label="Assessor" sortKey="advisor_name" currentSort={sortKey} currentDir={sortDir} onSort={handleSort} />
                  <SortableTh label="Perfil" sortKey="suitability" currentSort={sortKey} currentDir={sortDir} onSort={handleSort} />
                  <SortableTh label="AUM" sortKey="aum" currentSort={sortKey} currentDir={sortDir} onSort={handleSort} align="right" />
                  <SortableTh label="Health" sortKey="health_score" currentSort={sortKey} currentDir={sortDir} onSort={handleSort} align="right" />
                  <SortableTh label="Relationship" sortKey="relationship_score" currentSort={sortKey} currentDir={sortDir} onSort={handleSort} align="right" />
                  <SortableTh label="Prioridade" sortKey="priority_score" currentSort={sortKey} currentDir={sortDir} onSort={handleSort} align="right" />
                </tr>
              </thead>
              <tbody>
                {sorted.map((client) => (
                  <tr
                    key={client.id}
                    className="border-b border-[#14181F]/5 last:border-0 hover:bg-[#14181F]/[0.02]"
                  >
                    <td className="px-4 py-3">
                      <Link
                        href={`/clientes/${client.id}`}
                        className="font-medium hover:underline underline-offset-2"
                      >
                        {client.name}
                      </Link>
                      <p className="text-xs text-[#14181F]/40">#{client.xp_client_id}</p>
                    </td>
                    <td className="px-4 py-3 text-[#14181F]/70">{client.advisor_name ?? "—"}</td>
                    <td className="px-4 py-3 text-[#14181F]/70">
                      {formatSuitability(client.suitability)}
                    </td>
                    <td className="px-4 py-3 text-right font-mono tabular-nums">
                      {formatCurrency(client.aum)}
                    </td>
                    <td className="px-4 py-3 text-right">
                      {client.health_score !== null ? (
                        <ScoreTooltip score={client.health_score} breakdown={client.health_score_breakdown} />
                      ) : (
                        <span className="text-[#14181F]/25">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-right">
                      {client.relationship_score !== null ? (
                        <ScoreTooltip
                          score={client.relationship_score}
                          band={client.relationship_score_band}
                          breakdown={client.relationship_score_breakdown}
                        />
                      ) : (
                        <span className="text-[#14181F]/25">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-right">
                      {client.priority_score > 0 ? (
                        <span className="inline-flex items-center rounded-full bg-[#B23A48]/10 px-2 py-0.5 font-mono text-xs font-medium tabular-nums text-[#B23A48]">
                          {client.priority_score}
                        </span>
                      ) : (
                        <span className="text-[#14181F]/25">—</span>
                      )}
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
