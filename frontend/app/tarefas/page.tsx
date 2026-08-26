import { auth } from "@clerk/nextjs/server";
import Link from "next/link";
import TaskStatusButton from "./TaskStatusButton";

type Task = {
  id: string;
  client_id: string;
  client_name: string | null;
  description: string;
  due_date: string | null;
  status: string;
  severity: "critical" | "opportunity" | "follow_up" | null;
};

const SEVERITY_ACCENT: Record<string, string> = {
  critical: "#B23A48",
  opportunity: "#A6790A",
  follow_up: "#3E5C76",
};

async function getTasks(): Promise<Task[]> {
  const { getToken } = await auth();
  const token = await getToken();

  const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/tasks/`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    cache: "no-store",
  });

  if (!res.ok) return [];
  return res.json();
}

export default async function TarefasPage() {
  const tasks = await getTasks();
  const pending = tasks.filter((t) => t.status === "pending");
  const done = tasks.filter((t) => t.status === "done");

  return (
    <main className="mx-auto max-w-3xl px-6 py-10 sm:py-14">
      <header className="mb-8 border-b border-[#14181F]/10 pb-6">
        <p className="text-sm text-[#14181F]/50">Follow-ups</p>
        <h1 className="font-display text-4xl font-semibold tracking-tight">Tarefas</h1>
      </header>

      <section className="mb-10">
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-[#14181F]/70">
          Pendentes ({pending.length})
        </h2>
        {pending.length === 0 ? (
          <p className="text-sm text-[#14181F]/50">Nenhuma tarefa pendente.</p>
        ) : (
          <div className="space-y-2">
            {pending.map((task) => (
              <div
                key={task.id}
                className="flex items-start justify-between gap-4 rounded-lg border border-[#14181F]/10 bg-white p-3"
                style={{
                  borderLeft: `3px solid ${task.severity ? SEVERITY_ACCENT[task.severity] : "#14181F33"}`,
                }}
              >
                <div className="min-w-0">
                  <Link href={`/clientes/${task.client_id}`} className="text-sm font-medium hover:underline">
                    {task.client_name ?? "Cliente"}
                  </Link>
                  <p className="mt-1 text-sm text-[#14181F]/70">{task.description}</p>
                  {task.due_date && (
                    <p className="mt-1 font-mono text-xs tabular-nums text-[#14181F]/40">
                      até {new Date(task.due_date).toLocaleDateString("pt-BR")}
                    </p>
                  )}
                </div>
                <TaskStatusButton taskId={task.id} status={task.status} />
              </div>
            ))}
          </div>
        )}
      </section>

      {done.length > 0 && (
        <section>
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-[#14181F]/70">
            Concluídas ({done.length})
          </h2>
          <div className="space-y-2">
            {done.map((task) => (
              <div
                key={task.id}
                className="flex items-start justify-between gap-4 rounded-lg border border-[#14181F]/10 bg-white p-3 opacity-60"
              >
                <div className="min-w-0">
                  <p className="text-sm font-medium">{task.client_name ?? "Cliente"}</p>
                  <p className="mt-1 text-sm text-[#14181F]/70 line-through">{task.description}</p>
                </div>
                <TaskStatusButton taskId={task.id} status={task.status} />
              </div>
            ))}
          </div>
        </section>
      )}
    </main>
  );
}