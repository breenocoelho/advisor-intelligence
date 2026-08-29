import { auth } from "@clerk/nextjs/server";
import Link from "next/link";
import AdvisorsTable from "../assessores/AdvisorsTable";
import SvgLineChart from "../SvgLineChart";

type AdvisorRow = {
  id: string;
  name: string;
  aum: number;
  client_count: number;
  net_flow: number;
  aum_growth_pct: number | null;
  opportunity_count: number;
};

type TrendPoint = { snapshot_date: string; aum: number | null; client_count: number | null; net_flow: number | null };
type PortfolioMixItem = { asset_class: string; value: number; pct: number };
type SegmentFlag = { segment_key: string; segment_label: string; count: number };
type AdvisorFlag = { advisor_id: string; advisor_name: string; aum_growth_pct: number | null };

type OfficeSummary = {
  aum_total: number;
  aum_growth_pct: number | null;
  aum_trend: TrendPoint[];
  net_flow_total: number;
  client_count: number;
  advisor_count: number;
  avg_aum_per_client: number;
  avg_aum_per_advisor: number;
  advisor_leaderboard: AdvisorRow[];
  portfolio_mix: PortfolioMixItem[];
  segment_flags: SegmentFlag[];
  advisors_declining: AdvisorFlag[];
};

const ASSET_CLASS_LABELS: Record<string, string> = {
  coe: "COE",
  funds: "Fundos de Investimento",
  fixedIncome: "Renda Fixa",
  checkingAccount: "Caixa / Disponível",
  pensionFunds: "Previdência",
  repo: "Compromissada",
  treasury: "Tesouro Direto",
  stock: "Ações",
  tradedFunds: "Fundos Imobiliários",
};

const SEGMENT_FLAG_COLORS: Record<string, string> = {
  declining: "#B23A48",
  at_risk: "#B23A48",
  dormant: "#7A5CB0",
};

