export default function OverridableField({
  fieldKey,
  originalDisplay,
  overrides,
}: {
  fieldKey: string;
  originalDisplay: string;
  overrides: Record<string, string>;
}) {
  const override = overrides[fieldKey];
  if (!override) {
    return <p className="mt-1 text-sm">{originalDisplay}</p>;
  }

  return (
    <p className="mt-1 flex items-center gap-1.5 text-sm font-medium" style={{ color: "#B23A48" }}>
      <span aria-hidden>⚠</span>
      {override}
      <span className="text-xs font-normal text-[#14181F]/40">(XP: {originalDisplay})</span>
    </p>
  );
}
