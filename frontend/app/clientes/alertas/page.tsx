import { auth } from "@clerk/nextjs/server";

type Alert = {
  id: string;
  client_name: string | null;
  alert_type: string;
  severity: "critical" | "opportunity" | "follow_up";
  explanation: string | null;
  status: string;
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

const STATUS_LABELS: Record<string, string> = {
  actioned: "Acionado",
  dismissed: "Descartado",
};

async function getResolvedAlerts(): Promise<Alert[]> {
  const { getToken } = await auth();
  const token = await getToken();

  const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/alerts/`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    cache: "no-store",
  });

  if (!res.ok) return [];
  const all: Alert[] = await res.json();
  return all.filter((a) => a.status === "actioned" || a.status === "dismissed");
}

export default async function HistoricoPage() {
  const alerts = await getResolvedAlerts();

  return (
    <main className="mx-auto max-w-3xl px-6 py-10 sm:py-14">
      <header className="mb-8 border-b border-[#14181F]/10 pb-6">
        <p className="text-sm text-[#14181F]/50">Trilha de auditoria</p>
        <h1 className="font-display text-4xl font-semibold tracking-tight">Histórico</h1>
      </header>

      {alerts.length === 0 ? (
        <div className="rounded-lg border border-dashed border-[#14181F]/15 py-16 text-center">
          <p className="text-lg font-medium">Nenhum alerta resolvido ainda.</p>
          <p className="mt-1 text-sm text-[#14181F]/50">
            Alertas acionados ou descartados no Today aparecem aqui.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {alerts.map((alert) => {
            const config = SEVERITY_CONFIG[alert.severity];
            return (
              <article
                key={alert.id}
                className="flex items-start justify-between gap-4 rounded-lg border border-[#14181F]/10 bg-white p-4 opacity-80"
                style={{ borderLeft: `3px solid ${config.accent}` }}
              >
                <div className="min-w-0 flex-1">
                  <div className="flex items-baseline justify-between gap-3">
                    <p className="truncate font-medium">{alert.client_name ?? "Cliente"}</p>
                    <span className="shrink-0 text-xs font-medium uppercase tracking-wide text-[#14181F]/40">
                      {ALERT_TYPE_LABELS[alert.alert_type] ?? alert.alert_type}
                    </span>
                  </div>
                  <p className="mt-1 text-sm leading-relaxed text-[#14181F]/70">{alert.explanation}</p>
                </div>
                <span className="shrink-0 rounded-full bg-[#14181F]/5 px-2 py-0.5 text-xs font-medium text-[#14181F]/50">
                  {STATUS_LABELS[alert.status] ?? alert.status}
                </span>
              </article>
            );
          })}
        </div>
      )}
    </main>
  );
}