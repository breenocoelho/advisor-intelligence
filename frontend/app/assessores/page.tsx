import { auth } from "@clerk/nextjs/server";
import AdvisorsTable from "./AdvisorsTable";

type Advisor = {
  id: string;
  name: string;
  aum: number;
  client_count: number;
  net_flow: number;
  aum_growth_pct: number | null;
};

function formatCurrency(value: number): string {
  return value.toLocaleString("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 });
}

async function getAdvisors(): Promise<Advisor[]> {
  const { getToken } = await auth();
  const token = await getToken();

  const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/advisors/`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    cache: "no-store",
  });

  if (!res.ok) return [];
  return res.json();
}

export default async function AssessoresPage() {
  const advisors = await getAdvisors();

  const totalAum = advisors.reduce((sum, a) => sum + a.aum, 0);
  const totalNetFlow = advisors.reduce((sum, a) => sum + a.net_flow, 0);
  const totalClients = advisors.reduce((sum, a) => sum + a.client_count, 0);
  const avgAumPerClient = totalClients > 0 ? totalAum / totalClients : 0;

  return (
    <main className="mx-auto max-w-4xl px-6 py-10 sm:py-14">
      <header className="mb-8 border-b border-[#14181F]/10 pb-6">
        <p className="text-sm text-[#14181F]/50">Advisor Dashboard</p>
        <h1 className="font-display text-4xl font-semibold tracking-tight">Assessores</h1>
      </header>

      <section className="mb-10 grid grid-cols-2 gap-4 sm:grid-cols-4">
        <div className="card p-4">
          <p className="text-xs uppercase tracking-wide text-[#14181F]/40">AUM</p>
          <p className="mt-1 font-mono text-xl font-semibold tabular-nums">{formatCurrency(totalAum)}</p>
        </div>
        <div className="card p-4">
          <p className="text-xs uppercase tracking-wide text-[#14181F]/40">Net Flow</p>
          <p
            className="mt-1 font-mono text-xl font-semibold tabular-nums"
            style={{ color: totalNetFlow >= 0 ? "#3F7D5B" : "#B23A48" }}
          >
            {totalNetFlow >= 0 ? "+" : "−"} {formatCurrency(Math.abs(totalNetFlow))}
          </p>
        </div>
        <div className="card p-4">
          <p className="text-xs uppercase tracking-wide text-[#14181F]/40">Clients</p>
          <p className="mt-1 font-mono text-xl font-semibold tabular-nums">{totalClients}</p>
        </div>
        <div className="card p-4">
          <p className="text-xs uppercase tracking-wide text-[#14181F]/40">Avg AUM / Client</p>
          <p className="mt-1 font-mono text-xl font-semibold tabular-nums">{formatCurrency(avgAumPerClient)}</p>
        </div>
      </section>

      {advisors.length === 0 ? (
        <div className="rounded-lg border border-dashed border-[#14181F]/15 py-16 text-center">
          <p className="text-lg font-medium">Nenhum assessor com histórico ainda.</p>
        </div>
      ) : (
        <AdvisorsTable advisors={advisors} />
      )}
    </main>
  );
}
