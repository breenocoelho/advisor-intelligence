"use client";

import { useState } from "react";
import ThresholdRuleForm from "./ThresholdRuleForm";
import DeleteRuleButton from "./DeleteRuleButton";
import AuditLogList from "./AuditLogList";
import FieldOverridesAdmin from "./FieldOverridesAdmin";
import SetFieldOverrideForm from "./SetFieldOverrideForm";
import ExtendedFieldsAdmin from "./ExtendedFieldsAdmin";

type ThresholdRule = {
  id: string;
  signal_key: string;
  suitability_profile: string | null;
  value: number;
  updated_at: string | null;
  updated_by: string | null;
};

type AuditLogItem = {
  id: string;
  client_id: string | null;
  client_name: string | null;
  action_type: string;
  summary: string;
  created_at: string | null;
};

type FieldOverride = {
  client_id: string;
  client_name: string;
  field_name: string;
  override_value: string;
  created_at: string | null;
};

type Option = { id: string; value: string };
type FieldDefinition = { id: string; key: string; label: string; options: Option[] };
type Client = { id: string; name: string };

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

const TABS = ["Thresholds", "Audit Log", "Overrides de Cadastro", "Campos Customizados"] as const;
type Tab = (typeof TABS)[number];

export default function ConfigTabs({
  defaults,
  rules,
  auditLogs,
  fieldOverrides,
  extendedFields,
  clients,
}: {
  defaults: Record<string, number>;
  rules: ThresholdRule[];
  auditLogs: AuditLogItem[];
  fieldOverrides: FieldOverride[];
  extendedFields: FieldDefinition[];
  clients: Client[];
}) {
  const [activeTab, setActiveTab] = useState<Tab>("Thresholds");
  const signalKeys = Object.keys(defaults);

  return (
    <div>
      <div className="mb-8 flex gap-1 overflow-x-auto border-b border-[#14181F]/10">
        {TABS.map((tab) => (
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
          </button>
        ))}
      </div>

      {activeTab === "Thresholds" && (
        <div>
          <section className="mb-10">
            <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-[#14181F]/70">
              Defaults do sistema
            </h2>
            <div className="overflow-hidden card">
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
                  <div key={rule.id} className="flex items-center justify-between gap-4 card p-3">
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
        </div>
      )}

      {activeTab === "Audit Log" && (
        <section>
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-[#14181F]/70">
            Atividade recente ({auditLogs.length})
          </h2>
          <p className="mb-4 text-xs text-[#14181F]/40">
            Tarefas criadas, interações registradas/editadas/removidas, contatos, thresholds e overrides de
            cadastro — a partir de agora.
          </p>
          <AuditLogList logs={auditLogs} />
        </section>
      )}

      {activeTab === "Overrides de Cadastro" && (
        <div>
          <section className="mb-10">
            <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-[#14181F]/70">
              Campos sobrescritos ({fieldOverrides.length})
            </h2>
            <FieldOverridesAdmin overrides={fieldOverrides} />
          </section>
          <SetFieldOverrideForm clients={clients} />
        </div>
      )}

      {activeTab === "Campos Customizados" && (
        <section>
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-[#14181F]/70">
            Campos customizados do cadastro
          </h2>
          <p className="mb-4 text-xs text-[#14181F]/40">
            Campos que não vêm da XP — crie um agrupador (ex: &quot;Família&quot;), adicione opções e
            classifique os clientes.
          </p>
          <ExtendedFieldsAdmin fields={extendedFields} clients={clients} />
        </section>
      )}
    </div>
  );
}
