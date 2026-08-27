"use client";

import { useMemo, useState } from "react";
import TodayBoard, { SEVERITY_CONFIG, SEVERITY_ORDER, type ClientGroup } from "./TodayBoard";
import RelationshipWidget, { type RelationshipItem, type RelationshipStatusFilter } from "./RelationshipWidget";

type QuickFilter = "critical" | "opportunity" | "relationship" | "portfolio_changes" | null;

const RELATIONSHIP_TYPE_LABELS = ["Sem contato recente", "Follow-up atrasado"];
const PORTFOLIO_CHANGE_TYPE_LABELS = ["Movimentação relevante"];

function toggleInSet<T>(set: Set<T>, value: T): Set<T> {
  const next = new Set(set);
  if (next.has(value)) next.delete(value);
  else next.add(value);
  return next;
}

function formatSuitability(value: string): string {
  return value.charAt(0) + value.slice(1).toLowerCase();
}

export default function TodayClient({
  groups,
  relationship,
}: {
  groups: ClientGroup[];
  relationship: RelationshipItem[];
}) {
  const [severityFilter, setSeverityFilter] = useState<Set<string>>(new Set());
  const [typeFilter, setTypeFilter] = useState<Set<string>>(new Set());
  const [suitabilityFilter, setSuitabilityFilter] = useState<Set<string>>(new Set());
  const [statusFilter, setStatusFilter] = useState<RelationshipStatusFilter>(null);
  const [quickFilter, setQuickFilter] = useState<QuickFilter>(null);

  const criticalCount = groups.flatMap((g) => g.items).filter((i) => i.severity === "critical").length;
  const opportunityCount = groups.flatMap((g) => g.items).filter((i) => i.severity === "opportunity").length;
  const portfolioChangesCount = groups
    .flatMap((g) => g.items)
    .filter((i) => PORTFOLIO_CHANGE_TYPE_LABELS.includes(i.typeLabel)).length;
  const relationshipCount = relationship.filter((r) => r.status !== "ok").length;

  function applyQuickFilter(kind: QuickFilter) {
    if (quickFilter === kind) {
      setQuickFilter(null);
      setSeverityFilter(new Set());
      setTypeFilter(new Set());
      setStatusFilter(null);
      return;
    }
    setQuickFilter(kind);
    if (kind === "critical") {
      setSeverityFilter(new Set(["critical"]));
      setTypeFilter(new Set());
      setStatusFilter(null);
    } else if (kind === "opportunity") {
      setSeverityFilter(new Set(["opportunity"]));
      setTypeFilter(new Set());
      setStatusFilter(null);
    } else if (kind === "relationship") {
      setSeverityFilter(new Set());
      setTypeFilter(new Set(RELATIONSHIP_TYPE_LABELS));
      setStatusFilter("problem");
    } else if (kind === "portfolio_changes") {
      setSeverityFilter(new Set());
      setTypeFilter(new Set(PORTFOLIO_CHANGE_TYPE_LABELS));
      setStatusFilter(null);
    }
  }

  function manualFilterChange(update: () => void) {
    setQuickFilter(null);
    update();
  }

  const { availableSeverities, availableTypes, availableSuitabilities } = useMemo(() => {
    const severities = new Set<string>();
    const types = new Set<string>();
    const suitabilities = new Set<string>();
    for (const group of groups) {
      if (group.clientSuitability) suitabilities.add(group.clientSuitability);
      for (const item of group.items) {
        severities.add(item.severity);
        types.add(item.typeLabel);
      }
    }
    return {
      availableSeverities: SEVERITY_ORDER.filter((s) => severities.has(s)),
      availableTypes: Array.from(types).sort(),
      availableSuitabilities: Array.from(suitabilities).sort(),
    };
  }, [groups]);

  const filteredGroups = useMemo(() => {
    return groups
      .filter((g) => suitabilityFilter.size === 0 || (g.clientSuitability && suitabilityFilter.has(g.clientSuitability)))
      .map((g) => ({
        ...g,
        items: g.items.filter(
          (item) =>
            (severityFilter.size === 0 || severityFilter.has(item.severity)) &&
            (typeFilter.size === 0 || typeFilter.has(item.typeLabel))
        ),
      }))
      .filter((g) => g.items.length > 0);
  }, [groups, severityFilter, typeFilter, suitabilityFilter]);

  const hasActiveFilters = severityFilter.size > 0 || typeFilter.size > 0 || suitabilityFilter.size > 0 || statusFilter !== null;

  function clearAll() {
    setSeverityFilter(new Set());
    setTypeFilter(new Set());
    setSuitabilityFilter(new Set());
    setStatusFilter(null);
    setQuickFilter(null);
  }

  return (
    <>
      <div className="mb-8 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <button
          onClick={() => applyQuickFilter("critical")}
          className={`card p-3 text-left transition ${quickFilter === "critical" ? "ring-2 ring-[#B23A48]/50" : "hover:bg-[#14181F]/[0.02]"}`}
        >
          <p className="font-mono text-xl font-semibold tabular-nums" style={{ color: "#B23A48" }}>
            {criticalCount}
          </p>
          <p className="text-xs text-[#14181F]/50">Critical</p>
        </button>
        <button
          onClick={() => applyQuickFilter("opportunity")}
          className={`card p-3 text-left transition ${quickFilter === "opportunity" ? "ring-2 ring-[#A6790A]/50" : "hover:bg-[#14181F]/[0.02]"}`}
        >
          <p className="font-mono text-xl font-semibold tabular-nums" style={{ color: "#A6790A" }}>
            {opportunityCount}
          </p>
          <p className="text-xs text-[#14181F]/50">Opportunities</p>
        </button>
        <button
          onClick={() => applyQuickFilter("relationship")}
          className={`card p-3 text-left transition ${quickFilter === "relationship" ? "ring-2 ring-[#3E5C76]/50" : "hover:bg-[#14181F]/[0.02]"}`}
        >
          <p className="font-mono text-xl font-semibold tabular-nums" style={{ color: "#3E5C76" }}>
            {relationshipCount}
          </p>
          <p className="text-xs text-[#14181F]/50">Relationship</p>
        </button>
        <button
          onClick={() => applyQuickFilter("portfolio_changes")}
          className={`card p-3 text-left transition ${quickFilter === "portfolio_changes" ? "ring-2 ring-[#14181F]/30" : "hover:bg-[#14181F]/[0.02]"}`}
        >
          <p className="font-mono text-xl font-semibold tabular-nums">{portfolioChangesCount}</p>
          <p className="text-xs text-[#14181F]/50">Portfolio changes</p>
        </button>
      </div>

      <div className="flex flex-col gap-8 lg:flex-row">
        <aside className="shrink-0 lg:w-56">
          <div className="lg:sticky lg:top-6">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-xs font-semibold uppercase tracking-wide text-[#14181F]/50">Filtros</h2>
              {hasActiveFilters && (
                <button onClick={clearAll} className="text-xs font-medium text-[#14181F]/40 hover:text-[#14181F]/70">
                  Limpar
                </button>
              )}
            </div>

            <div className="space-y-5">
              <div>
                <p className="mb-2 text-xs font-medium uppercase tracking-wide text-[#14181F]/40">Severidade</p>
                <div className="space-y-1.5">
                  {availableSeverities.map((s) => (
                    <label key={s} className="flex items-center gap-2 text-sm">
                      <input
                        type="checkbox"
                        checked={severityFilter.has(s)}
                        onChange={() => manualFilterChange(() => setSeverityFilter((prev) => toggleInSet(prev, s)))}
                        className="h-3.5 w-3.5 rounded border-[#14181F]/30"
                      />
                      <span
                        className="h-1.5 w-1.5 rounded-full"
                        style={{ backgroundColor: SEVERITY_CONFIG[s as keyof typeof SEVERITY_CONFIG].accent }}
                      />
                      {SEVERITY_CONFIG[s as keyof typeof SEVERITY_CONFIG].label}
                    </label>
                  ))}
                </div>
              </div>

              <div>
                <p className="mb-2 text-xs font-medium uppercase tracking-wide text-[#14181F]/40">Tipo de sinal</p>
                <div className="space-y-1.5">
                  {availableTypes.map((t) => (
                    <label key={t} className="flex items-center gap-2 text-sm">
                      <input
                        type="checkbox"
                        checked={typeFilter.has(t)}
                        onChange={() => manualFilterChange(() => setTypeFilter((prev) => toggleInSet(prev, t)))}
                        className="h-3.5 w-3.5 rounded border-[#14181F]/30"
                      />
                      {t}
                    </label>
                  ))}
                </div>
              </div>

              {availableSuitabilities.length > 0 && (
                <div>
                  <p className="mb-2 text-xs font-medium uppercase tracking-wide text-[#14181F]/40">Suitability</p>
                  <div className="space-y-1.5">
                    {availableSuitabilities.map((s) => (
                      <label key={s} className="flex items-center gap-2 text-sm">
                        <input
                          type="checkbox"
                          checked={suitabilityFilter.has(s)}
                          onChange={() => manualFilterChange(() => setSuitabilityFilter((prev) => toggleInSet(prev, s)))}
                          className="h-3.5 w-3.5 rounded border-[#14181F]/30"
                        />
                        {formatSuitability(s)}
                      </label>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </aside>

        <div className="min-w-0 flex-1 space-y-10">
          {relationship.length > 0 && (
            <section>
              <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-[#14181F]/70">
                My Client Relationship
              </h2>
              <RelationshipWidget
                items={relationship}
                statusFilter={statusFilter}
                onStatusFilterChange={(f) => {
                  setQuickFilter(null);
                  setStatusFilter(f);
                }}
              />
            </section>
          )}

          <section>
            <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-[#14181F]/70">
              Alertas &amp; Insights
            </h2>
            <TodayBoard groups={filteredGroups} />
          </section>
        </div>
      </div>
    </>
  );
}
