import { auth } from "@clerk/nextjs/server";
import ClientesTable from "./ClientesTable";
import type { ScoreBreakdownItem } from "../ScoreTooltip";

type Client = {
  id: string;
  xp_client_id: string | null;
  name: string;
  aum: number | null;
  suitability: string | null;
  advisor_name: string | null;
  active_alerts_count: number;
  priority_score: number;
  health_score: number | null;
  health_score_breakdown: ScoreBreakdownItem[];
  relationship_score: number | null;
  relationship_score_band: string | null;
  relationship_score_breakdown: ScoreBreakdownItem[];
};

async function getClients(): Promise<Client[]> {
  const { getToken } = await auth();
  const token = await getToken();

  const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/clients/`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    cache: "no-store",
  });

  if (!res.ok) return [];
  return res.json();
}

export default async function ClientesPage() {
  const clients = await getClients();

  return (
    <main className="mx-auto max-w-6xl px-6 py-10 sm:py-14">
      <header className="mb-8 flex items-end justify-between border-b border-[#14181F]/10 pb-6">
        <div>
          <p className="text-sm text-[#14181F]/50">Carteira</p>
          <h1 className="font-display text-4xl font-semibold tracking-tight">Clientes</h1>
        </div>
        <div className="text-right">
          <p className="font-mono text-2xl font-semibold tabular-nums">{clients.length}</p>
          <p className="text-sm text-[#14181F]/50">
            {clients.length === 1 ? "cliente" : "clientes"}
          </p>
        </div>
      </header>

      <ClientesTable clients={clients} />
    </main>
  );
}