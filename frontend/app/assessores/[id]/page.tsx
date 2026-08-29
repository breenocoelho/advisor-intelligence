import { auth } from "@clerk/nextjs/server";
import Link from "next/link";
import { notFound } from "next/navigation";
import SvgLineChart from "../../SvgLineChart";
import AdvisorBenchmarkChart from "./AdvisorBenchmarkChart";
import ProductMixTable from "./ProductMixTable";
import WhatChangedCard from "../../WhatChangedCard";

type TrendPoint = { snapshot_date: string; aum: number | null; client_count: number | null; net_flow: number | null };
type ProductMixAssetItem = { asset_id: string; asset_name: string; value: number; pct_of_class: number };
type ProductMixItem = { asset_class: string; value: number; pct: number; assets: ProductMixAssetItem[] };
type OpportunityDistributionItem = { opportunity_type: string; count: number };
type AdvisorKeyInsight = { text: string; severity: "critical" | "opportunity" | "follow_up"; client_id: string; client_name: string };

type AdvisorDetail = {
  id: string;
  name: string;
  aum: number;
  client_count: number;
  net_flow: number;
  avg_aum_per_client: number;
  trend: TrendPoint[];
  product_mix: ProductMixItem[];
  contact_coverage_pct: number | null;
  relationship_coverage_pct: number | null;
  retention_pct: number | null;
  opportunity_distribution: OpportunityDistributionItem[];
  key_insights: AdvisorKeyInsight[];
};

const OPPORTUNITY_TYPE_LABELS: Record<string, string> = {
  idle_cash: "Caixa ociosa",
  upcoming_maturity: "Vencimento próximo",
};

const KEY_INSIGHT_SEVERITY_CONFIG = {
  critical: { accent: "#B23A48" },
  opportunity: { accent: "#A6790A" },
  follow_up: { accent: "#3E5C76" },
} as const;

function formatCurrency(value: number): string {
  return value.toLocaleString("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 });
}

function formatDateShort(value: string): string {
  return new Date(value).toLocaleDateString("pt-BR", { day: "2-digit", month: "short" });
}

async function getAdvisor(id: string): Promise<AdvisorDetail | null> {
  const { getToken } = await auth();
  const token = await getToken();

  const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/advisors/${id}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    cache: "no-store",
  });

  if (res.status === 404) return null;
  if (!res.ok) throw new Error("Falha ao carregar assessor");
  return res.json();
}

