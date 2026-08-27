"use client";

import { useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { useRouter } from "next/navigation";

const TYPES = ["Meeting", "Phone", "Email", "WhatsApp", "Other"] as const;
const TYPE_LABELS: Record<string, string> = {
  Meeting: "Reunião",
  Phone: "Ligação",
  Email: "E-mail",
  WhatsApp: "WhatsApp",
  Other: "Outro",
};

export type InteractionForEdit = {
  id: string;
  interaction_type: string;
  interaction_date: string;
  subject: string | null;
  notes: string | null;
};

function todayIso(): string {
  return new Date().toISOString().split("T")[0];
}

export default function RegisterInteractionForm({
  clientId,
  interaction,
  onCancel,
  onSaved,
}: {
  clientId: string;
  interaction?: InteractionForEdit;
  onCancel?: () => void;
  onSaved?: () => void;
}) {
  const { getToken } = useAuth();
  const router = useRouter();
  const isEditing = !!interaction;

  const [open, setOpen] = useState(isEditing);
  const [type, setType] = useState<(typeof TYPES)[number]>((interaction?.interaction_type as (typeof TYPES)[number]) ?? "Meeting");
  const [interactionDate, setInteractionDate] = useState(interaction?.interaction_date ?? todayIso());
  const [subject, setSubject] = useState(interaction?.subject ?? "");
  const [notes, setNotes] = useState(interaction?.notes ?? "");
  const [pending, setPending] = useState(false);

  async function submit() {
    setPending(true);
    try {
      const token = await getToken();
      const url = isEditing
        ? `${process.env.NEXT_PUBLIC_API_URL}/clients/${clientId}/interactions/${interaction!.id}`
        : `${process.env.NEXT_PUBLIC_API_URL}/clients/${clientId}/interactions`;
      const res = await fetch(url, {
        method: isEditing ? "PUT" : "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          interaction_type: type,
          interaction_date: interactionDate,
          subject: subject || null,
          notes: notes || null,
        }),
      });
      if (res.ok) {
        setSubject("");
        setNotes("");
        setOpen(false);
        onSaved?.();
        router.refresh();
      }
    } finally {
      setPending(false);
    }
  }

  function cancel() {
    if (isEditing) {
      onCancel?.();
    } else {
      setOpen(false);
    }
  }

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="rounded-md bg-[#14181F] px-3 py-1.5 text-xs font-medium text-white transition hover:opacity-90"
      >
        Registrar interação
      </button>
    );
  }

  return (
    <div className="card p-4">
      <p className="mb-3 text-sm font-medium">{isEditing ? "Editar interação" : "Nova interação"}</p>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <div>
          <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-[#14181F]/40">Tipo</label>
          <select
            value={type}
            onChange={(e) => setType(e.target.value as (typeof TYPES)[number])}
            className="w-full rounded-md border border-[#14181F]/15 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#14181F]/20"
          >
            {TYPES.map((t) => (
              <option key={t} value={t}>
                {TYPE_LABELS[t]}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-[#14181F]/40">Data</label>
          <input
            type="date"
            value={interactionDate}
            onChange={(e) => setInteractionDate(e.target.value)}
            className="w-full rounded-md border border-[#14181F]/15 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#14181F]/20"
          />
        </div>
      </div>

      <label className="mb-1 mt-3 block text-xs font-medium uppercase tracking-wide text-[#14181F]/40">Assunto</label>
      <input
        type="text"
        value={subject}
        onChange={(e) => setSubject(e.target.value)}
        placeholder="Ex: Revisão de carteira"
        className="w-full rounded-md border border-[#14181F]/15 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#14181F]/20"
      />

      <label className="mb-1 mt-3 block text-xs font-medium uppercase tracking-wide text-[#14181F]/40">Notas</label>
      <textarea
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
        rows={3}
        className="w-full rounded-md border border-[#14181F]/15 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#14181F]/20"
      />

      <div className="mt-4 flex justify-end gap-2">
        <button
          onClick={cancel}
          className="rounded-md border border-[#14181F]/15 px-3 py-1.5 text-xs font-medium text-[#14181F]/70 hover:bg-[#14181F]/5"
        >
          Cancelar
        </button>
        <button
          onClick={submit}
          disabled={pending}
          className="rounded-md bg-[#14181F] px-3 py-1.5 text-xs font-medium text-white hover:opacity-90 disabled:opacity-40"
        >
          {pending ? "Salvando..." : isEditing ? "Salvar edição" : "Salvar interação"}
        </button>
      </div>
    </div>
  );
}
