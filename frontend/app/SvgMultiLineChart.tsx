type Point = { label: string; value: number };
type Series = { name: string; color: string; points: Point[] };

export default function SvgMultiLineChart({
  series,
  height = 200,
  formatValue,
}: {
  series: Series[];
  height?: number;
  formatValue?: (value: number) => string;
}) {
  const nonEmpty = series.filter((s) => s.points.length > 0);
  if (nonEmpty.length === 0) {
    return <p className="text-sm text-[#14181F]/50">Sem dados suficientes para o período.</p>;
  }

  const width = 640;
  const paddingX = 8;
  const paddingTop = 16;
  const paddingBottom = 28;
  const plotWidth = width - paddingX * 2;
  const plotHeight = height - paddingTop - paddingBottom;

  const maxLen = Math.max(...nonEmpty.map((s) => s.points.length));
  const allValues = nonEmpty.flatMap((s) => s.points.map((p) => p.value));
  const min = Math.min(...allValues, 0);
  const max = Math.max(...allValues);
  const range = max - min || 1;

  const xFor = (i: number) => (maxLen === 1 ? paddingX + plotWidth / 2 : paddingX + (i / (maxLen - 1)) * plotWidth);
  const yFor = (v: number) => paddingTop + plotHeight - ((v - min) / range) * plotHeight;

  const firstLabels = nonEmpty[0].points;

  return (
    <div className="w-full">
      <div className="mb-2 flex flex-wrap gap-3">
        {nonEmpty.map((s) => (
          <span key={s.name} className="flex items-center gap-1.5 text-xs text-[#14181F]/70">
            <span className="h-2 w-2 rounded-full" style={{ backgroundColor: s.color }} />
            {s.name}
          </span>
        ))}
      </div>
      <div className="w-full overflow-x-auto">
        <svg viewBox={`0 0 ${width} ${height}`} className="w-full min-w-[420px]" style={{ height }}>
          {nonEmpty.map((s) => {
            const linePath = s.points
              .map((p, i) => `${i === 0 ? "M" : "L"} ${xFor(i).toFixed(1)} ${yFor(p.value).toFixed(1)}`)
              .join(" ");
            const last = s.points[s.points.length - 1];
            return (
              <g key={s.name}>
                <path d={linePath} fill="none" stroke={s.color} strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" />
                {s.points.map((p, i) => (
                  <circle key={i} cx={xFor(i)} cy={yFor(p.value)} r={2} fill={s.color} />
                ))}
                <text x={xFor(s.points.length - 1)} y={yFor(last.value) - 6} fontSize="10" fontWeight={600} fill={s.color} textAnchor="end">
                  {formatValue ? formatValue(last.value) : last.value.toLocaleString("pt-BR")}
                </text>
              </g>
            );
          })}
          {firstLabels.length > 0 && (
            <>
              <text x={xFor(0)} y={height - 8} fontSize="10" fill="#14181F66" textAnchor="start">
                {firstLabels[0].label}
              </text>
              <text x={xFor(firstLabels.length - 1)} y={height - 8} fontSize="10" fill="#14181F66" textAnchor="end">
                {firstLabels[firstLabels.length - 1].label}
              </text>
            </>
          )}
        </svg>
      </div>
    </div>
  );
}
