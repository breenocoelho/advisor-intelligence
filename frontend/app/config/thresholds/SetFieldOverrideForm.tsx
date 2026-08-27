"use client";

import { useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { useRouter } from "next/navigation";

type Client = { id: string; name: string };

const OVERRIDABLE_FIELDS: Record<string, string> = {
  marital_status: "Estado civil",
  activity: "Atividade",
  person_type: "Tipo de pessoa (F/J)",
  suitability: "Perfil (suitability)",
  income_value: "Renda declarada",
  declared_wealth_total: "Patrimônio declarado",
  qualified_investor: "Investidor qualificado",
  professional_investor: "Investidor profissional",
};

export default function SetFieldOverrideForm({ clients }: { clients: Client[] }) {
  const { getToken } = useAuth();
  const router = useRouter();
  const [clientId, setClientId] = useState(clients[0]?.id ?? "");
  const [fieldName, setFieldName] = useState(Object.keys(OVERRIDABLE_FIELDS)[0]);
  const [value, setValue] = useState("");
  const [pending, setPending] = useState(false);

  async function submit() {
    if (!clientId || !fieldName || !value.trim()) return;
    setPending(true);
    try {
      const token = await getToken();
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/clients/${clientId}/field-overrides/${fieldName}`,
        {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: JSON.stringify({ value: value.trim() }),
        }
      );
      if (res.ok) {
        setValue("");
        router.refresh();
      }
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="rounded-lg border border-dashed border-[#14181F]/20 bg-white p-4">
      <p className="text-sm font-medium">Novo override de cadastro</p>
      <p className="mt-1 text-xs text-[#14181F]/50">
        Use quando o cadastro da XP estiver desatualizado — o campo passa a exibir esse valor no Client 360,
        sinalizado em vermelho.
      </p>
      <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-4">
        <select
          value={clientId}
          onChange={(e) => setClientId(e.target.value)}
          className="rounded-md border border-[#14181F]/15 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#14181F]/20"
        >
          {clients.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
        <select
          value={fieldName}
          onChange={(e) => setFieldName(e.target.value)}
          className="rounded-md border border-[#14181F]/15 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#14181F]/20"
        >
          {Object.entries(OVERRIDABLE_FIELDS).map(([key, label]) => (
            <option key={key} value={key}>
              {label}
            </option>
          ))}
        </select>
        <input
          type="text"
          placeholder="Novo valor"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          className="rounded-md border border-[#14181F]/15 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#14181F]/20"
        />
        <button
          onClick={submit}
          disabled={pending || !value.trim()}
          className="rounded-md bg-[#14181F] px-3 py-2 text-sm font-medium text-white transition hover:opacity-90 disabled:opacity-40"
        >
          {pending ? "Salvando..." : "Salvar override"}
        </button>
      </div>
    </div>
  );
}
