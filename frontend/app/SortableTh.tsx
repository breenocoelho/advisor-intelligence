"use client";

export default function SortableTh({
  label,
  sortKey,
  currentSort,
  currentDir,
  onSort,
  align = "left",
}: {
  label: string;
  sortKey: string;
  currentSort: string;
  currentDir: "asc" | "desc";
  onSort: (key: string) => void;
  align?: "left" | "right";
}) {
  const active = currentSort === sortKey;
  return (
    <th className={`px-4 py-3 font-medium ${align === "right" ? "text-right" : "text-left"}`}>
      <button
        onClick={() => onSort(sortKey)}
        className={`inline-flex items-center gap-1 transition ${
          active ? "text-[#14181F]" : "text-[#14181F]/40 hover:text-[#14181F]/70"
        }`}
      >
        {label}
        {active && <span className="text-[10px]">{currentDir === "asc" ? "▲" : "▼"}</span>}
      </button>
    </th>
  );
}
