"use client";

import { useMemo, useState } from "react";
import Link from "next/link";

type Client = {
  id: string;
  xp_client_id: string | null;
  name: string;
  aum: number | null;
  suitability: string | null;
  advisor_name: string | null;
  priority_score: number;
};

function formatCurrency(value: number | null): string {
  if (value === null) return "—";
  return value.toLocaleString("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 });
}

function formatSuitability(value: string | null): string {
  if (!value) return "—";
  return value.charAt(0) + value.slice(1).toLowerCase();
}

export default function ClientesTable({ clients }: { clients: Client[] }) {
  const [search, setSearch] = useState("");
  const [advisorFilter, setAdvisorFilter] = useState("all");

  const advisors = useMemo(() => {
    const set = new Set(clients.map((c) => c.advisor_name).filter(Boolean) as string[]);
    return Array.from(set).sort();
  }, [clients]);

  const filtered = clients.filter((c) => {
    const matchesSearch =
      search.trim() === "" ||
      c.name.toLowerCase().includes(search.toLowerCase()) ||
      (c.xp_client_id ?? "").includes(search);
    const matchesAdvisor = advisorFilter === "all" || c.advisor_name === advisorFilter;
    return matchesSearch && matchesAdvisor;
  });

  return (
    <div>
      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center">
        <input
          type="text"
          placeholder="Buscar por nome ou código..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full rounded-md border border-[#14181F]/15 bg-white px-3 py-2 text-sm placeholder:text-[#14181F]/30 focus:outline-none focus:ring-2 focus:ring-[#14181F]/20 sm:max-w-xs"
        />
        <select
          value={advisorFilter}
          onChange={(e) => setAdvisorFilter(e.target.value)}
          className="rounded-md border border-[#14181F]/15 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#14181F]/20"
        >
          <option value="all">Todos os assessores</option>
          {advisors.map((a) => (
            <option key={a} value={a}>
              {a}
            </option>
          ))}
        </select>
      </div>

      {filtered.length === 0 ? (
        <div className="rounded-lg border border-dashed border-[#14181F]/15 py-16 text-center">
          <p className="text-lg font-medium">Nenhum cliente encontrado.</p>
        </div>
      ) : (
        <div className="overflow-hidden rounded-lg border border-[#14181F]/10 bg-white">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[#14181F]/10 text-left text-xs uppercase tracking-wide text-[#14181F]/40">
                <th className="px-4 py-3 font-medium">Cliente</th>
                <th className="px-4 py-3 font-medium">Assessor</th>
                <th className="px-4 py-3 font-medium">Perfil</th>
                <th className="px-4 py-3 text-right font-medium">AUM</th>
                <th className="px-4 py-3 text-right font-medium">Prioridade</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((client) => (
                <tr
                  key={client.id}
                  className="border-b border-[#14181F]/5 last:border-0 hover:bg-[#14181F]/[0.02]"
                >
                  <td className="px-4 py-3">
                    <Link
                      href={`/clientes/${client.id}`}
                      className="font-medium hover:underline underline-offset-2"
                    >
                      {client.name}
                    </Link>
                    <p className="text-xs text-[#14181F]/40">#{client.xp_client_id}</p>
                  </td>
                  <td className="px-4 py-3 text-[#14181F]/70">{client.advisor_name ?? "—"}</td>
                  <td className="px-4 py-3 text-[#14181F]/70">
                    {formatSuitability(client.suitability)}
                  </td>
                  <td className="px-4 py-3 text-right font-mono tabular-nums">
                    {formatCurrency(client.aum)}
                  </td>
                  <td className="px-4 py-3 text-right">
                    {client.priority_score > 0 ? (
                      <span className="inline-flex items-center rounded-full bg-[#B23A48]/10 px-2 py-0.5 font-mono text-xs font-medium tabular-nums text-[#B23A48]">
                        {client.priority_score}
                      </span>
                    ) : (
                      <span className="text-[#14181F]/25">—</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}