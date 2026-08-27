import { auth } from "@clerk/nextjs/server";
import Link from "next/link";
import { notFound } from "next/navigation";
import AssetPositionsComparison from "./AssetPositionsComparison";
import AssetPriceTrend from "./AssetPriceTrend";
import AssetFlows from "./AssetFlows";

type SnapshotPoint = {
  snapshot_date: string;
  total_value: number;
};

type AlertRow = {
  id: string;
  client_id: string;
  client_name: string | null;
  alert_type: string;
  severity: "critical" | "opportunity" | "follow_up";
  explanation: string | null;
  status: string;
};

type TaskRow = {
  id: string;
  client_id: string;
  client_name: string | null;
  description: string;
  due_date: string | null;
  status: string;
};

type ClientPosition = {
  client_id: string;
  client_name: string;
  market_value: number;
  quantity: number | null;
  pct_of_client_aum: number | null;
};

type AssetDetail = {
  id: string;
  name: string;
  asset_class: string;
  issuer: string | null;
  isin_code: string | null;
  cnpj_code: string | null;
  asset_code: string | null;
  due_date: string | null;
  rate: number | null;
  index_description: string | null;
  manager_name: string | null;
  payment_frequency: string | null;
  liquidity_days: number | null;
  minimum_investment: number | null;
  risk_rating: string | null;
  aum_trend: SnapshotPoint[];
  alerts: AlertRow[];
  tasks: TaskRow[];
  client_positions: ClientPosition[];
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

function formatCurrency(value: number | null): string {
  if (value === null) return "—";
  return value.toLocaleString("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 });
}

function formatDate(value: string | null): string {
  if (!value) return "—";
  return new Date(value).toLocaleDateString("pt-BR");
}

async function getAsset(id: string): Promise<AssetDetail | null> {
  const { getToken } = await auth();
  const token = await getToken();

  const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/assets/${id}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    cache: "no-store",
  });

  if (res.status === 404) return null;
  if (!res.ok) throw new Error("Falha ao carregar ativo");
  return res.json();
}

