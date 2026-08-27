"use client";

import { useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { useRouter } from "next/navigation";

type Option = { id: string; value: string };
type FieldDefinition = { id: string; key: string; label: string; options: Option[] };
type Client = { id: string; name: string };

function slugify(label: string): string {
  return label
    .toLowerCase()
    .normalize("NFD")
    .replace(new RegExp("[\\u0300-\\u036f]", "g"), "")
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "");
}

export default function ExtendedFieldsAdmin({ fields, clients }: { fields: FieldDefinition[]; clients: Client[] }) {
  const { getToken } = useAuth();
  const router = useRouter();

  const [newLabel, setNewLabel] = useState("");
  const [pendingAction, setPendingAction] = useState<string | null>(null);
  const [optionDrafts, setOptionDrafts] = useState<Record<string, string>>({});

  const [assignFieldId, setAssignFieldId] = useState(fields[0]?.id ?? "");
  const [assignOptionId, setAssignOptionId] = useState(fields[0]?.options[0]?.id ?? "");
  const [assignClientId, setAssignClientId] = useState(clients[0]?.id ?? "");

  async function authHeaders(): Promise<HeadersInit> {
    const token = await getToken();
    return { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}) };
  }

  async function createField() {
    if (!newLabel.trim()) return;
    setPendingAction("create-field");
    try {
      const headers = await authHeaders();
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/config/extended-fields`, {
        method: "POST",
        headers,
        body: JSON.stringify({ key: slugify(newLabel), label: newLabel.trim() }),
      });
      if (res.ok) {
        setNewLabel("");
        router.refresh();
      }
    } finally {
      setPendingAction(null);
    }
  }

  async function deleteField(id: string) {
    if (!confirm("Remover este campo customizado? Todas as opções e classificações associadas serão apagadas.")) return;
    setPendingAction(`delete-field-${id}`);
    try {
      const headers = await authHeaders();
      await fetch(`${process.env.NEXT_PUBLIC_API_URL}/config/extended-fields/${id}`, { method: "DELETE", headers });
      router.refresh();
    } finally {
      setPendingAction(null);
    }
  }

  async function createOption(fieldId: string) {
    const value = (optionDrafts[fieldId] ?? "").trim();
    if (!value) return;
    setPendingAction(`create-option-${fieldId}`);
    try {
      const headers = await authHeaders();
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/config/extended-fields/${fieldId}/options`, {
        method: "POST",
        headers,
        body: JSON.stringify({ value }),
      });
      if (res.ok) {
        setOptionDrafts((prev) => ({ ...prev, [fieldId]: "" }));
        router.refresh();
      }
    } finally {
      setPendingAction(null);
    }
  }

  async function deleteOption(optionId: string) {
    setPendingAction(`delete-option-${optionId}`);
    try {
      const headers = await authHeaders();
      await fetch(`${process.env.NEXT_PUBLIC_API_URL}/config/extended-fields/options/${optionId}`, {
        method: "DELETE",
        headers,
      });
      router.refresh();
    } finally {
      setPendingAction(null);
    }
  }

  async function assign() {
    if (!assignOptionId || !assignClientId) return;
    setPendingAction("assign");
    try {
      const headers = await authHeaders();
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/config/extended-fields/assignments`, {
        method: "POST",
        headers,
        body: JSON.stringify({ client_id: assignClientId, option_id: assignOptionId }),
      });
      if (res.ok) router.refresh();
    } finally {
      setPendingAction(null);
    }
  }

  const assignField = fields.find((f) => f.id === assignFieldId);

  return (
    <div className="space-y-6">
      <div className="space-y-3">
        {fields.length === 0 ? (
          <p className="text-sm text-[#14181F]/50">Nenhum campo customizado criado ainda.</p>
        ) : (
          fields.map((field) => (
            <div key={field.id} className="card p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium">{field.label}</p>
                  <p className="font-mono text-xs text-[#14181F]/40">{field.key}</p>
                </div>
                <button
                  onClick={() => deleteField(field.id)}
                  disabled={pendingAction === `delete-field-${field.id}`}
                  className="text-xs font-medium text-[#B23A48]/70 hover:text-[#B23A48] disabled:opacity-40"
                >
                  Remover campo
                </button>
              </div>

              {field.options.length > 0 && (
                <div className="mt-3 flex flex-wrap gap-1.5">
                  {field.options.map((opt) => (
                    <span
                      key={opt.id}
                      className="inline-flex items-center gap-1.5 rounded-full bg-[#14181F]/5 px-2.5 py-1 text-xs"
                    >
                      {opt.value}
                      <button
                        onClick={() => deleteOption(opt.id)}
                        disabled={pendingAction === `delete-option-${opt.id}`}
                        className="text-[#14181F]/30 hover:text-[#B23A48]"
                        aria-label={`Remover opção ${opt.value}`}
                      >
                        ×
                      </button>
                    </span>
                  ))}
                </div>
              )}

              <div className="mt-3 flex gap-2">
                <input
                  type="text"
                  placeholder={`Nova opção para "${field.label}"`}
                  value={optionDrafts[field.id] ?? ""}
                  onChange={(e) => setOptionDrafts((prev) => ({ ...prev, [field.id]: e.target.value }))}
                  className="flex-1 rounded-md border border-[#14181F]/15 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#14181F]/20"
                />
                <button
                  onClick={() => createOption(field.id)}
                  disabled={pendingAction === `create-option-${field.id}` || !(optionDrafts[field.id] ?? "").trim()}
                  className="rounded-md border border-[#14181F]/15 px-3 py-1.5 text-xs font-medium text-[#14181F]/70 transition hover:bg-[#14181F]/5 disabled:opacity-40"
                >
                  Adicionar opção
                </button>
              </div>
            </div>
          ))
        )}
      </div>

      <div className="rounded-lg border border-dashed border-[#14181F]/20 bg-white p-4">
        <p className="text-sm font-medium">Novo campo customizado</p>
        <p className="mt-1 text-xs text-[#14181F]/50">
          Ex: crie o campo &quot;Família&quot; para agrupar clientes que são parentes entre si.
        </p>
        <div className="mt-3 flex gap-2">
          <input
            type="text"
            placeholder="Nome do campo (ex: Família)"
            value={newLabel}
            onChange={(e) => setNewLabel(e.target.value)}
            className="flex-1 rounded-md border border-[#14181F]/15 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#14181F]/20"
          />
          <button
            onClick={createField}
            disabled={pendingAction === "create-field" || !newLabel.trim()}
            className="rounded-md bg-[#14181F] px-3 py-2 text-sm font-medium text-white transition hover:opacity-90 disabled:opacity-40"
          >
            Criar campo
          </button>
        </div>
      </div>

      {fields.some((f) => f.options.length > 0) && clients.length > 0 && (
        <div className="rounded-lg border border-dashed border-[#14181F]/20 bg-white p-4">
          <p className="text-sm font-medium">Classificar cliente</p>
          <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-4">
            <select
              value={assignFieldId}
              onChange={(e) => {
                setAssignFieldId(e.target.value);
                const f = fields.find((x) => x.id === e.target.value);
                setAssignOptionId(f?.options[0]?.id ?? "");
              }}
              className="rounded-md border border-[#14181F]/15 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#14181F]/20"
            >
              {fields.map((f) => (
                <option key={f.id} value={f.id}>
                  {f.label}
                </option>
              ))}
            </select>
            <select
              value={assignOptionId}
              onChange={(e) => setAssignOptionId(e.target.value)}
              className="rounded-md border border-[#14181F]/15 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#14181F]/20"
            >
              {(assignField?.options ?? []).map((opt) => (
                <option key={opt.id} value={opt.id}>
                  {opt.value}
                </option>
              ))}
            </select>
            <select
              value={assignClientId}
              onChange={(e) => setAssignClientId(e.target.value)}
              className="rounded-md border border-[#14181F]/15 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#14181F]/20"
            >
              {clients.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
            <button
              onClick={assign}
              disabled={pendingAction === "assign" || !assignOptionId}
              className="rounded-md bg-[#14181F] px-3 py-2 text-sm font-medium text-white transition hover:opacity-90 disabled:opacity-40"
            >
              Classificar
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
