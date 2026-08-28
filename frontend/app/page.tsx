import { auth } from "@clerk/nextjs/server";
import TodayClient from "./TodayClient";
import { type ClientGroup, type TodayItem } from "./TodayBoard";
import { type RelationshipItem } from "./RelationshipWidget";

type AlertRow = {
  id: string;
  client_id: string;
  client_name: string | null;
  client_suitability: string | null;
  alert_type: string;
  severity: "critical" | "opportunity" | "follow_up";
  explanation: string | null;
  status: string;
  created_at: string | null;
};

type InsightRow = {
  id: string;
  client_id: string;
  client_name: string | null;
  client_suitability: string | null;
  insight_type: string;
  severity: "critical" | "opportunity" | "follow_up";
  title: string;
  explanation: string | null;
  status: string;
};

const ALERT_TYPE_LABELS: Record<string, string> = {
  idle_cash: "Caixa ociosa",
  concentration: "Concentração",
  upcoming_maturity: "Vencimento próximo",
  relevant_movement: "Movimentação relevante",
  no_recent_contact: "Sem contato recente",
  followup_overdue: "Follow-up atrasado",
  behavioral_unusual_movement: "Movimentação fora do padrão",
  behavioral_unusual_allocation_shift: "Alocação fora do padrão",
};

const INSIGHT_TYPE_LABELS: Record<string, string> = {
  concentration_by_issuer: "Concentração por emissor",
};

const SEVERITY_WEIGHT: Record<string, number> = { critical: 3, opportunity: 2, follow_up: 1 };
const SEVERITY_ORDER: Record<string, number> = { critical: 0, opportunity: 1, follow_up: 2 };

async function getAlerts(): Promise<AlertRow[]> {
  const { getToken } = await auth();
  const token = await getToken();

  const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/alerts/?status=new`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    cache: "no-store",
  });

  if (!res.ok) return [];
  return res.json();
}

async function getInsights(): Promise<InsightRow[]> {
  const { getToken } = await auth();
  const token = await getToken();

  const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/insights/?status=new`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    cache: "no-store",
  });

  if (!res.ok) return [];
  return res.json();
}

async function getOpenOpportunitiesCount(): Promise<number> {
  const { getToken } = await auth();
  const token = await getToken();

  const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/opportunities/`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    cache: "no-store",
  });

  if (!res.ok) return 0;
  const opportunities: { status: string }[] = await res.json();
  return opportunities.filter((o) => !["won", "lost", "closed"].includes(o.status)).length;
}

async function getRelationshipOverview(): Promise<RelationshipItem[]> {
  const { getToken } = await auth();
  const token = await getToken();

  const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/clients/relationship-overview`, {
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

function buildGroups(alerts: AlertRow[], insights: InsightRow[]): ClientGroup[] {
  const groups = new Map<string, ClientGroup>();

  function ensureGroup(clientId: string, clientName: string | null, clientSuitability: string | null): ClientGroup {
    let group = groups.get(clientId);
    if (!group) {
      group = {
        clientId,
        clientName: clientName ?? "Cliente",
        clientSuitability,
        priorityScore: 0,
        items: [],
      };
      groups.set(clientId, group);
    }
    return group;
  }

  for (const a of alerts) {
    const group = ensureGroup(a.client_id, a.client_name, a.client_suitability);
    const item: TodayItem = {
      kind: "alert",
      id: a.id,
      severity: a.severity,
      typeLabel: ALERT_TYPE_LABELS[a.alert_type] ?? a.alert_type,
      title: null,
      explanation: a.explanation,
      status: a.status,
      firstSeenAt: a.created_at,
    };
    group.items.push(item);
    group.priorityScore += SEVERITY_WEIGHT[a.severity] ?? 0;
  }

  for (const i of insights) {
    const group = ensureGroup(i.client_id, i.client_name, i.client_suitability);
    const item: TodayItem = {
      kind: "insight",
      id: i.id,
      severity: i.severity,
      typeLabel: INSIGHT_TYPE_LABELS[i.insight_type] ?? i.insight_type,
      title: i.title,
      explanation: i.explanation,
      status: i.status,
      firstSeenAt: null,
    };
    group.items.push(item);
    group.priorityScore += SEVERITY_WEIGHT[i.severity] ?? 0;
  }

  const result = Array.from(groups.values());
  for (const group of result) {
    group.items.sort((a, b) => (SEVERITY_ORDER[a.severity] ?? 9) - (SEVERITY_ORDER[b.severity] ?? 9));
  }
  result.sort((a, b) => b.priorityScore - a.priorityScore);
  return result;
}

export default async function Today() {
  const [alerts, insights, relationship, opportunityCount] = await Promise.all([
    getAlerts(),
    getInsights(),
    getRelationshipOverview(),
    getOpenOpportunitiesCount(),
  ]);
  const groups = buildGroups(alerts, insights);
  const totalOpen = alerts.length + insights.length;

  return (
    <main className="mx-auto max-w-6xl px-6 py-10 sm:py-14">
      <header className="mb-6 flex items-end justify-between border-b border-[#14181F]/10 pb-6">
        <div>
          <p className="text-sm capitalize text-[#14181F]/50">{formatToday()}</p>
          <h1 className="font-display text-4xl font-semibold tracking-tight">Today</h1>
        </div>
        <div className="text-right">
          <p className="font-mono text-2xl font-semibold tabular-nums">{totalOpen}</p>
          <p className="text-sm text-[#14181F]/50">
            {totalOpen === 1 ? "item em aberto" : "itens em aberto"}
            {" · "}
            {groups.length === 1 ? "1 cliente" : `${groups.length} clientes`}
          </p>
        </div>
      </header>

      {totalOpen === 0 && relationship.length === 0 ? (
        <div className="rounded-lg border border-dashed border-[#14181F]/15 py-16 text-center">
          <p className="text-lg font-medium">Nada em aberto agora.</p>
          <p className="mt-1 text-sm text-[#14181F]/50">
            Assim que a próxima sincronização rodar, novidades aparecem aqui.
          </p>
        </div>
      ) : (
        <TodayClient groups={groups} relationship={relationship} opportunityCount={opportunityCount} />
      )}
    </main>
  );
}
