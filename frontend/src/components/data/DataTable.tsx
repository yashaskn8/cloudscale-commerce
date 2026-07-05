import React, { useState, useMemo } from "react";
import { cn } from "@/lib/utils";
import {
  ArrowUpDown, ArrowUp, ArrowDown, ChevronLeft, ChevronRight,
  Download, Columns, Check,
} from "lucide-react";
import { SearchBox } from "../ui/SearchBox";
import { EmptyState } from "../ui/EmptyState";
import { Skeleton } from "../ui/Skeleton";
import { Button } from "../ui/Button";
import { Dropdown } from "../ui/Dropdown";

// ─── Types ───────────────────────────────────────────────────────────
export interface DataColumn<T> {
  id: string;
  header: string;
  accessor: (row: T) => React.ReactNode;
  sortAccessor?: (row: T) => string | number;
  searchable?: boolean;
  hidden?: boolean;
  sticky?: boolean;
  width?: string;
  align?: "left" | "center" | "right";
}

type SortDir = "asc" | "desc" | null;

interface DataTableProps<T> {
  columns: DataColumn<T>[];
  data: T[];
  loading?: boolean;
  pageSize?: number;
  selectable?: boolean;
  onSelectionChange?: (rows: T[]) => void;
  bulkActions?: { label: string; icon?: React.ReactNode; onClick: (rows: T[]) => void; danger?: boolean }[];
  exportFilename?: string;
  getRowId?: (row: T, index?: number) => string;
  stickyHeader?: boolean;
  emptyTitle?: string;
  emptyDescription?: string;
  className?: string;
}

