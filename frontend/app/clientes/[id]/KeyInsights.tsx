export type KeyInsightItem = { text: string; severity: "critical" | "opportunity" | "follow_up"; link_tab: string };

const SEVERITY_CONFIG = {
  critical: { accent: "#B23A48" },
  opportunity: { accent: "#A6790A" },
  follow_up: { accent: "#3E5C76" },
} as const;

export default function KeyInsights({
  items,
  onNavigate,
}: {
  items: KeyInsightItem[];
  onNavigate: (tab: string) => void;
}) {
  if (items.length === 0) return null;

  return (
    <section className="mb-10">
      <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-[#14181F]/70">Key Insights</h2>
      <div className="card divide-y divide-[#14181F]/5">
        {items.map((item, i) => {
          const config = SEVERITY_CONFIG[item.severity];
          return (
            <button
              key={i}
              onClick={() => onNavigate(item.link_tab)}
              className="flex w-full items-start gap-3 p-3 text-left transition hover:bg-[#14181F]/[0.02]"
            >
              <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full" style={{ backgroundColor: config.accent }} />
              <span className="text-sm text-[#14181F]/80">{item.text}</span>
            </button>
          );
        })}
      </div>
    </section>
  );
}
