import React, { useRef, useState, useMemo } from "react";
import { cn } from "@/lib/utils";
import { ArrowUpDown, ArrowUp, ArrowDown } from "lucide-react";
import { useVirtualizer } from "@/hooks/useVirtualizer";
import { SearchBox } from "../ui/SearchBox";
import { EmptyState } from "../ui/EmptyState";

export interface VirtualColumn<T> {
  id: string;
  header: string;
  accessor: (row: T) => React.ReactNode;
  sortAccessor?: (row: T) => string | number;
  searchable?: boolean;
  width?: string; // CSS width e.g., '150px' or '25%'
}

type SortDir = "asc" | "desc" | null;

interface VirtualDataTableProps<T> {
  columns: VirtualColumn<T>[];
  data: T[];
  loading?: boolean;
  rowHeight?: number;
  containerHeight?: number;
  emptyTitle?: string;
  emptyDescription?: string;
  getRowId: (row: T) => string;
}

export function VirtualDataTable<T>({
  columns,
  data,
  loading = false,
  rowHeight = 52,
  containerHeight = 400,
  emptyTitle = "No data found",
  emptyDescription = "There are no records matching the current selection.",
  getRowId
}: VirtualDataTableProps<T>) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [search, setSearch] = useState("");
  const [sortCol, setSortCol] = useState<string | null>(null);
  const [sortDir, setSortDir] = useState<SortDir>(null);

  // Search Filter
  const searchableIds = useMemo(
    () => columns.filter((c) => c.searchable !== false).map((c) => c.id),
    [columns]
  );

  const filtered = useMemo(() => {
    if (!search) return data;
    const q = search.toLowerCase();
    return data.filter((row) =>
      searchableIds.some((id) => {
        const col = columns.find((c) => c.id === id);
        if (!col) return false;
        // Simple string matches on text values
        const val = col.sortAccessor ? col.sortAccessor(row) : null;
        return String(val || "").toLowerCase().includes(q);
      })
    );
  }, [data, search, searchableIds, columns]);

  // Sort Filter
  const sorted = useMemo(() => {
    if (!sortCol || !sortDir) return filtered;
    const col = columns.find((c) => c.id === sortCol);
    if (!col) return filtered;

    return [...filtered].sort((a, b) => {
      const aVal = col.sortAccessor ? col.sortAccessor(a) : "";
      const bVal = col.sortAccessor ? col.sortAccessor(b) : "";

      if (aVal < bVal) return sortDir === "asc" ? -1 : 1;
      if (aVal > bVal) return sortDir === "asc" ? 1 : -1;
      return 0;
    });
  }, [filtered, sortCol, sortDir, columns]);

  const toggleSort = (colId: string) => {
    if (sortCol === colId) {
      if (sortDir === "asc") setSortDir("desc");
      else if (sortDir === "desc") {
        setSortCol(null);
        setSortDir(null);
      }
    } else {
      setSortCol(colId);
      setSortDir("asc");
    }
  };

  // Virtualizer Hook
  const { virtualItems, totalHeight } = useVirtualizer({
    itemCount: sorted.length,
    itemHeight: rowHeight,
    overscan: 5,
    containerRef
  });

  return (
    <div className="space-y-4">
      {/* Search Header */}
      <div className="flex items-center justify-between gap-4">
        <div className="w-full max-w-sm">
          <SearchBox
            placeholder="Search virtual records..."
            value={search}
            onSearch={setSearch}
          />
        </div>
        <div className="text-xs text-muted-foreground">
          Showing <span className="font-semibold">{sorted.length}</span> / {data.length} records
        </div>
      </div>

      {/* Table Area */}
      <div className="border rounded-xl bg-card overflow-hidden shadow-sm">
        {/* Table Header */}
        <div className="flex bg-muted/50 border-b font-semibold text-xs text-muted-foreground uppercase select-none">
          {columns.map((col) => (
            <div
              key={col.id}
              onClick={() => col.sortAccessor && toggleSort(col.id)}
              style={{ width: col.width || "auto", flexGrow: col.width ? 0 : 1 }}
              className={cn(
                "px-6 py-4 flex items-center gap-2",
                col.sortAccessor && "cursor-pointer hover:text-foreground"
              )}
            >
              <span>{col.header}</span>
              {col.sortAccessor && sortCol === col.id && (
                <span>
                  {sortDir === "asc" ? (
                    <ArrowUp className="h-3.5 w-3.5 text-primary" />
                  ) : (
                    <ArrowDown className="h-3.5 w-3.5 text-primary" />
                  )}
                </span>
              )}
              {col.sortAccessor && sortCol !== col.id && (
                <ArrowUpDown className="h-3.5 w-3.5 opacity-30" />
              )}
            </div>
          ))}
        </div>

        {/* Scroll Container */}
        {loading ? (
          <div className="p-6 space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-10 bg-muted/65 rounded-lg animate-pulse" />
            ))}
          </div>
        ) : sorted.length === 0 ? (
          <div className="p-8">
            <EmptyState title={emptyTitle} description={emptyDescription} />
          </div>
        ) : (
          <div
            ref={containerRef}
            style={{ height: `${containerHeight}px` }}
            className="overflow-y-auto relative"
          >
            {/* Absolute element setting total height for scroll track */}
            <div style={{ height: `${totalHeight}px`, width: "100%", position: "relative" }}>
              {virtualItems.map((item) => {
                const row = sorted[item.index];
                if (!row) return null;
                const rowId = getRowId(row);

                return (
                  <div
                    key={rowId}
                    style={{
                      position: "absolute",
                      top: 0,
                      left: 0,
                      width: "100%",
                      height: `${rowHeight}px`,
                      transform: `translateY(${item.offsetTop}px)`
                    }}
                    className={cn(
                      "flex items-center border-b transition-colors hover:bg-muted/40",
                      item.index % 2 === 1 && "bg-muted/10"
                    )}
                  >
                    {columns.map((col) => (
                      <div
                        key={col.id}
                        style={{ width: col.width || "auto", flexGrow: col.width ? 0 : 1 }}
                        className="px-6 text-sm overflow-hidden text-ellipsis whitespace-nowrap text-foreground"
                      >
                        {col.accessor(row)}
                      </div>
                    ))}
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
