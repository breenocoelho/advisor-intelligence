import { auth } from "@clerk/nextjs/server";
import Link from "next/link";
import { notFound } from "next/navigation";
import ContactButton from "./ContactButton";
import PositionsComparison from "./PositionsComparison";

type Position = {
  id: string;
  asset_name: string;
  asset_class: string;
  market_value: number;
  quantity: number | null;
  due_date: string | null;
  issuer: string | null;
  rate: number | null;
  index_description: string | null;
  position_date: string;
  period_purchase_value: number;
  period_sale_value: number;
};

type Alert = {
  id: string;
  alert_type: string;
  severity: "critical" | "opportunity" | "follow_up";
  explanation: string | null;
  status: string;
  created_at: string | null;
};

type Task = {
  id: string;
  description: string;
  due_date: string | null;
  status: string;
};

type Insight = {
  id: string;
  insight_type: string;
  severity: "critical" | "opportunity" | "follow_up";
  title: string;
  explanation: string | null;
  status: string;
};

type SnapshotPoint = {
  snapshot_date: string;
  aum: number | null;
  health_score: number | null;
};

type ClientDetail = {
  id: string;
  xp_client_id: string | null;
  name: string;
  aum: number | null;
  suitability: string | null;
  advisor_name: string | null;
  active_alerts_count: number;
  last_contact_at: string | null;
  birth_year: number | null;
  birth_month: number | null;
  marital_status: string | null;
  activity: string | null;
  declared_wealth_total: number | null;
  qualified_investor: string | null;
  professional_investor: string | null;
  positions: Position[];
  alerts: Alert[];
  tasks: Task[];
  insights: Insight[];
  health_score: number | null;
  aum_trend: SnapshotPoint[];
};

const SEVERITY_CONFIG = {
  critical: { label: "Crítico", accent: "#B23A48" },
  opportunity: { label: "Oportunidade", accent: "#A6790A" },
  follow_up: { label: "Follow-up", accent: "#3E5C76" },
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

const STATUS_LABELS: Record<string, string> = {
  new: "Novo",
  viewed: "Visualizado",
  dismissed: "Descartado",
  actioned: "Acionado",
};

const INFLOW_COLOR = "#3F7D5B";
const OUTFLOW_COLOR = "#B23A48";

async function getClient(id: string): Promise<ClientDetail | null> {
  const { getToken } = await auth();
  const token = await getToken();

  const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/clients/${id}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    cache: "no-store",
  });

  if (res.status === 404) return null;
  if (!res.ok) throw new Error("Falha ao carregar cliente");
  return res.json();
}