export default async function AdvisorDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const advisor = await getAdvisor(id);

  if (!advisor) notFound();

  return (
    <main className="mx-auto max-w-4xl px-6 py-10 sm:py-14">
      <Link href="/assessores" className="text-sm text-[#14181F]/50 hover:underline">
        ← Assessores
      </Link>

      <header className="mt-4 mb-8 border-b border-[#14181F]/10 pb-6">
        <h1 className="font-display text-4xl font-semibold tracking-tight">{advisor.name}</h1>
      </header>

      {advisor.key_insights.length > 0 && (
        <section className="mb-10">
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-[#14181F]/70">Key Insights</h2>
          <div className="card divide-y divide-[#14181F]/5">
            {advisor.key_insights.map((item, i) => {
              const config = KEY_INSIGHT_SEVERITY_CONFIG[item.severity];
              return (
                <Link
                  key={i}
                  href={`/clientes/${item.client_id}`}
                  className="flex items-start gap-3 p-3 transition hover:bg-[#14181F]/[0.02]"
                >
                  <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full" style={{ backgroundColor: config.accent }} />
                  <span className="text-sm">
                    <span className="font-medium">{item.client_name}</span>
                    <span className="text-[#14181F]/70"> — {item.text}</span>
                  </span>
                </Link>
              );
            })}
          </div>
        </section>
      )}

      <section className="mb-10 grid grid-cols-2 gap-4 sm:grid-cols-4">
        <div className="card p-4">
          <p className="text-xs uppercase tracking-wide text-[#14181F]/40">AUM</p>
          <p className="mt-1 font-mono text-xl font-semibold tabular-nums">{formatCurrency(advisor.aum)}</p>
        </div>
        <div className="card p-4">
          <p className="text-xs uppercase tracking-wide text-[#14181F]/40">Net Flow</p>
          <p
            className="mt-1 font-mono text-xl font-semibold tabular-nums"
            style={{ color: advisor.net_flow >= 0 ? "#3F7D5B" : "#B23A48" }}
          >
            {advisor.net_flow >= 0 ? "+" : "−"} {formatCurrency(Math.abs(advisor.net_flow))}
          </p>
        </div>
        <div className="card p-4">
          <p className="text-xs uppercase tracking-wide text-[#14181F]/40">Clients</p>
          <p className="mt-1 font-mono text-xl font-semibold tabular-nums">{advisor.client_count}</p>
        </div>
        <div className="card p-4">
          <p className="text-xs uppercase tracking-wide text-[#14181F]/40">Avg AUM / Client</p>
          <p className="mt-1 font-mono text-xl font-semibold tabular-nums">
            {formatCurrency(advisor.avg_aum_per_client)}
          </p>
        </div>
      </section>

      <section className="mb-10 grid grid-cols-2 gap-4 sm:grid-cols-3">
        <div className="card p-4">
          <p className="text-xs uppercase tracking-wide text-[#14181F]/40">Contact Coverage</p>
          <p className="mt-1 font-mono text-xl font-semibold tabular-nums">
            {advisor.contact_coverage_pct !== null ? `${advisor.contact_coverage_pct.toFixed(0)}%` : "—"}
          </p>
        </div>
        <div className="card p-4">
          <p className="text-xs uppercase tracking-wide text-[#14181F]/40">Relationship Coverage</p>
          <p className="mt-1 font-mono text-xl font-semibold tabular-nums">
            {advisor.relationship_coverage_pct !== null ? `${advisor.relationship_coverage_pct.toFixed(0)}%` : "—"}
          </p>
        </div>
        <div className="card p-4">
          <p className="text-xs uppercase tracking-wide text-[#14181F]/40">Retention</p>
          <p className="mt-1 font-mono text-xl font-semibold tabular-nums">
            {advisor.retention_pct !== null ? `${advisor.retention_pct.toFixed(0)}%` : "—"}
          </p>
        </div>
      </section>

      {advisor.opportunity_distribution.length > 0 && (
        <section className="mb-10">
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-[#14181F]/70">
            Distribuição de Oportunidades
          </h2>
          <div className="card divide-y divide-[#14181F]/5">
            {advisor.opportunity_distribution.map((item) => (
              <div key={item.opportunity_type} className="flex items-center justify-between p-3">
                <span className="text-sm">{OPPORTUNITY_TYPE_LABELS[item.opportunity_type] ?? item.opportunity_type}</span>
                <span className="font-mono text-sm font-semibold tabular-nums">{item.count}</span>
              </div>
            ))}
          </div>
        </section>
      )}

      <WhatChangedCard whatChangedUrl={`/advisors/${advisor.id}/what-changed`} />

      {advisor.trend.length > 0 && (
        <>
          <section className="mb-10">
            <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-[#14181F]/70">AUM Evolution</h2>
            <div className="card p-4">
              <SvgLineChart
                points={advisor.trend
                  .filter((p) => p.aum !== null)
                  .map((p) => ({ label: formatDateShort(p.snapshot_date), value: p.aum as number }))}
                formatValue={formatCurrency}
              />
            </div>
          </section>

          <AdvisorBenchmarkChart trend={advisor.trend} />

          <section className="mb-10">
            <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-[#14181F]/70">Client Growth</h2>
            <div className="card p-4">
              <SvgLineChart
                points={advisor.trend
                  .filter((p) => p.client_count !== null)
                  .map((p) => ({ label: formatDateShort(p.snapshot_date), value: p.client_count as number }))}
                color="#3E5C76"
                formatValue={(v) => `${Math.round(v)}`}
              />
            </div>
          </section>
        </>
      )}

      {advisor.product_mix.length > 0 && (
        <section>
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-[#14181F]/70">Product Mix</h2>
          <ProductMixTable items={advisor.product_mix} />
        </section>
      )}
    </main>
  );
}