export default async function Asset360Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const asset = await getAsset(id);

  if (!asset) notFound();

  const positionDates = asset.aum_trend.map((p) => p.snapshot_date);
  const latestExposure = asset.aum_trend.length > 0 ? asset.aum_trend[asset.aum_trend.length - 1].total_value : 0;

  return (
    <main className="mx-auto max-w-4xl px-6 py-10 sm:py-14">
      <Link href="/ativos" className="text-sm text-[#14181F]/50 hover:underline">
        ← Ativos
      </Link>

      <header className="mt-4 mb-8 flex items-end justify-between border-b border-[#14181F]/10 pb-6">
        <div>
          <p className="text-sm text-[#14181F]/50">
            {ASSET_CLASS_LABELS[asset.asset_class] ?? asset.asset_class}
          </p>
          <h1 className="font-display text-4xl font-semibold tracking-tight">{asset.name}</h1>
          {asset.issuer && <p className="mt-1 text-sm text-[#14181F]/60">{asset.issuer}</p>}
        </div>
        <div className="text-right">
          <p className="font-mono text-2xl font-semibold tabular-nums">{formatCurrency(latestExposure)}</p>
          <p className="text-sm text-[#14181F]/50">exposição total do escritório</p>
        </div>
      </header>

      {/* Cadastro */}
      <section className="mb-10 grid grid-cols-2 gap-4 sm:grid-cols-4">
        <div className="card p-4">
          <p className="text-xs uppercase tracking-wide text-[#14181F]/40">Código</p>
          <p className="mt-1 font-mono text-sm tabular-nums">{asset.asset_code ?? "—"}</p>
        </div>
        <div className="card p-4">
          <p className="text-xs uppercase tracking-wide text-[#14181F]/40">ISIN / CNPJ</p>
          <p className="mt-1 font-mono text-sm tabular-nums">
            {asset.isin_code ?? asset.cnpj_code ?? "—"}
          </p>
        </div>
        <div className="card p-4">
          <p className="text-xs uppercase tracking-wide text-[#14181F]/40">Vencimento</p>
          <p className="mt-1 font-mono text-sm tabular-nums">{formatDate(asset.due_date)}</p>
        </div>
        <div className="card p-4">
          <p className="text-xs uppercase tracking-wide text-[#14181F]/40">Taxa / Indexador</p>
          <p className="mt-1 font-mono text-sm tabular-nums">
            {asset.rate !== null ? `${asset.rate}${asset.index_description ? ` ${asset.index_description}` : "%"}` : "—"}
          </p>
        </div>
        <div className="card p-4">
          <p className="text-xs uppercase tracking-wide text-[#14181F]/40">Gestora</p>
          <p className="mt-1 text-sm">{asset.manager_name ?? "—"}</p>
        </div>
        <div className="card p-4">
          <p className="text-xs uppercase tracking-wide text-[#14181F]/40">Pagamento</p>
          <p className="mt-1 text-sm">{asset.payment_frequency ?? "—"}</p>
        </div>
        <div className="card p-4">
          <p className="text-xs uppercase tracking-wide text-[#14181F]/40">Liquidez</p>
          <p className="mt-1 font-mono text-sm tabular-nums">
            {asset.liquidity_days !== null ? `D+${asset.liquidity_days}` : "—"}
          </p>
        </div>
        <div className="card p-4">
          <p className="text-xs uppercase tracking-wide text-[#14181F]/40">Aplicação mínima</p>
          <p className="mt-1 font-mono text-sm tabular-nums">{formatCurrency(asset.minimum_investment)}</p>
        </div>
        {asset.risk_rating && (
          <div className="card p-4">
            <p className="text-xs uppercase tracking-wide text-[#14181F]/40">Classificação de risco</p>
            <p
              className="mt-1 text-sm font-medium"
              style={{
                color:
                  asset.risk_rating === "Baixo" ? "#3F7D5B" : asset.risk_rating === "Alto" ? "#B23A48" : "#A6790A",
              }}
            >
              {asset.risk_rating}
            </p>
          </div>
        )}
      </section>

      {/* Tendencia */}
      {asset.aum_trend.length > 0 && (
        <section className="mb-10">
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-[#14181F]/70">
            Tendência — exposição total do escritório
          </h2>
          <div className="overflow-hidden card">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[#14181F]/10 text-left text-xs uppercase tracking-wide text-[#14181F]/40">
                  <th className="px-4 py-3 font-medium">Data</th>
                  <th className="px-4 py-3 text-right font-medium">Exposição total</th>
                </tr>
              </thead>
              <tbody>
                {asset.aum_trend.map((point) => (
                  <tr key={point.snapshot_date} className="border-b border-[#14181F]/5 last:border-0">
                    <td className="px-4 py-3 font-mono text-[#14181F]/70">{formatDate(point.snapshot_date)}</td>
                    <td className="px-4 py-3 text-right font-mono tabular-nums">
                      {formatCurrency(point.total_value)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* Preco unitario -- rentabilidade vs aporte/resgate */}
      <AssetPriceTrend assetId={asset.id} />

      {/* Compras/vendas por cliente num periodo */}
      <AssetFlows assetId={asset.id} availableDates={positionDates} />

      {/* Alertas */}
      <section className="mb-10">
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-[#14181F]/70">
          Alertas ({asset.alerts.length})
        </h2>
        {asset.alerts.length === 0 ? (
          <p className="text-sm text-[#14181F]/50">Nenhum alerta relacionado a este ativo.</p>
        ) : (
          <div className="space-y-2">
            {asset.alerts.map((alert) => {
              const config = SEVERITY_CONFIG[alert.severity];
              return (
                <div key={alert.id} className="flex items-start justify-between gap-4 card p-3">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <Link href={`/clientes/${alert.client_id}`} className="text-sm font-medium hover:underline">
                        {alert.client_name ?? "Cliente"}
                      </Link>
                      <span
                        className="rounded-full px-2 py-0.5 text-xs font-medium uppercase tracking-wide"
                        style={{ backgroundColor: `${config.accent}1a`, color: config.accent }}
                      >
                        {ALERT_TYPE_LABELS[alert.alert_type] ?? alert.alert_type}
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

      {/* Tarefas */}
      <section className="mb-10">
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-[#14181F]/70">
          Tarefas ({asset.tasks.length})
        </h2>
        {asset.tasks.length === 0 ? (
          <p className="text-sm text-[#14181F]/50">
            Nenhuma tarefa relacionada a este ativo (só tarefas criadas a partir de um alerta de
            concentração/vencimento carregam essa ligação).
          </p>
        ) : (
          <div className="space-y-2">
            {asset.tasks.map((task) => (
              <div key={task.id} className="flex items-center justify-between card p-3">
                <div className="min-w-0">
                  <Link href={`/clientes/${task.client_id}`} className="text-sm font-medium hover:underline">
                    {task.client_name ?? "Cliente"}
                  </Link>
                  <p className="mt-1 text-sm text-[#14181F]/70">{task.description}</p>
                </div>
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

      {/* Posicoes por cliente, com comparacao de datas */}
      <AssetPositionsComparison assetId={asset.id} availableDates={positionDates} />
    </main>
  );
}
