"use client";

import Link from "next/link";
import { useAuth } from "@clerk/nextjs";
import { useRouter } from "next/navigation";
import { useState } from "react";

type FieldOverride = {
  client_id: string;
  client_name: string;
  field_name: string;
  override_value: string;
  created_at: string | null;
};

function formatDate(value: string | null): string {
  if (!value) return "—";
  return new Date(value).toLocaleDateString("pt-BR");
}

export default function FieldOverridesAdmin({ overrides }: { overrides: FieldOverride[] }) {
  const { getToken } = useAuth();
  const router = useRouter();
  const [pendingKey, setPendingKey] = useState<string | null>(null);

  async function remove(clientId: string, fieldName: string) {
    const key = `${clientId}:${fieldName}`;
    setPendingKey(key);
    try {
      const token = await getToken();
      await fetch(`${process.env.NEXT_PUBLIC_API_URL}/clients/${clientId}/field-overrides/${fieldName}`, {
        method: "DELETE",
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      router.refresh();
    } finally {
      setPendingKey(null);
    }
  }

  if (overrides.length === 0) {
    return (
      <p className="text-sm text-[#14181F]/50">
        Nenhum campo cadastral sobrescrito. Overrides são criados a partir do Client 360.
      </p>
    );
  }

  return (
    <div className="overflow-hidden card">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-[#14181F]/10 text-left text-xs uppercase tracking-wide text-[#14181F]/40">
            <th className="px-4 py-3 font-medium">Cliente</th>
            <th className="px-4 py-3 font-medium">Campo</th>
            <th className="px-4 py-3 font-medium">Valor sobrescrito</th>
            <th className="px-4 py-3 font-medium">Desde</th>
            <th className="px-4 py-3" />
          </tr>
        </thead>
        <tbody>
          {overrides.map((o) => {
            const key = `${o.client_id}:${o.field_name}`;
            return (
              <tr key={key} className="border-b border-[#14181F]/5 last:border-0">
                <td className="px-4 py-3">
                  <Link href={`/clientes/${o.client_id}`} className="font-medium hover:underline">
                    {o.client_name}
                  </Link>
                </td>
                <td className="px-4 py-3 font-mono text-xs text-[#14181F]/70">{o.field_name}</td>
                <td className="px-4 py-3" style={{ color: "#B23A48" }}>
                  ⚠ {o.override_value}
                </td>
                <td className="px-4 py-3 font-mono text-xs tabular-nums text-[#14181F]/40">
                  {formatDate(o.created_at)}
                </td>
                <td className="px-4 py-3 text-right">
                  <button
                    onClick={() => remove(o.client_id, o.field_name)}
                    disabled={pendingKey === key}
                    className="text-xs font-medium text-[#14181F]/40 hover:text-[#14181F]/70 disabled:opacity-40"
                  >
                    {pendingKey === key ? "Removendo..." : "Remover override"}
                  </button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
