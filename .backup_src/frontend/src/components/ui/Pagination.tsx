import { cn } from "@/lib/utils";
import { ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight } from "lucide-react";

interface PaginationProps {
  page: number;
  totalPages: number;
  onPageChange: (page: number) => void;
  siblingsCount?: number;
  showEdges?: boolean;
  className?: string;
}

function getPages(current: number, total: number, siblings: number): (number | "dots")[] {
  const pages: (number | "dots")[] = [];
  const left = Math.max(2, current - siblings);
  const right = Math.min(total - 1, current + siblings);

  pages.push(1);
  if (left > 2) pages.push("dots");
  for (let i = left; i <= right; i++) pages.push(i);
  if (right < total - 1) pages.push("dots");
  if (total > 1) pages.push(total);
  return pages;
}

export function Pagination({ page, totalPages, onPageChange, siblingsCount = 1, showEdges = true, className }: PaginationProps) {
  if (totalPages <= 1) return null;
  const pages = getPages(page, totalPages, siblingsCount);

  const btn = "inline-flex items-center justify-center h-9 min-w-9 rounded-lg text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring";

  return (
    <nav aria-label="Pagination" className={cn("flex items-center gap-1", className)}>
      {showEdges && (
        <button onClick={() => onPageChange(1)} disabled={page === 1} className={cn(btn, "hover:bg-accent disabled:opacity-50")} aria-label="First page">
          <ChevronsLeft className="h-4 w-4" />
        </button>
      )}
      <button onClick={() => onPageChange(page - 1)} disabled={page === 1} className={cn(btn, "hover:bg-accent disabled:opacity-50")} aria-label="Previous page">
        <ChevronLeft className="h-4 w-4" />
      </button>
      {pages.map((p, i) =>
        p === "dots" ? (
          <span key={`dots-${i}`} className="px-2 text-muted-foreground">…</span>
        ) : (
          <button
            key={p}
            onClick={() => onPageChange(p)}
            aria-current={p === page ? "page" : undefined}
            className={cn(
              btn,
              p === page
                ? "bg-primary text-white shadow-sm"
                : "hover:bg-accent text-muted-foreground"
            )}
          >
            {p}
          </button>
        )
      )}
      <button onClick={() => onPageChange(page + 1)} disabled={page === totalPages} className={cn(btn, "hover:bg-accent disabled:opacity-50")} aria-label="Next page">
        <ChevronRight className="h-4 w-4" />
      </button>
      {showEdges && (
        <button onClick={() => onPageChange(totalPages)} disabled={page === totalPages} className={cn(btn, "hover:bg-accent disabled:opacity-50")} aria-label="Last page">
          <ChevronsRight className="h-4 w-4" />
        </button>
      )}
    </nav>
  );
}
