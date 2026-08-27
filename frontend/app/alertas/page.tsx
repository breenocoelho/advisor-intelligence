import { auth } from "@clerk/nextjs/server";
import Link from "next/link";

type AlertRow = {
  id: string;
  client_id: string;
  client_name: string | null;
  alert_type: string;
  severity: "critical" | "opportunity" | "follow_up";
  explanation: string | null;
  status: string;
  resolution_note: string | null;
  created_at: string | null;
};

type InsightRow = {
  id: string;
  client_id: string;
  client_name: string | null;
  insight_type: string;
  severity: "critical" | "opportunity" | "follow_up";
  title: string;
  explanation: string | null;
  status: string;
  resolution_note: string | null;
  updated_at: string | null;
};

type HistoryItem = {
  kind: "alert" | "insight";
  id: string;
  clientId: string;
  clientName: string;
  severity: "critical" | "opportunity" | "follow_up";
  typeLabel: string;
  title: string | null;
  explanation: string | null;
  status: string;
  resolutionNote: string | null;
  resolvedAt: string | null;
};

const SEVERITY_CONFIG = {
  critical: { accent: "#B23A48" },
  opportunity: { accent: "#A6790A" },
  follow_up: { accent: "#3E5C76" },
} as const;

const ALERT_TYPE_LABELS: Record<string, string> = {
  idle_cash: "Caixa ociosa",
  concentration: "Concentração",
  upcoming_maturity: "Vencimento próximo",
  relevant_movement: "Movimentação relevante",
  no_recent_contact: "Sem contato recente",
};

const INSIGHT_TYPE_LABELS: Record<string, string> = {
  concentration_by_issuer: "Concentração por emissor",
};

const STATUS_LABELS: Record<string, string> = {
  actioned: "Acionado",
  dismissed: "Descartado",
};

async function getHistory(): Promise<HistoryItem[]> {
  const { getToken } = await auth();
  const token = await getToken();
  const headers: HeadersInit = token ? { Authorization: `Bearer ${token}` } : {};

  const [alertsRes, insightsRes] = await Promise.all([
    fetch(`${process.env.NEXT_PUBLIC_API_URL}/alerts/`, { headers, cache: "no-store" }),
    fetch(`${process.env.NEXT_PUBLIC_API_URL}/insights/`, { headers, cache: "no-store" }),
  ]);

  const alerts: AlertRow[] = alertsRes.ok ? await alertsRes.json() : [];
  const insights: InsightRow[] = insightsRes.ok ? await insightsRes.json() : [];

  const resolvedAlerts: HistoryItem[] = alerts
    .filter((a) => a.status === "actioned" || a.status === "dismissed")
    .map((a) => ({
      kind: "alert",
      id: a.id,
      clientId: a.client_id,
      clientName: a.client_name ?? "Cliente",
      severity: a.severity,
      typeLabel: ALERT_TYPE_LABELS[a.alert_type] ?? a.alert_type,
      title: null,
      explanation: a.explanation,
      status: a.status,
      resolutionNote: a.resolution_note,
      resolvedAt: a.created_at,
    }));

  const resolvedInsights: HistoryItem[] = insights
    .filter((i) => i.status === "actioned" || i.status === "dismissed")
    .map((i) => ({
      kind: "insight",
      id: i.id,
      clientId: i.client_id,
      clientName: i.client_name ?? "Cliente",
      severity: i.severity,
      typeLabel: INSIGHT_TYPE_LABELS[i.insight_type] ?? i.insight_type,
      title: i.title,
      explanation: i.explanation,
      status: i.status,
      resolutionNote: i.resolution_note,
      resolvedAt: i.updated_at,
    }));

  return [...resolvedAlerts, ...resolvedInsights].sort((a, b) => {
    const dateA = a.resolvedAt ? new Date(a.resolvedAt).getTime() : 0;
    const dateB = b.resolvedAt ? new Date(b.resolvedAt).getTime() : 0;
    return dateB - dateA;
  });
}

export default async function HistoricoPage() {
  const items = await getHistory();

  return (
    <main className="mx-auto max-w-3xl px-6 py-10 sm:py-14">
      <header className="mb-8 border-b border-[#14181F]/10 pb-6">
        <p className="text-sm text-[#14181F]/50">Trilha de auditoria — alertas e insights</p>
        <h1 className="font-display text-4xl font-semibold tracking-tight">Histórico</h1>
      </header>

      {items.length === 0 ? (
        <div className="rounded-lg border border-dashed border-[#14181F]/15 py-16 text-center">
          <p className="text-lg font-medium">Nada resolvido ainda.</p>
          <p className="mt-1 text-sm text-[#14181F]/50">
            Itens acionados ou descartados no Today aparecem aqui.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {items.map((item) => {
            const config = SEVERITY_CONFIG[item.severity];
            return (
              <article
                key={`${item.kind}:${item.id}`}
                className="flex items-start justify-between gap-4 card p-4 opacity-80"
              >
                <div className="min-w-0 flex-1">
                  <div className="flex items-baseline justify-between gap-3">
                    <Link
                      href={`/clientes/${item.clientId}`}
                      className="truncate font-medium hover:underline"
                    >
                      {item.clientName}
                    </Link>
                    <span
                      className="shrink-0 rounded-full px-2 py-0.5 text-xs font-medium uppercase tracking-wide"
                      style={{ backgroundColor: `${config.accent}1a`, color: config.accent }}
                    >
                      {item.typeLabel}
                    </span>
                  </div>
                  {item.title && <p className="mt-1 text-sm font-medium">{item.title}</p>}
                  <p className="mt-1 text-sm leading-relaxed text-[#14181F]/70">{item.explanation}</p>
                  {item.resolutionNote && (
                    <p className="mt-2 rounded-md bg-[#14181F]/5 px-3 py-2 text-sm text-[#14181F]/70">
                      <span className="font-medium">Nota: </span>
                      {item.resolutionNote}
                    </p>
                  )}
                </div>
                <span className="shrink-0 rounded-full bg-[#14181F]/5 px-2 py-0.5 text-xs font-medium text-[#14181F]/50">
                  {STATUS_LABELS[item.status] ?? item.status}
                </span>
              </article>
            );
          })}
        </div>
      )}
    </main>
  );
}
