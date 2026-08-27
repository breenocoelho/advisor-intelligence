type AuditLogItem = {
  id: string;
  client_id: string | null;
  client_name: string | null;
  action_type: string;
  summary: string;
  created_at: string | null;
};

const ACTION_LABELS: Record<string, string> = {
  task_created: "Tarefa criada",
  interaction_created: "Interação registrada",
  interaction_updated: "Interação editada",
  interaction_deleted: "Interação removida",
  contact_registered: "Contato registrado",
  threshold_rule_saved: "Threshold definido",
  threshold_rule_deleted: "Threshold removido",
  field_override_set: "Override de cadastro definido",
  field_override_removed: "Override de cadastro removido",
  extended_field_created: "Campo customizado criado",
  extended_field_deleted: "Campo customizado removido",
  extended_field_option_created: "Opção de campo criada",
  extended_field_option_deleted: "Opção de campo removida",
  extended_field_assigned: "Classificação atribuída",
  extended_field_unassigned: "Classificação removida",
};

function formatDateTime(value: string | null): string {
  if (!value) return "—";
  return new Date(value).toLocaleString("pt-BR", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
}

export default function AuditLogList({ logs }: { logs: AuditLogItem[] }) {
  if (logs.length === 0) {
    return <p className="text-sm text-[#14181F]/50">Nenhuma atividade registrada ainda.</p>;
  }

  return (
    <ol className="space-y-2">
      {logs.map((log) => (
        <li key={log.id} className="card flex items-start justify-between gap-4 p-3">
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span className="rounded-full bg-[#14181F]/5 px-2 py-0.5 text-xs font-medium text-[#14181F]/60">
                {ACTION_LABELS[log.action_type] ?? log.action_type}
              </span>
              {log.client_name && <span className="text-xs text-[#14181F]/40">{log.client_name}</span>}
            </div>
            <p className="mt-1 text-sm text-[#14181F]/70">{log.summary}</p>
          </div>
          <span className="shrink-0 font-mono text-xs tabular-nums text-[#14181F]/40">
            {formatDateTime(log.created_at)}
          </span>
        </li>
      ))}
    </ol>
  );
}