// ─── Component ───────────────────────────────────────────────────────
export function DataTable<T>({
  columns: allColumns,
  data,
  loading,
  pageSize: defaultPageSize = 10,
  selectable = false,
  onSelectionChange,
  bulkActions,
  exportFilename = "export",
  getRowId = (_: T, i?: number) => String(i ?? 0),
  stickyHeader = true,
  emptyTitle,
  emptyDescription,
  className,
}: DataTableProps<T>) {
  // State
  const [search, setSearch] = useState("");
  const [sortCol, setSortCol] = useState<string | null>(null);
  const [sortDir, setSortDir] = useState<SortDir>(null);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(defaultPageSize);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [hiddenCols, setHiddenCols] = useState<Set<string>>(() =>
    new Set(allColumns.filter((c) => c.hidden).map((c) => c.id))
  );

  const visibleColumns = useMemo(
    () => allColumns.filter((c) => !hiddenCols.has(c.id)),
    [allColumns, hiddenCols]
  );

  // Search
  const searchableIds = useMemo(
    () => allColumns.filter((c) => c.searchable !== false).map((c) => c.id),
    [allColumns]
  );

  const filtered = useMemo(() => {
    if (!search) return data;
    const q = search.toLowerCase();
    return data.filter((row) =>
      searchableIds.some((id) => {
        const col = allColumns.find((c) => c.id === id);
        if (!col) return false;
        const val = col.accessor(row);
        return String(val).toLowerCase().includes(q);
      })
    );
  }, [data, search, searchableIds, allColumns]);

  // Sort
  const sorted = useMemo(() => {
    if (!sortCol || !sortDir) return filtered;
    const col = allColumns.find((c) => c.id === sortCol);
    if (!col) return filtered;
    const accessor = col.sortAccessor || col.accessor;
    return [...filtered].sort((a, b) => {
      const av = accessor(a);
      const bv = accessor(b);
      const cmp = String(av).localeCompare(String(bv), undefined, { numeric: true });
      return sortDir === "asc" ? cmp : -cmp;
    });
  }, [filtered, sortCol, sortDir, allColumns]);

  // Pagination
  const totalPages = Math.max(1, Math.ceil(sorted.length / pageSize));
  const safePage = Math.min(page, totalPages);
  const paged = sorted.slice((safePage - 1) * pageSize, safePage * pageSize);

  // Selection
  const allSelected = paged.length > 0 && paged.every((_, i) => selected.has(getRowId(_, i + (safePage - 1) * pageSize)));

  const toggleAll = () => {
    const ids = paged.map((r, i) => getRowId(r, i + (safePage - 1) * pageSize));
    if (allSelected) {
      const next = new Set(selected);
      ids.forEach((id) => next.delete(id));
      setSelected(next);
    } else {
      setSelected(new Set([...selected, ...ids]));
    }
  };

  const toggleRow = (id: string) => {
    const next = new Set(selected);
    next.has(id) ? next.delete(id) : next.add(id);
    setSelected(next);
  };

  // Notify parent
  React.useEffect(() => {
    if (onSelectionChange) {
      const selectedRows = data.filter((r, i) => selected.has(getRowId(r, i)));
      onSelectionChange(selectedRows);
    }
  }, [selected]);

  // Sort handler
  const handleSort = (colId: string) => {
    if (sortCol === colId) {
      setSortDir(sortDir === "asc" ? "desc" : sortDir === "desc" ? null : "asc");
      if (sortDir === "desc") setSortCol(null);
    } else {
      setSortCol(colId);
      setSortDir("asc");
    }
  };

  // CSV Export
  const exportCSV = () => {
    const headers = visibleColumns.map((c) => c.header).join(",");
    const rows = sorted.map((row) =>
      visibleColumns.map((c) => `"${String(c.accessor(row)).replace(/"/g, '""')}"`).join(",")
    );
    const blob = new Blob([headers + "\n" + rows.join("\n")], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${exportFilename}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // Column visibility toggle
  const toggleColumn = (colId: string) => {
    const next = new Set(hiddenCols);
    next.has(colId) ? next.delete(colId) : next.add(colId);
    setHiddenCols(next);
  };

  // Loading skeleton
  if (loading) {
    return (
      <div className={cn("w-full space-y-2", className)}>
        <div className="flex items-center gap-2 mb-4">
          <Skeleton className="h-10 w-64" />
          <Skeleton className="h-10 w-24 ml-auto" />
        </div>
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="flex gap-4 py-3">
            {Array.from({ length: 4 }).map((_, j) => (
              <Skeleton key={j} className="h-5 flex-1" />
            ))}
          </div>
        ))}
      </div>
    );
  }

  const selectedCount = selected.size;

  return (
    <div className={cn("w-full", className)}>
      {/* Toolbar */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3 mb-4">
        <SearchBox
          value={search}
          onChange={setSearch}
          placeholder="Search records…"
          className="w-full sm:max-w-xs"
        />
        <div className="flex items-center gap-2 ml-auto">
          {/* Column visibility */}
          <Dropdown
            align="right"
            trigger={
              <Button variant="outline" size="sm" icon={<Columns className="h-4 w-4" />}>
                Columns
              </Button>
            }
            items={allColumns.map((c) => ({
              id: c.id,
              label: c.header,
              icon: !hiddenCols.has(c.id) ? <Check className="h-3 w-3" /> : <span className="h-3 w-3" />,
              onClick: () => toggleColumn(c.id),
            }))}
          />
          <Button variant="outline" size="sm" onClick={exportCSV} icon={<Download className="h-4 w-4" />}>
            Export
          </Button>
        </div>
      </div>

      {/* Bulk actions bar */}
      {selectedCount > 0 && bulkActions && (
        <div className="flex items-center gap-3 mb-3 px-4 py-2 rounded-lg bg-primary/5 border border-primary/20">
          <span className="text-sm font-medium text-primary">{selectedCount} selected</span>
          <div className="flex gap-2 ml-auto">
            {bulkActions.map((action, i) => (
              <Button
                key={i}
                variant={action.danger ? "destructive" : "outline"}
                size="sm"
                icon={action.icon}
                onClick={() => action.onClick(data.filter((r, idx) => selected.has(getRowId(r, idx))))}
              >
                {action.label}
              </Button>
            ))}
          </div>
        </div>
      )}

      {/* Table */}
      <div className="overflow-x-auto rounded-lg border">
        <table className="w-full text-sm">
          <thead>
            <tr className={cn("border-b bg-muted/50", stickyHeader && "sticky top-0 z-10")}>
              {selectable && (
                <th className="w-12 px-4 py-3">
                  <input
                    type="checkbox"
                    checked={allSelected}
                    onChange={toggleAll}
                    className="rounded border-input"
                    aria-label="Select all rows"
                  />
                </th>
              )}
              {visibleColumns.map((col) => (
                <th
                  key={col.id}
                  className={cn(
                    "px-4 py-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground whitespace-nowrap cursor-pointer select-none hover:text-foreground transition-colors",
                    col.align === "center" && "text-center",
                    col.align === "right" && "text-right"
                  )}
                  style={{ width: col.width }}
                  onClick={() => handleSort(col.id)}
                >
                  <span className="inline-flex items-center gap-1">
                    {col.header}
                    {sortCol === col.id ? (
                      sortDir === "asc" ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />
                    ) : (
                      <ArrowUpDown className="h-3 w-3 opacity-40" />
                    )}
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y">
            {paged.length === 0 ? (
              <tr>
                <td colSpan={visibleColumns.length + (selectable ? 1 : 0)} className="px-4 py-12">
                  <EmptyState
                    variant={search ? "search" : "default"}
                    title={emptyTitle}
                    description={emptyDescription}
                  />
                </td>
              </tr>
            ) : (
              paged.map((row, i) => {
                const rowId = getRowId(row, i + (safePage - 1) * pageSize);
                const isSelected = selected.has(rowId);
                return (
                  <tr
                    key={rowId}
                    className={cn(
                      "transition-colors hover:bg-accent/50",
                      isSelected && "bg-primary/5"
                    )}
                  >
                    {selectable && (
                      <td className="w-12 px-4 py-3">
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={() => toggleRow(rowId)}
                          className="rounded border-input"
                          aria-label={`Select row ${rowId}`}
                        />
                      </td>
                    )}
                    {visibleColumns.map((col) => (
                      <td
                        key={col.id}
                        className={cn(
                          "px-4 py-3 text-foreground",
                          col.align === "center" && "text-center",
                          col.align === "right" && "text-right"
                        )}
                      >
                        {col.accessor(row)}
                      </td>
                    ))}
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Footer */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3 mt-4 text-sm">
        <div className="text-muted-foreground">
          Showing {((safePage - 1) * pageSize) + 1}–{Math.min(safePage * pageSize, sorted.length)} of {sorted.length} results
        </div>
        <div className="flex items-center gap-2">
          <select
            value={pageSize}
            onChange={(e) => { setPageSize(Number(e.target.value)); setPage(1); }}
            className="h-8 rounded-md border border-input bg-background px-2 text-xs"
          >
            {[10, 25, 50, 100].map((n) => (
              <option key={n} value={n}>{n} / page</option>
            ))}
          </select>
          <div className="flex items-center gap-1">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={safePage === 1}
              className="inline-flex h-8 w-8 items-center justify-center rounded-md hover:bg-accent disabled:opacity-50"
              aria-label="Previous page"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
            <span className="px-2 font-medium">{safePage} / {totalPages}</span>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={safePage === totalPages}
              className="inline-flex h-8 w-8 items-center justify-center rounded-md hover:bg-accent disabled:opacity-50"
              aria-label="Next page"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