async function getPositionDates(id: string): Promise<string[]> {
  const { getToken } = await auth();
  const token = await getToken();

  const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/clients/${id}/position-dates`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    cache: "no-store",
  });

  if (!res.ok) return [];
  return res.json();
}

function formatCurrency(value: number | null): string {
  if (value === null) return "—";
  return value.toLocaleString("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 });
}

function formatSuitability(value: string | null): string {
  if (!value) return "—";
  return value.charAt(0) + value.slice(1).toLowerCase();
}

function formatBirth(year: number | null, month: number | null): string {
  if (!year) return "—";
  return month ? `${String(month).padStart(2, "0")}/${year}` : `${year}`;
}

function healthScoreColor(score: number | null): string {
  if (score === null) return "#14181F66";
  if (score >= 80) return "#3F7D5B";
  if (score >= 60) return "#A6790A";
  return "#B23A48";
}

function formatLastContact(value: string | null): string {
  if (!value) return "nunca registrado";
  const days = Math.floor((Date.now() - new Date(value).getTime()) / (1000 * 60 * 60 * 24));
  if (days === 0) return "hoje";
  if (days === 1) return "há 1 dia";
  return `há ${days} dias`;
}

export default async function Client360Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const client = await getClient(id);

  if (!client) notFound();

  const positionDates = await getPositionDates(id);

  const totalPositions = client.positions.reduce((sum, p) => sum + p.market_value, 0);
  const totalInflow = client.positions.reduce((sum, p) => sum + p.period_purchase_value, 0);
  const totalOutflow = client.positions.reduce((sum, p) => sum + p.period_sale_value, 0);
  const netFlow = totalInflow - totalOutflow;
  const hasMovement = totalInflow > 0 || totalOutflow > 0;

  return (
    <main className="mx-auto max-w-4xl px-6 py-10 sm:py-14">
      <Link href="/clientes" className="text-sm text-[#14181F]/50 hover:underline">
        ← Clientes
      </Link>

      <header className="mt-4 mb-8 flex items-end justify-between border-b border-[#14181F]/10 pb-6">
        <div>
          <p className="text-sm text-[#14181F]/50">#{client.xp_client_id}</p>
          <h1 className="font-display text-4xl font-semibold tracking-tight">{client.name}</h1>
          <p className="mt-1 text-sm text-[#14181F]/60">
            {client.advisor_name ?? "Sem assessor vinculado"} · {formatSuitability(client.suitability)}
          </p>
          <div className="mt-3 flex items-center gap-3">
            <span className="text-sm text-[#14181F]/50">
              Último contato: {formatLastContact(client.last_contact_at)}
            </span>
            <ContactButton clientId={client.id} />
          </div>
        </div>
        <div className="text-right">
          <p className="font-mono text-2xl font-semibold tabular-nums">{formatCurrency(client.aum)}</p>
          <p className="text-sm text-[#14181F]/50">patrimônio (AUM)</p>
          {client.health_score !== null && (
            <p className="mt-2 inline-flex items-center gap-1.5 rounded-full bg-[#14181F]/5 px-2.5 py-1">
              <span
                className="h-1.5 w-1.5 rounded-full"
                style={{ backgroundColor: healthScoreColor(client.health_score) }}
              />
              <span className="font-mono text-xs font-semibold tabular-nums">
                {client.health_score}
              </span>
              <span className="text-xs text-[#14181F]/50">health score</span>
            </p>
          )}
        </div>
      </header>

      {/* Perfil */}
      <section className="mb-10 grid grid-cols-2 gap-4 sm:grid-cols-4">
        <div className="rounded-lg border border-[#14181F]/10 bg-white p-4">
          <p className="text-xs uppercase tracking-wide text-[#14181F]/40">Nascimento</p>
          <p className="mt-1 font-mono text-sm tabular-nums">
            {formatBirth(client.birth_year, client.birth_month)}
          </p>
        </div>
        <div className="rounded-lg border border-[#14181F]/10 bg-white p-4">
          <p className="text-xs uppercase tracking-wide text-[#14181F]/40">Estado civil</p>
          <p className="mt-1 text-sm">{client.marital_status ?? "—"}</p>
        </div>
        <div className="rounded-lg border border-[#14181F]/10 bg-white p-4">
          <p className="text-xs uppercase tracking-wide text-[#14181F]/40">Patrimônio declarado</p>
          <p className="mt-1 font-mono text-sm tabular-nums">
            {formatCurrency(client.declared_wealth_total)}
          </p>
        </div>
        <div className="rounded-lg border border-[#14181F]/10 bg-white p-4">
          <p className="text-xs uppercase tracking-wide text-[#14181F]/40">Investidor qualificado</p>
          <p className="mt-1 text-sm">{client.qualified_investor === "S" ? "Sim" : "Não"}</p>
        </div>
      </section>

      {/* Movimentação no período */}
      {hasMovement && (
        <section className="mb-10">
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-[#14181F]/70">
            Movimentação no período
          </h2>
          <div className="grid grid-cols-3 gap-4">
            <div className="rounded-lg border border-[#14181F]/10 bg-white p-4">
              <p className="text-xs uppercase tracking-wide text-[#14181F]/40">Aportes</p>
              <p className="mt-1 font-mono text-xl font-semibold tabular-nums" style={{ color: INFLOW_COLOR }}>
                + {formatCurrency(totalInflow)}
              </p>
            </div>
            <div className="rounded-lg border border-[#14181F]/10 bg-white p-4">
              <p className="text-xs uppercase tracking-wide text-[#14181F]/40">Resgates</p>
              <p className="mt-1 font-mono text-xl font-semibold tabular-nums" style={{ color: OUTFLOW_COLOR }}>
                − {formatCurrency(totalOutflow)}
              </p>
            </div>
            <div className="rounded-lg border border-[#14181F]/10 bg-white p-4">
              <p className="text-xs uppercase tracking-wide text-[#14181F]/40">Fluxo líquido</p>
              <p
                className="mt-1 font-mono text-xl font-semibold tabular-nums"
                style={{ color: netFlow >= 0 ? INFLOW_COLOR : OUTFLOW_COLOR }}
              >
                {netFlow >= 0 ? "+" : "−"} {formatCurrency(Math.abs(netFlow))}
              </p>
            </div>
          </div>
        </section>
      )}

      {/* Tendencia (client_daily_snapshot) */}
      {client.aum_trend.length > 0 && (
        <section className="mb-10">
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-[#14181F]/70">
            Tendência
          </h2>
          <div className="overflow-hidden rounded-lg border border-[#14181F]/10 bg-white">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[#14181F]/10 text-left text-xs uppercase tracking-wide text-[#14181F]/40">
                  <th className="px-4 py-3 font-medium">Data</th>
                  <th className="px-4 py-3 text-right font-medium">AUM</th>
                  <th className="px-4 py-3 text-right font-medium">Health score</th>
                </tr>
              </thead>
              <tbody>
                {client.aum_trend.map((point) => (
                  <tr key={point.snapshot_date} className="border-b border-[#14181F]/5 last:border-0">
                    <td className="px-4 py-3 font-mono text-[#14181F]/70">
                      {new Date(point.snapshot_date).toLocaleDateString("pt-BR")}
                    </td>
                    <td className="px-4 py-3 text-right font-mono tabular-nums">
                      {formatCurrency(point.aum)}
                    </td>
                    <td className="px-4 py-3 text-right font-mono tabular-nums">
                      {point.health_score !== null ? (
                        <span style={{ color: healthScoreColor(point.health_score) }}>
                          {point.health_score}
                        </span>
                      ) : (
                        "—"
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* Alertas */}
      <section className="mb-10">
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-[#14181F]/70">
          Alertas ({client.alerts.length})
        </h2>
        {client.alerts.length === 0 ? (
          <p className="text-sm text-[#14181F]/50">Nenhum alerta registrado para este cliente.</p>
        ) : (
          <div className="space-y-2">
            {client.alerts.map((alert) => {
              const config = SEVERITY_CONFIG[alert.severity];
              return (
                <div
                  key={alert.id}
                  className="flex items-start justify-between gap-4 rounded-lg border border-[#14181F]/10 bg-white p-3"
                  style={{ borderLeft: `3px solid ${config.accent}` }}
                >
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-medium uppercase tracking-wide text-[#14181F]/40">
                        {ALERT_TYPE_LABELS[alert.alert_type] ?? alert.alert_type}
                      </span>
                      <span className="text-xs text-[#14181F]/30">
                        {STATUS_LABELS[alert.status] ?? alert.status}
                      </span>
                    </div>
                    <p className="mt-1 text-sm text-[#14181F]/70">{alert.explanation}</p>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </section>

      {/* Insights */}
      <section className="mb-10">
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-[#14181F]/70">
          Insights ({client.insights.length})
        </h2>
        {client.insights.length === 0 ? (
          <p className="text-sm text-[#14181F]/50">Nenhum insight registrado para este cliente.</p>
        ) : (
          <div className="space-y-2">
            {client.insights.map((insight) => {
              const config = SEVERITY_CONFIG[insight.severity];
              return (
                <div
                  key={insight.id}
                  className="flex items-start justify-between gap-4 rounded-lg border border-[#14181F]/10 bg-white p-3"
                  style={{ borderLeft: `3px solid ${config.accent}` }}
                >
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-medium uppercase tracking-wide text-[#14181F]/40">
                        {INSIGHT_TYPE_LABELS[insight.insight_type] ?? insight.insight_type}
                      </span>
                      <span className="text-xs text-[#14181F]/30">
                        {STATUS_LABELS[insight.status] ?? insight.status}
                      </span>
                    </div>
                    <p className="mt-1 text-sm font-medium">{insight.title}</p>
                    <p className="mt-1 text-sm text-[#14181F]/70">{insight.explanation}</p>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </section>

      {/* Tarefas */}
      <section className="mb-10">
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-[#14181F]/70">
          Tarefas ({client.tasks.length})
        </h2>
        {client.tasks.length === 0 ? (
          <p className="text-sm text-[#14181F]/50">Nenhuma tarefa em aberto.</p>
        ) : (
          <div className="space-y-2">
            {client.tasks.map((task) => (
              <div
                key={task.id}
                className="flex items-center justify-between rounded-lg border border-[#14181F]/10 bg-white p-3"
              >
                <p className="text-sm">{task.description}</p>
                <div className="flex shrink-0 items-center gap-3">
                  {task.due_date && (
                    <span className="font-mono text-xs tabular-nums text-[#14181F]/40">
                      até {new Date(task.due_date).toLocaleDateString("pt-BR")}
                    </span>
                  )}
                  <span className="rounded-full bg-[#14181F]/5 px-2 py-0.5 text-xs font-medium text-[#14181F]/50">
                    {task.status === "pending" ? "Pendente" : "Concluída"}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Comparacao de posicoes entre datas */}
      <PositionsComparison clientId={client.id} availableDates={positionDates} />

      {/* Posições (data mais recente) */}
      <section>
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-[#14181F]/70">
          Posições atuais ({client.positions.length})
        </h2>
        {client.positions.length === 0 ? (
          <p className="text-sm text-[#14181F]/50">Nenhuma posição sincronizada.</p>
        ) : (
          <div className="overflow-hidden rounded-lg border border-[#14181F]/10 bg-white">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[#14181F]/10 text-left text-xs uppercase tracking-wide text-[#14181F]/40">
                  <th className="px-4 py-3 font-medium">Ativo</th>
                  <th className="px-4 py-3 font-medium">Classe</th>
                  <th className="px-4 py-3 font-medium">Vencimento</th>
                  <th className="px-4 py-3 text-right font-medium">Valor</th>
                  <th className="px-4 py-3 text-right font-medium">% carteira</th>
                </tr>
              </thead>
              <tbody>
                {client.positions.map((position) => {
                  const hasInflow = position.period_purchase_value > 0;
                  const hasOutflow = position.period_sale_value > 0;
                  return (
                    <tr key={position.id} className="border-b border-[#14181F]/5 last:border-0">
                      <td className="px-4 py-3">
                        <p className="font-medium">{position.asset_name}</p>
                        {position.issuer && (
                          <p className="text-xs text-[#14181F]/40">{position.issuer}</p>
                        )}
                        {(hasInflow || hasOutflow) && (
                          <div className="mt-1 flex flex-wrap gap-x-3 gap-y-0.5">
                            {hasInflow && (
                              <span className="font-mono text-xs tabular-nums" style={{ color: INFLOW_COLOR }}>
                                + {formatCurrency(position.period_purchase_value)} aportado
                              </span>
                            )}
                            {hasOutflow && (
                              <span className="font-mono text-xs tabular-nums" style={{ color: OUTFLOW_COLOR }}>
                                − {formatCurrency(position.period_sale_value)} resgatado
                              </span>
                            )}
                          </div>
                        )}
                      </td>
                      <td className="px-4 py-3 text-[#14181F]/70">
                        {ASSET_CLASS_LABELS[position.asset_class] ?? position.asset_class}
                      </td>
                      <td className="px-4 py-3 font-mono text-[#14181F]/70">
                        {position.due_date
                          ? new Date(position.due_date).toLocaleDateString("pt-BR")
                          : "—"}
                      </td>
                      <td className="px-4 py-3 text-right font-mono tabular-nums">
                        {formatCurrency(position.market_value)}
                      </td>
                      <td className="px-4 py-3 text-right font-mono tabular-nums text-[#14181F]/50">
                        {totalPositions > 0
                          ? `${((position.market_value / totalPositions) * 100).toFixed(1)}%`
                          : "—"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </main>
  );
}