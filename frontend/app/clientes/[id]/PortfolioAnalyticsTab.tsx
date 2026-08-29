"use client";

import PositionsComparison from "./PositionsComparison";
import AnalyticsTab from "./AnalyticsTab";
import PerformanceAttribution from "./PerformanceAttribution";
import BenchmarkComparison from "./BenchmarkComparison";

type TopPosition = { asset_name: string; market_value: number; pct_of_aum: number };
type IssuerExposure = { issuer: string; value: number; pct_of_aum: number };

function formatCurrency(value: number): string {
  return value.toLocaleString("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 });
}

export default function PortfolioAnalyticsTab({
  clientId,
  positionDates,
  topPositions,
  issuerBreakdown,
}: {
  clientId: string;
  positionDates: string[];
  topPositions: TopPosition[];
  issuerBreakdown: IssuerExposure[];
}) {
  return (
    <div className="space-y-10">
      {(topPositions.length > 0 || issuerBreakdown.length > 0) && (
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
          {topPositions.length > 0 && (
            <section>
              <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-[#14181F]/70">
                Top Posições
              </h2>
              <div className="card divide-y divide-[#14181F]/5">
                {topPositions.map((p, i) => (
                  <div key={i} className="flex items-center justify-between p-3">
                    <span className="text-sm">{p.asset_name}</span>
                    <span className="font-mono text-sm tabular-nums text-[#14181F]/70">
                      {formatCurrency(p.market_value)} ({p.pct_of_aum.toFixed(1)}%)
                    </span>
                  </div>
                ))}
              </div>
            </section>
          )}
          {issuerBreakdown.length > 0 && (
            <section>
              <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-[#14181F]/70">
                Top Emissores
              </h2>
              <div className="card divide-y divide-[#14181F]/5">
                {issuerBreakdown.map((e, i) => (
                  <div key={i} className="flex items-center justify-between p-3">
                    <span className="text-sm">{e.issuer}</span>
                    <span className="font-mono text-sm tabular-nums text-[#14181F]/70">
                      {formatCurrency(e.value)} ({e.pct_of_aum.toFixed(1)}%)
                    </span>
                  </div>
                ))}
              </div>
            </section>
          )}
        </div>
      )}

      <PositionsComparison clientId={clientId} availableDates={positionDates} />
      <AnalyticsTab clientId={clientId} />
      {positionDates.length >= 2 && (
        <PerformanceAttribution clientId={clientId} availableDates={positionDates} />
      )}
      {positionDates.length > 0 && (
        <BenchmarkComparison clientId={clientId} latestDate={positionDates[positionDates.length - 1]} />
      )}
    </div>
  );
}
