import { auth } from "@clerk/nextjs/server";
import AlertCard from "./AlertCard";

type Alert = {
  id: string;
  client_id: string;
  client_name: string | null;
  alert_type: string;
  severity: "critical" | "opportunity" | "follow_up";
  explanation: string | null;
  status: string;
  created_at: string | null;
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

const ALERT_TYPE_LABELS: Record<string, string> = {
  idle_cash: "Caixa ociosa",
  concentration: "Concentração",
  upcoming_maturity: "Vencimento próximo",
  relevant_movement: "Movimentação relevante",
};

async function getAlerts(): Promise<Alert[]> {
  const { getToken } = await auth();
  const token = await getToken();

  const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/alerts/?status=new`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    cache: "no-store",
  });

  if (!res.ok) return [];
  return res.json();
}

function formatToday(): string {
  return new Date().toLocaleDateString("pt-BR", {
    weekday: "long",
    day: "2-digit",
    month: "long",
  });
}

export default async function Today() {
  const alerts = await getAlerts();

  const grouped = SEVERITY_ORDER.map((severity) => ({
    severity,
    config: SEVERITY_CONFIG[severity],
    items: alerts.filter((a) => a.severity === severity),
  }));

  const totalOpen = alerts.length;

  return (
    <main className="mx-auto max-w-3xl px-6 py-10 sm:py-14">
      <header className="mb-10 flex items-end justify-between border-b border-[#14181F]/10 pb-6">
        <div>
          <p className="text-sm capitalize text-[#14181F]/50">{formatToday()}</p>
          <h1 className="font-display text-4xl font-semibold tracking-tight">Today</h1>
        </div>
        <div className="text-right">
          <p className="font-mono text-2xl font-semibold tabular-nums">{totalOpen}</p>
          <p className="text-sm text-[#14181F]/50">
            {totalOpen === 1 ? "alerta em aberto" : "alertas em aberto"}
          </p>
        </div>
      </header>

      {totalOpen === 0 ? (
        <div className="rounded-lg border border-dashed border-[#14181F]/15 py-16 text-center">
          <p className="text-lg font-medium">Nenhum alerta em aberto agora.</p>
          <p className="mt-1 text-sm text-[#14181F]/50">
            Assim que a próxima sincronização rodar, novidades aparecem aqui.
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
                  {group.items.map((alert) => (
                    <AlertCard
                      key={alert.id}
                      alert={alert}
                      accent={group.config.accent}
                      typeLabel={ALERT_TYPE_LABELS[alert.alert_type] ?? alert.alert_type}
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