function formatCurrency(value: number): string {
  return value.toLocaleString("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 });
}

function formatDateShort(value: string): string {
  return new Date(value).toLocaleDateString("pt-BR", { day: "2-digit", month: "short" });
}

async function getOfficeSummary(): Promise<OfficeSummary | null> {
  const { getToken } = await auth();
  const token = await getToken();

  const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/office/summary`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    cache: "no-store",
  });

  if (!res.ok) return null;
  return res.json();
}

export default async function EscritorioPage() {
  const office = await getOfficeSummary();

  return (
    <main className="mx-auto max-w-4xl px-6 py-10 sm:py-14">
      <header className="mb-8 border-b border-[#14181F]/10 pb-6">
        <p className="text-sm text-[#14181F]/50">Office Dashboard</p>
        <h1 className="font-display text-4xl font-semibold tracking-tight">Escritório</h1>
      </header>

      {!office ? (
        <div className="rounded-lg border border-dashed border-[#14181F]/15 py-16 text-center">
          <p className="text-lg font-medium">Nenhum dado disponível ainda.</p>
        </div>
      ) : (
        <>
          <section className="mb-10 grid grid-cols-2 gap-4 sm:grid-cols-4">
            <div className="card p-4">
              <p className="text-xs uppercase tracking-wide text-[#14181F]/40">AUM Total</p>
              <p className="mt-1 font-mono text-xl font-semibold tabular-nums">{formatCurrency(office.aum_total)}</p>
              {office.aum_growth_pct !== null && (
                <p className="mt-1 text-xs font-medium" style={{ color: office.aum_growth_pct >= 0 ? "#3F7D5B" : "#B23A48" }}>
                  {office.aum_growth_pct >= 0 ? "+" : ""}
                  {office.aum_growth_pct.toFixed(1)}%
                </p>
              )}
            </div>
            <div className="card p-4">
              <p className="text-xs uppercase tracking-wide text-[#14181F]/40">Net Flow</p>
              <p
                className="mt-1 font-mono text-xl font-semibold tabular-nums"
                style={{ color: office.net_flow_total >= 0 ? "#3F7D5B" : "#B23A48" }}
              >
                {office.net_flow_total >= 0 ? "+" : "−"} {formatCurrency(Math.abs(office.net_flow_total))}
              </p>
            </div>
            <div className="card p-4">
              <p className="text-xs uppercase tracking-wide text-[#14181F]/40">Clientes / Assessores</p>
              <p className="mt-1 font-mono text-xl font-semibold tabular-nums">
                {office.client_count} / {office.advisor_count}
              </p>
            </div>
            <div className="card p-4">
              <p className="text-xs uppercase tracking-wide text-[#14181F]/40">Avg AUM / Cliente</p>
              <p className="mt-1 font-mono text-xl font-semibold tabular-nums">{formatCurrency(office.avg_aum_per_client)}</p>
            </div>
          </section>

          {(office.segment_flags.length > 0 || office.advisors_declining.length > 0) && (
            <section className="mb-10">
              <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-[#14181F]/70">
                Flags de Gestão
              </h2>
              <div className="flex flex-wrap gap-3">
                {office.segment_flags.map((f) => (
                  <div key={f.segment_key} className="card px-4 py-3">
                    <p className="font-mono text-lg font-semibold tabular-nums" style={{ color: SEGMENT_FLAG_COLORS[f.segment_key] ?? "#14181F" }}>
                      {f.count}
                    </p>
                    <p className="text-xs text-[#14181F]/50">clientes {f.segment_label}</p>
                  </div>
                ))}
                {office.advisors_declining.length > 0 && (
                  <div className="card px-4 py-3">
                    <p className="font-mono text-lg font-semibold tabular-nums text-[#B23A48]">
                      {office.advisors_declining.length}
                    </p>
                    <p className="text-xs text-[#14181F]/50">
                      assessor(es) com AUM em queda: {office.advisors_declining.map((a) => a.advisor_name).join(", ")}
                    </p>
                  </div>
                )}
              </div>
            </section>
          )}

          {office.aum_trend.length > 0 && (
            <section className="mb-10">
              <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-[#14181F]/70">AUM Evolution</h2>
              <div className="card p-4">
                <SvgLineChart
                  points={office.aum_trend
                    .filter((p) => p.aum !== null)
                    .map((p) => ({ label: formatDateShort(p.snapshot_date), value: p.aum as number }))}
                  formatValue={formatCurrency}
                />
              </div>
            </section>
          )}

          {office.portfolio_mix.length > 0 && (
            <section className="mb-10">
              <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-[#14181F]/70">
                Portfolio Overview
              </h2>
              <div className="card divide-y divide-[#14181F]/5">
                {office.portfolio_mix.map((m) => (
                  <div key={m.asset_class} className="flex items-center justify-between p-3">
                    <span className="text-sm">{ASSET_CLASS_LABELS[m.asset_class] ?? m.asset_class}</span>
                    <span className="flex items-center gap-3">
                      <span className="font-mono text-sm tabular-nums text-[#14181F]/70">{formatCurrency(m.value)}</span>
                      <span className="font-mono text-sm font-semibold tabular-nums">{m.pct.toFixed(1)}%</span>
                    </span>
                  </div>
                ))}
              </div>
            </section>
          )}

          {office.advisor_leaderboard.length > 0 && (
            <section>
              <div className="mb-3 flex items-center justify-between">
                <h2 className="text-sm font-semibold uppercase tracking-wide text-[#14181F]/70">
                  Advisor Leaderboard
                </h2>
                <Link href="/assessores" className="text-xs font-medium text-[#14181F]/40 hover:text-[#14181F]/70">
                  Ver todos →
                </Link>
              </div>
              <AdvisorsTable advisors={office.advisor_leaderboard} />
            </section>
          )}
        </>
      )}
    </main>
  );
}
