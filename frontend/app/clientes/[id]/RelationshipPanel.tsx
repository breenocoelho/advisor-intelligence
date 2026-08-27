"use client";

import { useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { useRouter } from "next/navigation";
import RegisterInteractionForm from "./RegisterInteractionForm";
import type { ClientDetail } from "./ClientTabs";

const INTERACTION_TYPE_LABELS: Record<string, string> = {
  Meeting: "Reunião",
  Phone: "Ligação",
  Email: "E-mail",
  WhatsApp: "WhatsApp",
  Other: "Contato",
};

const COMPONENT_LABELS: Record<string, string> = {
  recency: "Recency",
  frequency: "Frequency",
  engagement: "Engagement",
  aum_stability: "AUM stability",
  open_tasks: "Open Tasks",
};

function scoreColor(score: number): string {
  if (score >= 80) return "#3F7D5B";
  if (score >= 60) return "#A6790A";
  return "#B23A48";
}

function formatDate(value: string): string {
  return new Date(value).toLocaleDateString("pt-BR", { day: "2-digit", month: "short", year: "numeric" });
}

export default function RelationshipPanel({ client }: { client: ClientDetail }) {
  const { getToken } = useAuth();
  const router = useRouter();
  const [editingId, setEditingId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const timeline = [...client.interactions].sort(
    (a, b) => new Date(b.interaction_date).getTime() - new Date(a.interaction_date).getTime()
  );

  async function deleteInteraction(id: string) {
    if (!confirm("Apagar esta interação? Essa ação não pode ser desfeita.")) return;
    setDeletingId(id);
    try {
      const token = await getToken();
      await fetch(`${process.env.NEXT_PUBLIC_API_URL}/clients/${client.id}/interactions/${id}`, {
        method: "DELETE",
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      router.refresh();
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <div className="space-y-10">
      {client.relationship_score !== null && (
        <section>
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-[#14181F]/70">
            Relationship Score
          </h2>
          <div className="card p-5">
            <div className="flex items-center gap-4">
              <div className="text-center">
                <p className="font-mono text-4xl font-bold tabular-nums" style={{ color: scoreColor(client.relationship_score) }}>
                  {client.relationship_score}
                </p>
                <p className="text-xs font-medium uppercase tracking-wide text-[#14181F]/50">
                  {client.relationship_score_band}
                </p>
              </div>
              <div className="flex-1 border-l border-[#14181F]/10 pl-4">
                <ul className="space-y-1 text-sm text-[#14181F]/70">
                  {client.relationship_score_explanation.map((line, i) => (
                    <li key={i}>• {line}</li>
                  ))}
                </ul>
              </div>
            </div>
            {client.relationship_score_components && (
              <div className="mt-4 grid grid-cols-2 gap-3 border-t border-[#14181F]/10 pt-4 sm:grid-cols-5">
                {Object.entries(client.relationship_score_components).map(([key, value]) => (
                  <div key={key}>
                    <p className="text-xs uppercase tracking-wide text-[#14181F]/40">
                      {COMPONENT_LABELS[key] ?? key}
                    </p>
                    <p className="mt-1 font-mono text-sm font-semibold tabular-nums" style={{ color: scoreColor(value) }}>
                      {value}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </section>
      )}

      <section>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-[#14181F]/70">
            Timeline de contatos ({timeline.length})
          </h2>
          <RegisterInteractionForm clientId={client.id} />
        </div>
        {timeline.length === 0 ? (
          <p className="text-sm text-[#14181F]/50">Nenhuma interação registrada ainda.</p>
        ) : (
          <ol className="space-y-3 border-l border-[#14181F]/10 pl-4">
            {timeline.map((interaction) => (
              <li key={interaction.id} className="relative">
                <span className="absolute -left-[21px] top-1.5 h-2 w-2 rounded-full bg-[#14181F]/30" />
                {editingId === interaction.id ? (
                  <RegisterInteractionForm
                    clientId={client.id}
                    interaction={interaction}
                    onCancel={() => setEditingId(null)}
                    onSaved={() => setEditingId(null)}
                  />
                ) : (
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="text-xs font-mono tabular-nums text-[#14181F]/40">
                        {formatDate(interaction.interaction_date)}
                      </p>
                      <p className="text-sm font-medium">
                        {INTERACTION_TYPE_LABELS[interaction.interaction_type] ?? interaction.interaction_type}
                        {interaction.subject && <span className="font-normal"> — {interaction.subject}</span>}
                      </p>
                      {interaction.notes && <p className="text-sm text-[#14181F]/70">{interaction.notes}</p>}
                    </div>
                    <div className="flex shrink-0 items-center gap-2">
                      <button
                        onClick={() => setEditingId(interaction.id)}
                        className="text-xs font-medium text-[#14181F]/40 hover:text-[#14181F]/70"
                      >
                        Editar
                      </button>
                      <button
                        onClick={() => deleteInteraction(interaction.id)}
                        disabled={deletingId === interaction.id}
                        className="text-xs font-medium text-[#B23A48]/70 hover:text-[#B23A48] disabled:opacity-40"
                      >
                        {deletingId === interaction.id ? "Apagando..." : "Apagar"}
                      </button>
                    </div>
                  </div>
                )}
              </li>
            ))}
          </ol>
        )}
      </section>
    </div>
  );
}
