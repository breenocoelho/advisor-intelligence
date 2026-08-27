type Point = { label: string; value: number };

export default function SvgLineChart({
  points,
  color = "#14181F",
  height = 160,
  formatValue,
}: {
  points: Point[];
  color?: string;
  height?: number;
  formatValue?: (value: number) => string;
}) {
  if (points.length === 0) {
    return <p className="text-sm text-[#14181F]/50">Sem dados suficientes para o período.</p>;
  }

  const width = 640;
  const paddingX = 8;
  const paddingTop = 24;
  const paddingBottom = 28;
  const plotWidth = width - paddingX * 2;
  const plotHeight = height - paddingTop - paddingBottom;

  const values = points.map((p) => p.value);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;

  const xFor = (i: number) => (points.length === 1 ? paddingX + plotWidth / 2 : paddingX + (i / (points.length - 1)) * plotWidth);
  const yFor = (v: number) => paddingTop + plotHeight - ((v - min) / range) * plotHeight;

  const linePath = points.map((p, i) => `${i === 0 ? "M" : "L"} ${xFor(i).toFixed(1)} ${yFor(p.value).toFixed(1)}`).join(" ");
  const areaPath = `${linePath} L ${xFor(points.length - 1).toFixed(1)} ${(paddingTop + plotHeight).toFixed(1)} L ${xFor(0).toFixed(1)} ${(paddingTop + plotHeight).toFixed(1)} Z`;

  const last = points[points.length - 1];
  const first = points[0];
  const trendUp = last.value >= first.value;
  const trendColor = points.length > 1 ? (trendUp ? "#3F7D5B" : "#B23A48") : color;

  return (
    <div className="w-full overflow-x-auto">
      <svg viewBox={`0 0 ${width} ${height}`} className="w-full min-w-[420px]" style={{ height }}>
        <path d={areaPath} fill={trendColor} opacity={0.08} />
        <path d={linePath} fill="none" stroke={trendColor} strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" />
        {points.map((p, i) => (
          <circle key={i} cx={xFor(i)} cy={yFor(p.value)} r={2.5} fill={trendColor} />
        ))}
        {/* rotulo do primeiro e ultimo ponto */}
        <text x={xFor(0)} y={height - 8} fontSize="10" fill="#14181F66" textAnchor="start">
          {first.label}
        </text>
        <text x={xFor(points.length - 1)} y={height - 8} fontSize="10" fill="#14181F66" textAnchor="end">
          {last.label}
        </text>
        <text x={xFor(points.length - 1)} y={yFor(last.value) - 8} fontSize="11" fontWeight={600} fill={trendColor} textAnchor="end">
          {formatValue ? formatValue(last.value) : last.value.toLocaleString("pt-BR")}
        </text>
      </svg>
    </div>
  );
}
