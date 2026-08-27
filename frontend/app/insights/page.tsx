import { auth } from "@clerk/nextjs/server";
import InsightCard from "../InsightCard";

type Insight = {
  id: string;
  client_id: string;
  client_name: string | null;
  insight_type: string;
  severity: "critical" | "opportunity" | "follow_up";
  title: string;
  explanation: string | null;
  status: string;
};

const SEVERITY_CONFIG = {
  critical: { label: "Crítico", accent: "#B23A48" },
  opportunity: { label: "Oportunidade", accent: "#A6790A" },
  follow_up: { label: "Follow-up", accent: "#3E5C76" },
} as const;

const SEVERITY_ORDER: (keyof typeof SEVERITY_CONFIG)[] = [
  "critical",
  "opportunity",
  "follow_up",
];

const INSIGHT_TYPE_LABELS: Record<string, string> = {
  concentration_by_issuer: "Concentração por emissor",
};

async function getInsights(): Promise<Insight[]> {
  const { getToken } = await auth();
  const token = await getToken();

  const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/insights/`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    cache: "no-store",
  });

  if (!res.ok) return [];
  const all: Insight[] = await res.json();
  return all.filter((i) => i.status === "new" || i.status === "viewed");
}

export default async function InsightsPage() {
  const insights = await getInsights();

  const grouped = SEVERITY_ORDER.map((severity) => ({
    severity,
    config: SEVERITY_CONFIG[severity],
    items: insights.filter((i) => i.severity === severity),
  }));

  const total = insights.length;

  return (
    <main className="mx-auto max-w-3xl px-6 py-10 sm:py-14">
      <header className="mb-10 flex items-end justify-between border-b border-[#14181F]/10 pb-6">
        <div>
          <p className="text-sm text-[#14181F]/50">Sinais recorrentes, sem duplicar alertas</p>
          <h1 className="font-display text-4xl font-semibold tracking-tight">Insights</h1>
        </div>
        <div className="text-right">
          <p className="font-mono text-2xl font-semibold tabular-nums">{total}</p>
          <p className="text-sm text-[#14181F]/50">
            {total === 1 ? "insight em aberto" : "insights em aberto"}
          </p>
        </div>
      </header>

      {total === 0 ? (
        <div className="rounded-lg border border-dashed border-[#14181F]/15 py-16 text-center">
          <p className="text-lg font-medium">Nenhum insight em aberto agora.</p>
          <p className="mt-1 text-sm text-[#14181F]/50">
            Diferente de alertas, insights não se recriam sozinhos a cada sync — eles
            atualizam a mesma linha até serem acionados ou descartados.
          </p>
        </div>
      ) : (
        <div className="space-y-10">
          {grouped
            .filter((g) => g.items.length > 0)
            .map((group) => (
              <section key={group.severity}>
                <div className="mb-3 flex items-center gap-2">
                  <span
                    className="h-2 w-2 rounded-full"
                    style={{ backgroundColor: group.config.accent }}
                  />
                  <h2 className="text-sm font-semibold uppercase tracking-wide text-[#14181F]/70">
                    {group.config.label}
                  </h2>
                  <span className="font-mono text-sm tabular-nums text-[#14181F]/40">
                    {group.items.length}
                  </span>
                </div>
                <div className="space-y-3">
                  {group.items.map((insight) => (
                    <InsightCard
                      key={insight.id}
                      insight={insight}
                      accent={group.config.accent}
                      typeLabel={INSIGHT_TYPE_LABELS[insight.insight_type] ?? insight.insight_type}
                    />
                  ))}
                </div>
              </section>
            ))}
        </div>
      )}
    </main>
  );
}
