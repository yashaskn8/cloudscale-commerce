import React from "react";
import { cn } from "@/lib/utils";

interface SkeletonProps {
  className?: string;
  variant?: "text" | "circle" | "rect";
  width?: string | number;
  height?: string | number;
  count?: number;
}

export function Skeleton({ className, variant = "text", width, height, count = 1 }: SkeletonProps) {
  const base = "animate-pulse bg-muted rounded";
  const variants = {
    text: "h-4 w-full rounded",
    circle: "rounded-full",
    rect: "rounded-lg",
  };

  const style: React.CSSProperties = { width, height };

  if (count > 1) {
    return (
      <div className="space-y-2">
        {Array.from({ length: count }).map((_, i) => (
          <div key={i} className={cn(base, variants[variant], className)} style={style} />
        ))}
      </div>
    );
  }

  return <div className={cn(base, variants[variant], className)} style={style} />;
}

// Preset skeleton layouts
export function SkeletonCard({ className }: { className?: string }) {
  return (
    <div className={cn("rounded-xl border p-4 space-y-3", className)}>
      <Skeleton variant="rect" className="h-40 w-full" />
      <Skeleton className="h-5 w-3/4" />
      <Skeleton className="h-4 w-1/2" />
      <div className="flex gap-2 pt-2">
        <Skeleton className="h-8 w-20" />
        <Skeleton className="h-8 w-20" />
      </div>
    </div>
  );
}

export function SkeletonTable({ rows = 5, cols = 4 }: { rows?: number; cols?: number }) {
  return (
    <div className="w-full space-y-2">
      <div className="flex gap-4 pb-2 border-b">
        {Array.from({ length: cols }).map((_, i) => (
          <Skeleton key={i} className="h-4 flex-1" />
        ))}
      </div>
      {Array.from({ length: rows }).map((_, r) => (
        <div key={r} className="flex gap-4 py-2">
          {Array.from({ length: cols }).map((_, c) => (
            <Skeleton key={c} className="h-4 flex-1" />
          ))}
        </div>
      ))}
    </div>
  );
}
