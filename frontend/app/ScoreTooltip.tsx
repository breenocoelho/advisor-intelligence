export type ScoreBreakdownItem = { direction: "up" | "down"; label: string; detail: string };

function scoreColor(score: number): string {
  if (score >= 80) return "#3F7D5B";
  if (score >= 60) return "#A6790A";
  return "#B23A48";
}

export default function ScoreTooltip({
  score,
  band,
  breakdown,
  label,
}: {
  score: number;
  band?: string | null;
  breakdown: ScoreBreakdownItem[];
  label?: string;
}) {
  return (
    <span className="group relative inline-flex items-center gap-1.5 rounded-full bg-[#14181F]/5 px-2.5 py-1 align-middle">
      <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: scoreColor(score) }} />
      <span className="font-mono text-xs font-semibold tabular-nums">{score}</span>
      {label && <span className="text-xs text-[#14181F]/50">{label}</span>}

      {breakdown.length > 0 && (
        <div className="pointer-events-none absolute left-1/2 top-full z-20 mt-2 hidden w-64 -translate-x-1/2 rounded-lg border border-[#14181F]/10 bg-white p-3 text-left normal-case shadow-lg group-hover:block">
          {band && (
            <p className="mb-2 text-xs font-semibold uppercase tracking-wide" style={{ color: scoreColor(score) }}>
              {band}
            </p>
          )}
          <ul className="space-y-1.5">
            {breakdown.map((item, i) => (
              <li key={i} className="flex items-start gap-1.5 text-xs">
                <span
                  className="mt-0.5 font-semibold"
                  style={{ color: item.direction === "up" ? "#3F7D5B" : "#B23A48" }}
                >
                  {item.direction === "up" ? "▲" : "▼"}
                </span>
                <span>
                  <span className="font-medium text-[#14181F]">{item.label}</span>
                  <span className="block text-[#14181F]/50">{item.detail}</span>
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </span>
  );
}
