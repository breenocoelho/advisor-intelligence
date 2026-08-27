"use client";

import { useState } from "react";
import PortfolioAnalyticsTab from "./PortfolioAnalyticsTab";
import RelationshipPanel from "./RelationshipPanel";
import SvgLineChart from "../../SvgLineChart";
import OverridableField from "./OverridableField";
import type { ScoreBreakdownItem } from "../../ScoreTooltip";

export type Position = {
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

export type AlertItem = {
  id: string;
  alert_type: string;
  severity: "critical" | "opportunity" | "follow_up";
  explanation: string | null;
  status: string;
  created_at: string | null;
};

export type TaskItem = {
  id: string;
  description: string;
  due_date: string | null;
  status: string;
  created_at: string | null;
};

export type InsightItem = {
  id: string;
  insight_type: string;
  severity: "critical" | "opportunity" | "follow_up";
  title: string;
  explanation: string | null;
  status: string;
};

export type SnapshotPoint = {
  snapshot_date: string;
  aum: number | null;
  health_score: number | null;
};

export type InteractionItem = {
  id: string;
  interaction_type: string;
  interaction_date: string;
  subject: string | null;
  notes: string | null;
  created_at: string | null;
};

export type ClientDetail = {
  id: string;
  xp_client_id: string | null;
  name: string;
  aum: number | null;
  suitability: string | null;
  person_type: string | null;
  income_value: number | null;
  registration_updated_at: string | null;
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
  alerts: AlertItem[];
  tasks: TaskItem[];
  insights: InsightItem[];
  health_score: number | null;
  health_score_breakdown: ScoreBreakdownItem[];
  aum_trend: SnapshotPoint[];
  interactions: InteractionItem[];
  relationship_score: number | null;
  relationship_score_band: string | null;
  relationship_score_breakdown: ScoreBreakdownItem[];
  relationship_score_components: Record<string, number> | null;
  relationship_score_explanation: string[];
  field_overrides: Record<string, string>;
  extended_fields: { assignment_id: string; field_key: string; field_label: string; option_id: string; option_value: string }[];
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
  followup_overdue: "Follow-up atrasado",
};

const INSIGHT_TYPE_LABELS: Record<string, string> = {
  concentration_by_issuer: "Concentração por emissor",
};

const STATUS_LABELS: Record<string, string> = {
  new: "Novo",
  viewed: "Visualizado",
  dismissed: "Descartado",
  actioned: "Acionado",
};

const INFLOW_COLOR = "#3F7D5B";
const OUTFLOW_COLOR = "#B23A48";

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

function formatPersonType(value: string | null): string {
  if (value === "F") return "Física";
  if (value === "J") return "Jurídica";
  return "—";
}

function formatDate(value: string | null): string {
  if (!value) return "—";
  return new Date(value).toLocaleDateString("pt-BR");
}

function healthScoreColor(score: number | null): string {
  if (score === null) return "#14181F66";
  if (score >= 80) return "#3F7D5B";
  if (score >= 60) return "#A6790A";
  return "#B23A48";
}

const TABS = ["Overview", "Portfolio Analytics", "Relationship", "Alertas", "Tarefas"] as const;
type Tab = (typeof TABS)[number];

export default function ClientTabs({
  client,
  positionDates,
}: {
  client: ClientDetail;
  positionDates: string[];
}) {
  const [activeTab, setActiveTab] = useState<Tab>("Overview");

  const totalInflow = client.positions.reduce((sum, p) => sum + p.period_purchase_value, 0);
  const totalOutflow = client.positions.reduce((sum, p) => sum + p.period_sale_value, 0);
  const netFlow = totalInflow - totalOutflow;
  const hasMovement = totalInflow > 0 || totalOutflow > 0;

  const openAlertsCount = client.alerts.filter((a) => a.status === "new").length + client.insights.filter((i) => i.status === "new" || i.status === "viewed").length;
  const openTasksCount = client.tasks.filter((t) => t.status === "pending").length;

  return (
    <div>
      <div className="mb-8 flex gap-1 overflow-x-auto border-b border-[#14181F]/10">
        {TABS.map((tab) => {
          const count =
            tab === "Alertas" ? openAlertsCount : tab === "Tarefas" ? openTasksCount : null;
          return (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`shrink-0 border-b-2 px-4 py-2.5 text-sm font-medium transition ${
                activeTab === tab
                  ? "border-[#14181F] text-[#14181F]"
                  : "border-transparent text-[#14181F]/50 hover:text-[#14181F]/80"
              }`}
            >
              {tab}
              {count !== null && count > 0 && (
                <span className="ml-1.5 font-mono text-xs tabular-nums text-[#14181F]/40">{count}</span>
              )}
            </button>
          );
        })}
      </div>

      {activeTab === "Overview" && (
        <div>
          <section className="mb-10 grid grid-cols-2 gap-4 sm:grid-cols-4">
            <div className="card p-4">
              <p className="text-xs uppercase tracking-wide text-[#14181F]/40">Código da conta</p>
              <p className="mt-1 font-mono text-sm tabular-nums">{client.xp_client_id ?? "—"}</p>
            </div>
            <div className="card p-4">
              <p className="text-xs uppercase tracking-wide text-[#14181F]/40">Tipo de pessoa</p>
              <OverridableField fieldKey="person_type" originalDisplay={formatPersonType(client.person_type)} overrides={client.field_overrides} />
            </div>
            <div className="card p-4">
              <p className="text-xs uppercase tracking-wide text-[#14181F]/40">Perfil (suitability)</p>
              <OverridableField fieldKey="suitability" originalDisplay={formatSuitability(client.suitability)} overrides={client.field_overrides} />
            </div>
            <div className="card p-4">
              <p className="text-xs uppercase tracking-wide text-[#14181F]/40">Atualização cadastral (XP)</p>
              <p className="mt-1 font-mono text-sm tabular-nums">{formatDate(client.registration_updated_at)}</p>
            </div>
            <div className="card p-4">
              <p className="text-xs uppercase tracking-wide text-[#14181F]/40">Nascimento</p>
              <p className="mt-1 font-mono text-sm tabular-nums">
                {formatBirth(client.birth_year, client.birth_month)}
              </p>
            </div>
            <div className="card p-4">
              <p className="text-xs uppercase tracking-wide text-[#14181F]/40">Estado civil</p>
              <OverridableField fieldKey="marital_status" originalDisplay={client.marital_status ?? "—"} overrides={client.field_overrides} />
            </div>
            <div className="card p-4">
              <p className="text-xs uppercase tracking-wide text-[#14181F]/40">Renda declarada</p>
              <OverridableField fieldKey="income_value" originalDisplay={formatCurrency(client.income_value)} overrides={client.field_overrides} />
            </div>
            <div className="card p-4">
              <p className="text-xs uppercase tracking-wide text-[#14181F]/40">Patrimônio declarado</p>
              <OverridableField fieldKey="declared_wealth_total" originalDisplay={formatCurrency(client.declared_wealth_total)} overrides={client.field_overrides} />
            </div>
          </section>

          {client.extended_fields.length > 0 && (
            <section className="mb-10">
              <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-[#14181F]/70">Classificações</h2>
              <div className="flex flex-wrap gap-2">
                {client.extended_fields.map((f) => (
                  <span
                    key={f.assignment_id}
                    className="inline-flex items-center gap-1.5 rounded-full bg-[#14181F]/5 px-3 py-1 text-sm"
                  >
                    <span className="text-xs uppercase tracking-wide text-[#14181F]/40">{f.field_label}:</span>
                    {f.option_value}
                  </span>
                ))}
              </div>
            </section>
          )}

          {hasMovement && (
            <section className="mb-10">
              <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-[#14181F]/70">
                Movimentação no período
              </h2>
              <div className="grid grid-cols-3 gap-4">
                <div className="card p-4">
                  <p className="text-xs uppercase tracking-wide text-[#14181F]/40">Aportes</p>
                  <p className="mt-1 font-mono text-xl font-semibold tabular-nums" style={{ color: INFLOW_COLOR }}>
                    + {formatCurrency(totalInflow)}
                  </p>
                </div>
                <div className="card p-4">
                  <p className="text-xs uppercase tracking-wide text-[#14181F]/40">Resgates</p>
                  <p className="mt-1 font-mono text-xl font-semibold tabular-nums" style={{ color: OUTFLOW_COLOR }}>
                    − {formatCurrency(totalOutflow)}
                  </p>
                </div>
                <div className="card p-4">
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

          {client.aum_trend.length > 0 && (
            <section>
              <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-[#14181F]/70">Tendência</h2>
              <div className="card mb-3 p-4">
                <SvgLineChart
                  points={client.aum_trend
                    .filter((p) => p.aum !== null)
                    .map((p) => ({
                      label: new Date(p.snapshot_date).toLocaleDateString("pt-BR", { day: "2-digit", month: "short" }),
                      value: p.aum as number,
                    }))}
                  formatValue={formatCurrency}
                />
              </div>
              <div className="overflow-hidden card">
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
                        <td className="px-4 py-3 font-mono text-[#14181F]/70">{formatDate(point.snapshot_date)}</td>
                        <td className="px-4 py-3 text-right font-mono tabular-nums">{formatCurrency(point.aum)}</td>
                        <td className="px-4 py-3 text-right font-mono tabular-nums">
                          {point.health_score !== null ? (
                            <span style={{ color: healthScoreColor(point.health_score) }}>{point.health_score}</span>
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
        </div>
      )}

      {activeTab === "Portfolio Analytics" && (
        <PortfolioAnalyticsTab clientId={client.id} positionDates={positionDates} />
      )}

      {activeTab === "Relationship" && <RelationshipPanel client={client} />}

      {activeTab === "Alertas" && (
        <div>
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
                    <div key={alert.id} className="flex items-start justify-between gap-4 card p-3">
                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          <span
                            className="rounded-full px-2 py-0.5 text-xs font-medium uppercase tracking-wide"
                            style={{ backgroundColor: `${config.accent}1a`, color: config.accent }}
                          >
                            {ALERT_TYPE_LABELS[alert.alert_type] ?? alert.alert_type}
                          </span>
                          <span className="text-xs text-[#14181F]/30">{STATUS_LABELS[alert.status] ?? alert.status}</span>
                        </div>
                        <p className="mt-1 text-sm text-[#14181F]/70">{alert.explanation}</p>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </section>

          <section>
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
                    <div key={insight.id} className="flex items-start justify-between gap-4 card p-3">
                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          <span
                            className="rounded-full px-2 py-0.5 text-xs font-medium uppercase tracking-wide"
                            style={{ backgroundColor: `${config.accent}1a`, color: config.accent }}
                          >
                            {INSIGHT_TYPE_LABELS[insight.insight_type] ?? insight.insight_type}
                          </span>
                          <span className="text-xs text-[#14181F]/30">{STATUS_LABELS[insight.status] ?? insight.status}</span>
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
        </div>
      )}

      {activeTab === "Tarefas" && (
        <section>
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-[#14181F]/70">
            Tarefas ({client.tasks.length})
          </h2>
          {client.tasks.length === 0 ? (
            <p className="text-sm text-[#14181F]/50">Nenhuma tarefa em aberto.</p>
          ) : (
            <div className="space-y-2">
              {client.tasks.map((task) => (
                <div key={task.id} className="flex items-center justify-between card p-3">
                  <p className="text-sm">{task.description}</p>
                  <div className="flex shrink-0 items-center gap-3">
                    {task.due_date && (
                      <span className="font-mono text-xs tabular-nums text-[#14181F]/40">
                        até {formatDate(task.due_date)}
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
      )}
    </div>
  );
}
