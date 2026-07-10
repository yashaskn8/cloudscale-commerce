import { cn } from "@/lib/utils";

interface ProgressProps {
  value: number;
  max?: number;
  variant?: "default" | "success" | "warning" | "error";
  size?: "sm" | "md" | "lg";
  showLabel?: boolean;
  label?: string;
  animated?: boolean;
  className?: string;
}

const barColors = {
  default: "bg-primary",
  success: "bg-green-500",
  warning: "bg-amber-500",
  error: "bg-red-500",
};

const sizeStyles = {
  sm: "h-1.5",
  md: "h-2.5",
  lg: "h-4",
};

export function Progress({
  value,
  max = 100,
  variant = "default",
  size = "md",
  showLabel = false,
  label,
  animated = true,
  className,
}: ProgressProps) {
  const pct = Math.min(100, Math.max(0, (value / max) * 100));

  return (
    <div className={cn("w-full space-y-1", className)}>
      {(showLabel || label) && (
        <div className="flex justify-between text-xs">
          <span className="text-muted-foreground">{label || "Progress"}</span>
          <span className="font-medium text-foreground">{Math.round(pct)}%</span>
        </div>
      )}
      <div
        className={cn("w-full overflow-hidden rounded-full bg-muted", sizeStyles[size])}
        role="progressbar"
        aria-valuenow={value}
        aria-valuemin={0}
        aria-valuemax={max}
      >
        <div
          className={cn(
            "h-full rounded-full transition-all duration-500 ease-out",
            barColors[variant],
            animated && "animate-progress-stripe"
          )}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
