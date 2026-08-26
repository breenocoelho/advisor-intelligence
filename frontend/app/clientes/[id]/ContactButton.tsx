"use client";

import { useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { useRouter } from "next/navigation";

export default function ContactButton({ clientId }: { clientId: string }) {
  const { getToken } = useAuth();
  const router = useRouter();
  const [pending, setPending] = useState(false);

  async function registerContact() {
    setPending(true);
    try {
      const token = await getToken();
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/clients/${clientId}/contact`,
        {
          method: "POST",
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        }
      );
      if (res.ok) router.refresh();
    } finally {
      setPending(false);
    }
  }

  return (
    <button
      onClick={registerContact}
      disabled={pending}
      className="rounded-md bg-[#14181F] px-3 py-1.5 text-xs font-medium text-white transition hover:opacity-90 disabled:opacity-40"
    >
      {pending ? "Registrando..." : "Registrar contato agora"}
    </button>
  );
}