import { auth } from "@clerk/nextjs/server";
import OpportunitiesBoard, { type OpportunityItem } from "./OpportunitiesBoard";

async function getOpportunities(): Promise<OpportunityItem[]> {
  const { getToken } = await auth();
  const token = await getToken();

  const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/opportunities/`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    cache: "no-store",
  });

  if (!res.ok) return [];
  return res.json();
}

export default async function OportunidadesPage() {
  const opportunities = await getOpportunities();
  const open = opportunities.filter((o) => !["won", "lost", "closed"].includes(o.status));

  return (
    <main className="mx-auto max-w-5xl px-6 py-10 sm:py-14">
      <header className="mb-8 flex items-end justify-between border-b border-[#14181F]/10 pb-6">
        <div>
          <p className="text-sm text-[#14181F]/50">Opportunity Engine</p>
          <h1 className="font-display text-4xl font-semibold tracking-tight">Oportunidades</h1>
        </div>
        <div className="text-right">
          <p className="font-mono text-2xl font-semibold tabular-nums">{open.length}</p>
          <p className="text-sm text-[#14181F]/50">{open.length === 1 ? "em aberto" : "em aberto"}</p>
        </div>
      </header>

      <OpportunitiesBoard opportunities={opportunities} />
    </main>
  );
}
