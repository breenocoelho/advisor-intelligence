"use client";

import PositionsComparison from "./PositionsComparison";
import AnalyticsTab from "./AnalyticsTab";
import PerformanceAttribution from "./PerformanceAttribution";
import BenchmarkComparison from "./BenchmarkComparison";

export default function PortfolioAnalyticsTab({
  clientId,
  positionDates,
}: {
  clientId: string;
  positionDates: string[];
}) {
  return (
    <div className="space-y-10">
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
