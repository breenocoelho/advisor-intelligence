"use client";

import { useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { useRouter } from "next/navigation";

export default function TaskStatusButton({ taskId, status }: { taskId: string; status: string }) {
  const { getToken } = useAuth();
  const router = useRouter();
  const [pending, setPending] = useState(false);

  async function toggle() {
    setPending(true);
    try {
      const token = await getToken();
      const newStatus = status === "pending" ? "done" : "pending";
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/tasks/${taskId}?new_status=${newStatus}`,
        {
          method: "PATCH",
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
      onClick={toggle}
      disabled={pending}
      className="shrink-0 rounded-md border border-[#14181F]/15 px-3 py-1.5 text-xs font-medium text-[#14181F]/70 transition hover:bg-[#14181F]/5 disabled:opacity-40"
    >
      {status === "pending" ? "Marcar concluída" : "Reabrir"}
    </button>
  );
}