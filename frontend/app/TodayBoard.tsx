"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useAuth } from "@clerk/nextjs";
import { useRouter } from "next/navigation";

export type TodayItem = {
  kind: "alert" | "insight";
  id: string;
  severity: "critical" | "opportunity" | "follow_up";
  typeLabel: string;
  title: string | null;
  explanation: string | null;
  status: string;
  firstSeenAt: string | null;
};

export type ClientGroup = {
  clientId: string;
  clientName: string;
  clientSuitability: string | null;
  priorityScore: number;
  items: TodayItem[];
};

export const SEVERITY_CONFIG = {
  critical: { label: "Crítico", accent: "#B23A48" },
  opportunity: { label: "Oportunidade", accent: "#A6790A" },
  follow_up: { label: "Follow-up", accent: "#3E5C76" },
} as const;

export const SEVERITY_ORDER: (keyof typeof SEVERITY_CONFIG)[] = ["critical", "opportunity", "follow_up"];
const PAGE_SIZE = 10;

function formatFirstSeen(value: string): string {
  return new Date(value).toLocaleDateString("pt-BR", { day: "2-digit", month: "short", year: "numeric" });
}

function itemKey(item: TodayItem): string {
  return `${item.kind}:${item.id}`;
}

function defaultDueDate(): string {
  const d = new Date();
  d.setDate(d.getDate() + 7);
  return d.toISOString().split("T")[0];
}

function endpointBase(kind: "alert" | "insight"): string {
  return kind === "alert" ? "alerts" : "insights";
}

function toggleInSet<T>(set: Set<T>, value: T): Set<T> {
  const next = new Set(set);
  if (next.has(value)) next.delete(value);
  else next.add(value);
  return next;
}

