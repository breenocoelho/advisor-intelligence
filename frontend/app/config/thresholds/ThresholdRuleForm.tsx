"use client";

import { useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { useRouter } from "next/navigation";

export default function ThresholdRuleForm({ signalKeys }: { signalKeys: string[] }) {
  const { getToken } = useAuth();
  const router = useRouter();
  const [signalKey, setSignalKey] = useState(signalKeys[0] ?? "");
  const [profile, setProfile] = useState("");
  const [value, setValue] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    setPending(true);
    setError(null);
    try {
      const token = await getToken();
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/threshold-rules/`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          signal_key: signalKey,
          suitability_profile: profile.trim() || null,
          value: Number(value),
        }),
      });
      if (res.ok) {
        setValue("");
        setProfile("");
        router.refresh();
      } else {
        setError("Não foi possível salvar. Confira o valor.");
      }
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="rounded-lg border border-dashed border-[#14181F]/20 bg-white p-4">
      <p className="text-sm font-medium">Novo override</p>
      <p className="mt-1 text-xs text-[#14181F]/50">
        Deixe o perfil em branco para definir o default da organização (aplica a
        clientes sem override específico de perfil).
      </p>
      <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-4">
        <select
          value={signalKey}
          onChange={(e) => setSignalKey(e.target.value)}
          className="rounded-md border border-[#14181F]/15 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#14181F]/20"
        >
          {signalKeys.map((k) => (
            <option key={k} value={k}>
              {k}
            </option>
          ))}
        </select>
        <input
          type="text"
          placeholder="Perfil (ex: MODERADO) — opcional"
          value={profile}
          onChange={(e) => setProfile(e.target.value)}
          className="rounded-md border border-[#14181F]/15 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#14181F]/20"
        />
        <input
          type="number"
          step="any"
          placeholder="Valor"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          className="rounded-md border border-[#14181F]/15 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#14181F]/20"
        />
        <button
          onClick={submit}
          disabled={pending || !value}
          className="rounded-md bg-[#14181F] px-3 py-2 text-sm font-medium text-white transition hover:opacity-90 disabled:opacity-40"
        >
          {pending ? "Salvando..." : "Salvar override"}
        </button>
      </div>
      {error && <p className="mt-2 text-xs text-[#B23A48]">{error}</p>}
    </div>
  );
}
