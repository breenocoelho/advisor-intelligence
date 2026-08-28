"use client";

import { useState } from "react";
import Link from "next/link";
import { useAuth } from "@clerk/nextjs";
import { useRouter } from "next/navigation";

export type OpportunityItem = {
  id: string;
  client_id: string;
  client_name: string | null;
  opportunity_type: string;
  status: string;
  potential_value: number | null;
  urgency: number | null;
  confidence: number | null;
  score: number | null;
  explanation: string | null;
  created_at: string | null;
};

const TYPE_LABELS: Record<string, string> = {
  idle_cash: "Caixa ociosa",
  upcoming_maturity: "Vencimento próximo",
};

const STATUS_OPTIONS = [
  "detected", "reviewed", "assigned", "contacted", "proposal", "executed", "won", "lost", "closed",
];

const STATUS_LABELS: Record<string, string> = {
  detected: "Detectada",
  reviewed: "Revisada",
  assigned: "Atribuída",
  contacted: "Contato feito",
  proposal: "Proposta enviada",
  executed: "Executada",
  won: "Ganha",
  lost: "Perdida",
  closed: "Fechada",
};

function formatCurrency(value: number | null): string {
  if (value === null) return "—";
  return value.toLocaleString("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 });
}

function scoreColor(score: number | null): string {
  if (score === null) return "#14181F66";
  if (score >= 70) return "#3F7D5B";
  if (score >= 40) return "#A6790A";
  return "#B23A48";
}

export default function OpportunitiesBoard({ opportunities }: { opportunities: OpportunityItem[] }) {
  const { getToken } = useAuth();
  const router = useRouter();
  const [pendingIds, setPendingIds] = useState<Set<string>>(new Set());

  async function changeStatus(id: string, status: string) {
    setPendingIds((prev) => new Set(prev).add(id));
    try {
      const token = await getToken();
      await fetch(`${process.env.NEXT_PUBLIC_API_URL}/opportunities/${id}`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ status }),
      });
      router.refresh();
    } finally {
      setPendingIds((prev) => {
        const next = new Set(prev);
        next.delete(id);
        return next;
      });
    }
  }

  if (opportunities.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-[#14181F]/15 py-16 text-center">
        <p className="text-lg font-medium">Nenhuma oportunidade em aberto.</p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {opportunities.map((opp) => (
        <div key={opp.id} className="flex items-start justify-between gap-4 card p-4">
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <Link href={`/clientes/${opp.client_id}`} className="font-medium hover:underline">
                {opp.client_name ?? "Cliente"}
              </Link>
              <span className="rounded-full bg-[#A6790A]/10 px-2 py-0.5 text-xs font-medium uppercase tracking-wide text-[#A6790A]">
                {TYPE_LABELS[opp.opportunity_type] ?? opp.opportunity_type}
              </span>
            </div>
            <p className="mt-1 text-sm text-[#14181F]/70">{opp.explanation}</p>
            <div className="mt-2 flex flex-wrap items-center gap-3 text-xs text-[#14181F]/50">
              <span>Valor potencial: <span className="font-mono tabular-nums">{formatCurrency(opp.potential_value)}</span></span>
              <span>Score: <span className="font-mono font-semibold tabular-nums" style={{ color: scoreColor(opp.score) }}>{opp.score ?? "—"}</span></span>
            </div>
          </div>
          <select
            value={opp.status}
            disabled={pendingIds.has(opp.id)}
            onChange={(e) => changeStatus(opp.id, e.target.value)}
            className="shrink-0 rounded-md border border-[#14181F]/15 px-2 py-1.5 text-xs font-medium text-[#14181F]/70 focus:outline-none focus:ring-2 focus:ring-[#14181F]/20 disabled:opacity-40"
          >
            {STATUS_OPTIONS.map((s) => (
              <option key={s} value={s}>{STATUS_LABELS[s]}</option>
            ))}
          </select>
        </div>
      ))}
    </div>
  );
}
