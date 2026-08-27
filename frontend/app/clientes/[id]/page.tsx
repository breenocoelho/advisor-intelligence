import { auth } from "@clerk/nextjs/server";
import Link from "next/link";
import { notFound } from "next/navigation";
import ContactButton from "./ContactButton";
import ClientTabs, { type ClientDetail } from "./ClientTabs";
import ScoreTooltip from "../../ScoreTooltip";

async function getClient(id: string): Promise<ClientDetail | null> {
  const { getToken } = await auth();
  const token = await getToken();

  const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/clients/${id}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    cache: "no-store",
  });

  if (res.status === 404) return null;
  if (!res.ok) throw new Error("Falha ao carregar cliente");
  return res.json();
}

async function getPositionDates(id: string): Promise<string[]> {
  const { getToken } = await auth();
  const token = await getToken();

  const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/clients/${id}/position-dates`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    cache: "no-store",
  });

  if (!res.ok) return [];
  return res.json();
}

function formatCurrency(value: number | null): string {
  if (value === null) return "—";
  return value.toLocaleString("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 });
}

function formatSuitability(value: string | null): string {
  if (!value) return "—";
  return value.charAt(0) + value.slice(1).toLowerCase();
}

function formatLastContact(value: string | null): string {
  if (!value) return "nunca registrado";
  const days = Math.floor((Date.now() - new Date(value).getTime()) / (1000 * 60 * 60 * 24));
  if (days === 0) return "hoje";
  if (days === 1) return "há 1 dia";
  return `há ${days} dias`;
}

export default async function Client360Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const client = await getClient(id);

  if (!client) notFound();

  const positionDates = await getPositionDates(id);

  return (
    <main className="mx-auto max-w-5xl px-6 py-10 sm:py-14">
      <Link href="/clientes" className="text-sm text-[#14181F]/50 hover:underline">
        ← Clientes
      </Link>

      <header className="mt-4 mb-8 flex flex-wrap items-end justify-between gap-4 border-b border-[#14181F]/10 pb-6">
        <div>
          <p className="text-sm text-[#14181F]/50">#{client.xp_client_id}</p>
          <h1 className="font-display text-4xl font-semibold tracking-tight">{client.name}</h1>
          <p className="mt-1 text-sm text-[#14181F]/60">
            {client.advisor_name ?? "Sem assessor vinculado"} · {formatSuitability(client.suitability)}
          </p>
          <div className="mt-3 flex items-center gap-3">
            <span className="text-sm text-[#14181F]/50">
              Último contato: {formatLastContact(client.last_contact_at)}
            </span>
            <ContactButton clientId={client.id} />
          </div>
        </div>
        <div className="flex flex-wrap items-end gap-6">
          <div className="text-right">
            <p className="font-mono text-2xl font-semibold tabular-nums">{formatCurrency(client.aum)}</p>
            <p className="text-sm text-[#14181F]/50">patrimônio (AUM)</p>
          </div>
          <div className="flex gap-2">
            {client.health_score !== null && (
              <ScoreTooltip score={client.health_score} breakdown={client.health_score_breakdown} label="health" />
            )}
            {client.relationship_score !== null && (
              <ScoreTooltip
                score={client.relationship_score}
                band={client.relationship_score_band}
                breakdown={client.relationship_score_breakdown}
                label="relationship"
              />
            )}
          </div>
        </div>
      </header>

      <ClientTabs client={client} positionDates={positionDates} />
    </main>
  );
}