export default function TodayBoard({ groups }: { groups: ClientGroup[] }) {
  const { getToken } = useAuth();
  const router = useRouter();

  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [pendingIds, setPendingIds] = useState<Set<string>>(new Set());
  const [bulkNote, setBulkNote] = useState("");
  const [bulkPending, setBulkPending] = useState(false);

  const [actionModal, setActionModal] = useState<{ item: TodayItem; newStatus: "actioned" | "dismissed" } | null>(null);
  const [actionNote, setActionNote] = useState("");

  const [taskModal, setTaskModal] = useState<TodayItem | null>(null);
  const [taskDescription, setTaskDescription] = useState("");
  const [taskDueDate, setTaskDueDate] = useState(defaultDueDate());
  const [taskCreatedIds, setTaskCreatedIds] = useState<Set<string>>(new Set());

  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());
  const [page, setPage] = useState(1);

  useEffect(() => {
    setPage(1);
  }, [groups]);

  const totalPages = Math.max(1, Math.ceil(groups.length / PAGE_SIZE));
  const safePage = Math.min(page, totalPages);
  const pagedGroups = groups.slice((safePage - 1) * PAGE_SIZE, safePage * PAGE_SIZE);

  function toggleExpanded(clientId: string) {
    setExpandedIds((prev) => toggleInSet(prev, clientId));
  }

  function toggleSelected(key: string) {
    setSelected((prev) => toggleInSet(prev, key));
  }

  function toggleClientSelected(group: ClientGroup) {
    const keys = group.items.map(itemKey);
    const allSelected = keys.every((k) => selected.has(k));
    setSelected((prev) => {
      const next = new Set(prev);
      if (allSelected) keys.forEach((k) => next.delete(k));
      else keys.forEach((k) => next.add(k));
      return next;
    });
  }

  async function patchStatus(item: TodayItem, newStatus: string, note: string) {
    const token = await getToken();
    const params = new URLSearchParams({ new_status: newStatus });
    if (note.trim()) params.set("note", note.trim());
    await fetch(`${process.env.NEXT_PUBLIC_API_URL}/${endpointBase(item.kind)}/${item.id}?${params.toString()}`, {
      method: "PATCH",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
  }

  async function confirmAction() {
    if (!actionModal) return;
    const key = itemKey(actionModal.item);
    setPendingIds((prev) => new Set(prev).add(key));
    try {
      await patchStatus(actionModal.item, actionModal.newStatus, actionNote);
      setActionModal(null);
      setActionNote("");
      router.refresh();
    } finally {
      setPendingIds((prev) => {
        const next = new Set(prev);
        next.delete(key);
        return next;
      });
    }
  }

  async function submitTask() {
    if (!taskModal) return;
    const key = itemKey(taskModal);
    setPendingIds((prev) => new Set(prev).add(key));
    try {
      const token = await getToken();
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/${endpointBase(taskModal.kind)}/${taskModal.id}/tasks`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: JSON.stringify({ description: taskDescription, due_date: taskDueDate }),
        }
      );
      if (res.ok) {
        setTaskCreatedIds((prev) => new Set(prev).add(key));
        setTaskModal(null);
      }
    } finally {
      setPendingIds((prev) => {
        const next = new Set(prev);
        next.delete(key);
        return next;
      });
    }
  }

  async function bulkAction(newStatus: "actioned" | "dismissed") {
    setBulkPending(true);
    try {
      const targets = groups.flatMap((g) => g.items).filter((item) => selected.has(itemKey(item)));
      await Promise.all(targets.map((item) => patchStatus(item, newStatus, bulkNote)));
      setSelected(new Set());
      setBulkNote("");
      router.refresh();
    } finally {
      setBulkPending(false);
    }
  }

  function openTaskModal(item: TodayItem) {
    setTaskModal(item);
    setTaskDescription(item.explanation ?? item.title ?? "");
    setTaskDueDate(defaultDueDate());
  }

  return (
    <div>
      <div
        className={`sticky top-3 z-40 mb-6 card flex flex-wrap items-center gap-3 border-[#14181F]/20 bg-white p-3 shadow-md transition ${
          selected.size === 0 ? "opacity-50" : ""
        }`}
      >
        <span className="text-sm font-medium">
          {selected.size} {selected.size === 1 ? "selecionado" : "selecionados"}
        </span>
        <input
          type="text"
          placeholder="Nota opcional (aplica a todos)"
          value={bulkNote}
          onChange={(e) => setBulkNote(e.target.value)}
          disabled={selected.size === 0}
          className="min-w-[200px] flex-1 rounded-md border border-[#14181F]/15 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#14181F]/20 disabled:cursor-not-allowed"
        />
        <button
          onClick={() => bulkAction("actioned")}
          disabled={bulkPending || selected.size === 0}
          className="rounded-md bg-[#14181F] px-3 py-1.5 text-xs font-medium text-white transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-40"
        >
          Acionar selecionados
        </button>
        <button
          onClick={() => bulkAction("dismissed")}
          disabled={bulkPending || selected.size === 0}
          className="rounded-md border border-[#14181F]/15 px-3 py-1.5 text-xs font-medium text-[#14181F]/70 transition hover:bg-[#14181F]/5 disabled:cursor-not-allowed disabled:opacity-40"
        >
          Descartar selecionados
        </button>
        <button
          onClick={() => setSelected(new Set())}
          disabled={bulkPending || selected.size === 0}
          className="text-xs font-medium text-[#14181F]/40 hover:text-[#14181F]/70 disabled:cursor-not-allowed disabled:opacity-40"
        >
          Limpar seleção
        </button>
      </div>

      {groups.length === 0 ? (
        <div className="rounded-lg border border-dashed border-[#14181F]/15 py-16 text-center">
          <p className="text-lg font-medium">Nenhum item com esses filtros.</p>
        </div>
      ) : (
        <div className="space-y-4">
            {pagedGroups.map((group) => {
              const keys = group.items.map(itemKey);
              const allSelected = keys.length > 0 && keys.every((k) => selected.has(k));
              const isExpanded = expandedIds.has(group.clientId);
              return (
                <section key={group.clientId} className="card p-4">
                  <div className="flex items-center justify-between gap-3">
                    <div className="flex items-center gap-3">
                      <input
                        type="checkbox"
                        checked={allSelected}
                        onChange={() => toggleClientSelected(group)}
                        className="h-4 w-4 rounded border-[#14181F]/30"
                        aria-label={`Selecionar tudo de ${group.clientName}`}
                      />
                      <button
                        onClick={() => toggleExpanded(group.clientId)}
                        className="text-[#14181F]/40 transition hover:text-[#14181F]/70"
                        aria-label={isExpanded ? "Recolher" : "Expandir"}
                      >
                        <span className={`inline-block transition-transform ${isExpanded ? "rotate-90" : ""}`}>
                          ▸
                        </span>
                      </button>
                      <Link
                        href={`/clientes/${group.clientId}`}
                        className="font-display text-lg font-semibold hover:underline"
                      >
                        {group.clientName}
                      </Link>
                    </div>
                    <span className="font-mono text-xs tabular-nums text-[#14181F]/40">
                      {group.items.length} {group.items.length === 1 ? "item" : "itens"}
                    </span>
                  </div>

                  {!isExpanded && (
                    <button
                      onClick={() => toggleExpanded(group.clientId)}
                      className="mt-3 flex flex-wrap gap-1.5 text-left"
                    >
                      {group.items.map((item) => {
                        const config = SEVERITY_CONFIG[item.severity];
                        return (
                          <span
                            key={itemKey(item)}
                            className="rounded-full px-2 py-0.5 text-xs font-medium uppercase tracking-wide"
                            style={{ backgroundColor: `${config.accent}1a`, color: config.accent }}
                          >
                            {item.typeLabel}
                          </span>
                        );
                      })}
                    </button>
                  )}

                  {isExpanded && (
                    <div className="mt-3 space-y-2 border-t border-[#14181F]/10 pt-3">
                      {group.items.map((item) => {
                        const key = itemKey(item);
                        const config = SEVERITY_CONFIG[item.severity];
                        const pending = pendingIds.has(key);
                        const taskCreated = taskCreatedIds.has(key);
                        return (
                          <div key={key} className="flex items-start gap-3 rounded-md border border-[#14181F]/10 p-3">
                            <input
                              type="checkbox"
                              checked={selected.has(key)}
                              onChange={() => toggleSelected(key)}
                              className="mt-1 h-4 w-4 shrink-0 rounded border-[#14181F]/30"
                              aria-label="Selecionar item"
                            />
                            <div className="min-w-0 flex-1">
                              <div className="flex items-baseline gap-2">
                                <span
                                  className="rounded-full px-2 py-0.5 text-xs font-medium uppercase tracking-wide"
                                  style={{ backgroundColor: `${config.accent}1a`, color: config.accent }}
                                >
                                  {item.typeLabel}
                                </span>
                                <span className="text-xs uppercase tracking-wide text-[#14181F]/30">
                                  {item.kind === "insight" ? "insight" : "alerta"}
                                </span>
                              </div>
                              {item.title && <p className="mt-1 text-sm font-medium">{item.title}</p>}
                              <p className="mt-1 text-sm leading-relaxed text-[#14181F]/70">{item.explanation}</p>
                              {item.firstSeenAt && (
                                <p className="mt-1 text-xs text-[#14181F]/40">
                                  Identificado em {formatFirstSeen(item.firstSeenAt)}
                                </p>
                              )}
                            </div>
                            <div className="flex shrink-0 flex-col gap-1.5">
                              <button
                                onClick={() => openTaskModal(item)}
                                disabled={pending || taskCreated}
                                className="rounded-md border border-[#14181F]/15 px-3 py-1.5 text-xs font-medium text-[#14181F]/70 transition hover:bg-[#14181F]/5 disabled:opacity-40"
                              >
                                {taskCreated ? "Lembrete criado ✓" : "Lembrar depois"}
                              </button>
                              <button
                                onClick={() => setActionModal({ item, newStatus: "actioned" })}
                                disabled={pending}
                                className="rounded-md bg-[#14181F] px-3 py-1.5 text-xs font-medium text-white transition hover:opacity-90 disabled:opacity-40"
                              >
                                Acionar
                              </button>
                              <button
                                onClick={() => setActionModal({ item, newStatus: "dismissed" })}
                                disabled={pending}
                                className="rounded-md border border-[#14181F]/15 px-3 py-1.5 text-xs font-medium text-[#14181F]/70 transition hover:bg-[#14181F]/5 disabled:opacity-40"
                              >
                                Descartar
                              </button>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </section>
              );
            })}
          </div>
        )}

        {totalPages > 1 && (
          <div className="mt-6 flex items-center justify-between">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={safePage <= 1}
              className="rounded-md border border-[#14181F]/15 px-3 py-1.5 text-xs font-medium text-[#14181F]/70 transition hover:bg-[#14181F]/5 disabled:opacity-40"
            >
              ← Anterior
            </button>
            <span className="font-mono text-xs tabular-nums text-[#14181F]/50">
              Página {safePage} de {totalPages} · {groups.length} clientes
            </span>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={safePage >= totalPages}
              className="rounded-md border border-[#14181F]/15 px-3 py-1.5 text-xs font-medium text-[#14181F]/70 transition hover:bg-[#14181F]/5 disabled:opacity-40"
            >
              Próxima →
            </button>
          </div>
        )}

      {actionModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#14181F]/40 px-4">
          <div className="w-full max-w-sm card p-5">
            <h3 className="font-display text-lg font-semibold">
              {actionModal.newStatus === "actioned" ? "Acionar" : "Descartar"}
            </h3>
            <p className="mt-1 text-sm text-[#14181F]/50">{actionModal.item.typeLabel}</p>

            <label className="mt-4 block text-xs font-medium uppercase tracking-wide text-[#14181F]/40">
              Nota (opcional) — por que {actionModal.newStatus === "actioned" ? "acionou" : "descartou"}
            </label>
            <textarea
              value={actionNote}
              onChange={(e) => setActionNote(e.target.value)}
              rows={3}
              className="mt-1 w-full rounded-md border border-[#14181F]/15 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#14181F]/20"
              placeholder="Ex: cliente já ciente, vamos rebalancear na próxima reunião"
            />

            <div className="mt-5 flex justify-end gap-2">
              <button
                onClick={() => {
                  setActionModal(null);
                  setActionNote("");
                }}
                className="rounded-md border border-[#14181F]/15 px-3 py-1.5 text-xs font-medium text-[#14181F]/70 hover:bg-[#14181F]/5"
              >
                Cancelar
              </button>
              <button
                onClick={confirmAction}
                className="rounded-md bg-[#14181F] px-3 py-1.5 text-xs font-medium text-white hover:opacity-90"
              >
                Confirmar
              </button>
            </div>
          </div>
        </div>
      )}

      {taskModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#14181F]/40 px-4">
          <div className="w-full max-w-sm card p-5">
            <h3 className="font-display text-lg font-semibold">Lembrete</h3>
            <p className="mt-1 text-sm text-[#14181F]/50">{taskModal.typeLabel}</p>

            <label className="mt-4 block text-xs font-medium uppercase tracking-wide text-[#14181F]/40">
              O que ver depois
            </label>
            <textarea
              value={taskDescription}
              onChange={(e) => setTaskDescription(e.target.value)}
              rows={3}
              className="mt-1 w-full rounded-md border border-[#14181F]/15 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#14181F]/20"
            />

            <label className="mt-3 block text-xs font-medium uppercase tracking-wide text-[#14181F]/40">
              Quando
            </label>
            <input
              type="date"
              value={taskDueDate}
              onChange={(e) => setTaskDueDate(e.target.value)}
              className="mt-1 w-full rounded-md border border-[#14181F]/15 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#14181F]/20"
            />

            <div className="mt-5 flex justify-end gap-2">
              <button
                onClick={() => setTaskModal(null)}
                className="rounded-md border border-[#14181F]/15 px-3 py-1.5 text-xs font-medium text-[#14181F]/70 hover:bg-[#14181F]/5"
              >
                Cancelar
              </button>
              <button
                onClick={submitTask}
                disabled={!taskDescription.trim()}
                className="rounded-md bg-[#14181F] px-3 py-1.5 text-xs font-medium text-white hover:opacity-90 disabled:opacity-40"
              >
                Salvar lembrete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
