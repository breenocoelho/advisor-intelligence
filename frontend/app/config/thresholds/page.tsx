import { auth } from "@clerk/nextjs/server";
import ConfigTabs from "./ConfigTabs";

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

async function authHeaders(): Promise<HeadersInit> {
  const { getToken } = await auth();
  const token = await getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function getThresholdRules(): Promise<ThresholdRulesResponse> {
  const headers = await authHeaders();
  const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/threshold-rules/`, { headers, cache: "no-store" });
  if (!res.ok) return { defaults: {}, rules: [] };
  return res.json();
}

async function getAuditLogs(): Promise<AuditLogItem[]> {
  const headers = await authHeaders();
  const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/config/audit-logs?limit=100`, { headers, cache: "no-store" });
  if (!res.ok) return [];
  return res.json();
}

async function getFieldOverrides(): Promise<FieldOverride[]> {
  const headers = await authHeaders();
  const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/config/field-overrides`, { headers, cache: "no-store" });
  if (!res.ok) return [];
  return res.json();
}

async function getExtendedFields(): Promise<FieldDefinition[]> {
  const headers = await authHeaders();
  const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/config/extended-fields`, { headers, cache: "no-store" });
  if (!res.ok) return [];
  return res.json();
}

async function getClients(): Promise<Client[]> {
  const headers = await authHeaders();
  const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/clients/`, { headers, cache: "no-store" });
  if (!res.ok) return [];
  return res.json();
}

export default async function ConfigPage() {
  const [{ defaults, rules }, auditLogs, fieldOverrides, extendedFields, clients] = await Promise.all([
    getThresholdRules(),
    getAuditLogs(),
    getFieldOverrides(),
    getExtendedFields(),
    getClients(),
  ]);

  return (
    <main className="mx-auto max-w-3xl px-6 py-10 sm:py-14">
      <header className="mb-8 border-b border-[#14181F]/10 pb-6">
        <p className="text-sm text-[#14181F]/50">Administração</p>
        <h1 className="font-display text-4xl font-semibold tracking-tight">Config</h1>
        <p className="mt-2 text-sm text-[#14181F]/60">
          Motor de alertas, atividade do escritório, overrides de cadastro e campos customizados.
        </p>
      </header>

      <ConfigTabs
        defaults={defaults}
        rules={rules}
        auditLogs={auditLogs}
        fieldOverrides={fieldOverrides}
        extendedFields={extendedFields}
        clients={clients.map((c: Client) => ({ id: c.id, name: c.name }))}
      />
    </main>
  );
}
