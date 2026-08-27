import { auth } from "@clerk/nextjs/server";
import ThresholdRuleForm from "./ThresholdRuleForm";
import DeleteRuleButton from "./DeleteRuleButton";

type ThresholdRule = {
  id: string;
  signal_key: string;
  suitability_profile: string | null;
  value: number;
  updated_at: string | null;
  updated_by: string | null;
};

type ThresholdRulesResponse = {
  defaults: Record<string, number>;
  rules: ThresholdRule[];
};

const SIGNAL_LABELS: Record<string, string> = {
  idle_cash: "Caixa ociosa (% do AUM)",
  concentration: "Concentração por posição (% do AUM)",
  concentration_issuer: "Concentração por emissor (% do AUM)",
  upcoming_maturity_days: "Vencimento próximo (dias)",
  relevant_movement: "Movimentação relevante (% do AUM)",
  no_contact_days: "Sem contato (dias)",
  health_score_good: "Health Score — faixa boa (mínimo)",
  health_score_warn: "Health Score — faixa de atenção (mínimo)",
};

async function getThresholdRules(): Promise<ThresholdRulesResponse> {
  const { getToken } = await auth();
  const token = await getToken();

  const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/threshold-rules/`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    cache: "no-store",
  });

  if (!res.ok) return { defaults: {}, rules: [] };
  return res.json();
}

export default async function ThresholdsPage() {
  const { defaults, rules } = await getThresholdRules();
  const signalKeys = Object.keys(defaults);

  return (
    <main className="mx-auto max-w-3xl px-6 py-10 sm:py-14">
      <header className="mb-8 border-b border-[#14181F]/10 pb-6">
        <p className="text-sm text-[#14181F]/50">Motor de alertas e insights</p>
        <h1 className="font-display text-4xl font-semibold tracking-tight">Thresholds</h1>
        <p className="mt-2 text-sm text-[#14181F]/60">
          Overrides por organização (perfil em branco) ou por perfil de suitability. Sem
          override, cada sinal usa o default do sistema abaixo.
        </p>
      </header>

      <section className="mb-10">
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-[#14181F]/70">
          Defaults do sistema
        </h2>
        <div className="overflow-hidden rounded-lg border border-[#14181F]/10 bg-white">
          <table className="w-full text-sm">
            <tbody>
              {signalKeys.map((key) => (
                <tr key={key} className="border-b border-[#14181F]/5 last:border-0">
                  <td className="px-4 py-3">{SIGNAL_LABELS[key] ?? key}</td>
                  <td className="px-4 py-3 text-right font-mono tabular-nums text-[#14181F]/60">
                    {defaults[key]}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="mb-10">
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-[#14181F]/70">
          Overrides ativos ({rules.length})
        </h2>
        {rules.length === 0 ? (
          <p className="text-sm text-[#14181F]/50">
            Nenhum override configurado — todos os clientes usam os defaults do sistema.
          </p>
        ) : (
          <div className="space-y-2">
            {rules.map((rule) => (
              <div
                key={rule.id}
                className="flex items-center justify-between gap-4 rounded-lg border border-[#14181F]/10 bg-white p-3"
              >
                <div className="min-w-0">
                  <p className="text-sm font-medium">{SIGNAL_LABELS[rule.signal_key] ?? rule.signal_key}</p>
                  <p className="mt-1 text-xs text-[#14181F]/50">
                    {rule.suitability_profile ? `Perfil: ${rule.suitability_profile}` : "Default da organização"}
                  </p>
                </div>
                <div className="flex shrink-0 items-center gap-3">
                  <span className="font-mono text-sm font-semibold tabular-nums">{rule.value}</span>
                  <DeleteRuleButton ruleId={rule.id} />
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      <ThresholdRuleForm signalKeys={signalKeys} />
    </main>
  );
}
