"use client";

import { useState } from "react";
import { useAuth } from "@clerk/nextjs";

type Alert = {
  id: string;
  client_name: string | null;
  explanation: string | null;
  status: string;
};

function defaultDueDate(): string {
  const d = new Date();
  d.setDate(d.getDate() + 7);
  return d.toISOString().split("T")[0];
}

export default function AlertCard({
  alert,
  accent,
  typeLabel,
}: {
  alert: Alert;
  accent: string;
  typeLabel: string;
}) {
  const { getToken } = useAuth();
  const [status, setStatus] = useState(alert.status);
  const [pending, setPending] = useState(false);
  const [taskCreated, setTaskCreated] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [description, setDescription] = useState(alert.explanation ?? "");
  const [dueDate, setDueDate] = useState(defaultDueDate());

  async function updateStatus(newStatus: string) {
    setPending(true);
    try {
      const token = await getToken();
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/alerts/${alert.id}?new_status=${newStatus}`,
        {
          method: "PATCH",
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        }
      );
      if (res.ok) setStatus(newStatus);
    } finally {
      setPending(false);
    }
  }

  async function submitTask() {
    setPending(true);
    try {
      const token = await getToken();
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/alerts/${alert.id}/tasks`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ description, due_date: dueDate }),
      });
      if (res.ok) {
        setTaskCreated(true);
        setShowModal(false);
      }
    } finally {
      setPending(false);
    }
  }

  if (status !== "new") return null;

  return (
    <>
      <article
        className="flex items-start gap-4 rounded-lg border border-[#14181F]/10 bg-white p-4 shadow-sm"
        style={{ borderLeft: `3px solid ${accent}` }}
      >
        <div className="min-w-0 flex-1">
          <div className="flex items-baseline justify-between gap-3">
            <p className="truncate font-medium">{alert.client_name ?? "Cliente"}</p>
            <span className="shrink-0 text-xs font-medium uppercase tracking-wide text-[#14181F]/40">
              {typeLabel}
            </span>
          </div>
          <p className="mt-1 text-sm leading-relaxed text-[#14181F]/70">{alert.explanation}</p>
        </div>
        <div className="flex shrink-0 flex-col gap-1.5 sm:flex-row">
          <button
            onClick={() => setShowModal(true)}
            disabled={pending || taskCreated}
            className="rounded-md border border-[#14181F]/15 px-3 py-1.5 text-xs font-medium text-[#14181F]/70 transition hover:bg-[#14181F]/5 disabled:opacity-40"
          >
            {taskCreated ? "Tarefa criada ✓" : "Criar tarefa"}
          </button>
          <button
            onClick={() => updateStatus("actioned")}
            disabled={pending}
            className="rounded-md bg-[#14181F] px-3 py-1.5 text-xs font-medium text-white transition hover:opacity-90 disabled:opacity-40"
          >
            Acionar
          </button>
          <button
            onClick={() => updateStatus("dismissed")}
            disabled={pending}
            className="rounded-md border border-[#14181F]/15 px-3 py-1.5 text-xs font-medium text-[#14181F]/70 transition hover:bg-[#14181F]/5 disabled:opacity-40"
          >
            Descartar
          </button>
        </div>
      </article>

      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#14181F]/40 px-4">
          <div className="w-full max-w-sm rounded-lg bg-white p-5 shadow-lg">
            <h3 className="font-display text-lg font-semibold">Nova tarefa</h3>
            <p className="mt-1 text-sm text-[#14181F]/50">
              {alert.client_name ?? "Cliente"} — {typeLabel}
            </p>

            <label className="mt-4 block text-xs font-medium uppercase tracking-wide text-[#14181F]/40">
              O que fazer
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
              className="mt-1 w-full rounded-md border border-[#14181F]/15 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#14181F]/20"
            />

            <label className="mt-3 block text-xs font-medium uppercase tracking-wide text-[#14181F]/40">
              Prazo
            </label>
            <input
              type="date"
              value={dueDate}
              onChange={(e) => setDueDate(e.target.value)}
              className="mt-1 w-full rounded-md border border-[#14181F]/15 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#14181F]/20"
            />

            <div className="mt-5 flex justify-end gap-2">
              <button
                onClick={() => setShowModal(false)}
                className="rounded-md border border-[#14181F]/15 px-3 py-1.5 text-xs font-medium text-[#14181F]/70 hover:bg-[#14181F]/5"
              >
                Cancelar
              </button>
              <button
                onClick={submitTask}
                disabled={pending || !description.trim()}
                className="rounded-md bg-[#14181F] px-3 py-1.5 text-xs font-medium text-white hover:opacity-90 disabled:opacity-40"
              >
                {pending ? "Salvando..." : "Criar tarefa"}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}