"use client";

import { useMemo, useState, type ReactNode } from "react";

/**
 * Reusable sortable / searchable / paginated table — replaces the legacy
 * Bootstrap-Table usage. Generic over the row type.
 *
 * Contract (the template VAI/CAS will follow):
 *  - `columns`: declarative column defs. `accessor` returns the raw value used
 *    for sorting + default rendering; `render` optionally customizes the cell.
 *  - `searchable`: when a column is searchable, its accessor value is matched
 *    (case-insensitive substring) against the search box.
 *  - Sorting and pagination are handled internally; the parent just passes data.
 */
export interface Column<Row> {
  id: string;
  header: string;
  accessor: (row: Row) => string | number | boolean | null;
  /** Custom cell renderer; defaults to the accessor value. */
  render?: (row: Row) => ReactNode;
  /** Include this column's value in the search filter. Default false. */
  searchable?: boolean;
  /** Allow sorting by this column. Default true. */
  sortable?: boolean;
  align?: "left" | "right" | "center";
}

export interface DataTableProps<Row> {
  rows: Row[];
  columns: Column<Row>[];
  rowKey: (row: Row) => string | number;
  pageSize?: number;
  searchPlaceholder?: string;
  initialSort?: { columnId: string; dir: "asc" | "desc" };
}

function compare(a: string | number | boolean | null, b: string | number | boolean | null): number {
  if (a === null) return 1;
  if (b === null) return -1;
  if (typeof a === "number" && typeof b === "number") return a - b;
  return String(a).localeCompare(String(b));
}

export default function DataTable<Row>({
  rows,
  columns,
  rowKey,
  pageSize = 25,
  searchPlaceholder = "Search…",
  initialSort,
}: DataTableProps<Row>) {
  const [query, setQuery] = useState("");
  const [sort, setSort] = useState<{ columnId: string; dir: "asc" | "desc" } | null>(
    initialSort ?? null,
  );
  const [page, setPage] = useState(0);

  const searchCols = useMemo(() => columns.filter((c) => c.searchable), [columns]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return rows;
    return rows.filter((row) =>
      searchCols.some((c) => String(c.accessor(row) ?? "").toLowerCase().includes(q)),
    );
  }, [rows, query, searchCols]);

  const sorted = useMemo(() => {
    if (!sort) return filtered;
    const col = columns.find((c) => c.id === sort.columnId);
    if (!col) return filtered;
    const dir = sort.dir === "asc" ? 1 : -1;
    return [...filtered].sort((a, b) => dir * compare(col.accessor(a), col.accessor(b)));
  }, [filtered, sort, columns]);

  const pageCount = Math.max(1, Math.ceil(sorted.length / pageSize));
  const safePage = Math.min(page, pageCount - 1);
  const pageRows = sorted.slice(safePage * pageSize, safePage * pageSize + pageSize);

  function toggleSort(columnId: string) {
    setPage(0);
    setSort((prev) =>
      prev?.columnId === columnId
        ? { columnId, dir: prev.dir === "asc" ? "desc" : "asc" }
        : { columnId, dir: "asc" },
    );
  }

  const alignClass = (align?: Column<Row>["align"]) =>
    align === "right" ? "text-right" : align === "center" ? "text-center" : "text-left";

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <input
          type="search"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setPage(0);
          }}
          placeholder={searchPlaceholder}
          className="w-full max-w-xs rounded-md border border-rule bg-paper px-3 py-1.5 text-sm text-ink outline-none transition-colors placeholder:text-ink-soft/60 focus:border-teal focus:ring-1 focus:ring-teal/30"
        />
        <span className="shrink-0 font-mono text-[11px] uppercase tracking-[0.12em] tabular-nums text-ink-soft">
          {sorted.length} rows
        </span>
      </div>

      <div className="overflow-x-auto rounded-lg border border-rule">
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="border-b border-rule bg-panel">
              {columns.map((c) => {
                const sortable = c.sortable !== false;
                const active = sort?.columnId === c.id;
                return (
                  <th
                    key={c.id}
                    onClick={sortable ? () => toggleSort(c.id) : undefined}
                    title={sortable ? `Sort by ${c.header.replace(/\n/g, " ")}` : undefined}
                    aria-sort={
                      active ? (sort!.dir === "asc" ? "ascending" : "descending") : undefined
                    }
                    // `whitespace-pre-line` lets a header carry a "\n" and wrap
                    // onto two lines, so full names ("Value-Added Retention")
                    // fit without stretching the column.
                    className={`whitespace-pre-line px-3 py-2.5 align-bottom font-mono text-[11px] uppercase tracking-[0.1em] ${alignClass(c.align)} ${
                      active ? "text-teal" : "text-ink-soft"
                    } ${sortable ? "group cursor-pointer select-none transition-colors hover:text-ink" : ""}`}
                  >
                    {c.header}
                    {active ? (
                      <span className="ml-1 text-teal">{sort!.dir === "asc" ? "▲" : "▼"}</span>
                    ) : (
                      sortable && (
                        // Persistent low-contrast affordance so it's obvious a
                        // column can be sorted before you hover it.
                        <span
                          aria-hidden
                          className="ml-1 text-ink-soft/35 transition-colors group-hover:text-ink-soft"
                        >
                          ↕
                        </span>
                      )
                    )}
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody className="divide-y divide-rule">
            {pageRows.map((row) => (
              <tr key={rowKey(row)} className="transition-colors hover:bg-panel">
                {columns.map((c) => {
                  const numeric = c.align === "right";
                  return (
                    <td
                      key={c.id}
                      className={`px-3 py-2 text-ink ${alignClass(c.align)} ${
                        numeric ? "tabular-nums" : ""
                      }`}
                    >
                      {c.render ? c.render(row) : String(c.accessor(row) ?? "—")}
                    </td>
                  );
                })}
              </tr>
            ))}
            {pageRows.length === 0 && (
              <tr>
                <td
                  colSpan={columns.length}
                  className="px-3 py-8 text-center font-mono text-[11px] uppercase tracking-[0.12em] text-ink-soft"
                >
                  No matches
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {pageCount > 1 && (
        <div className="flex items-center justify-end gap-3 text-sm">
          <button
            onClick={() => setPage((p) => Math.max(0, p - 1))}
            disabled={safePage === 0}
            className="rounded-md border border-rule bg-paper px-3 py-1 font-mono text-[11px] uppercase tracking-[0.12em] text-ink-soft transition-colors hover:border-teal hover:text-ink disabled:opacity-40 disabled:hover:border-rule disabled:hover:text-ink-soft"
          >
            Prev
          </button>
          <span className="font-mono text-[11px] uppercase tracking-[0.12em] tabular-nums text-ink-soft">
            Page {safePage + 1} / {pageCount}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(pageCount - 1, p + 1))}
            disabled={safePage >= pageCount - 1}
            className="rounded-md border border-rule bg-paper px-3 py-1 font-mono text-[11px] uppercase tracking-[0.12em] text-ink-soft transition-colors hover:border-teal hover:text-ink disabled:opacity-40 disabled:hover:border-rule disabled:hover:text-ink-soft"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}
