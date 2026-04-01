import React from "react";
import { cn } from "@/lib/utils";

type BadgeVariant = "default" | "secondary" | "success" | "warning" | "destructive" | "outline" | "info";

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant;
  dot?: boolean;
  icon?: React.ReactNode;
  removable?: boolean;
  onRemove?: () => void;
}

const variantStyles: Record<BadgeVariant, string> = {
  default: "bg-primary/10 text-primary border-primary/20",
  secondary: "bg-secondary text-secondary-foreground border-secondary",
  success: "bg-green-100 text-green-800 border-green-200 dark:bg-green-900/30 dark:text-green-400 dark:border-green-800",
  warning: "bg-amber-100 text-amber-800 border-amber-200 dark:bg-amber-900/30 dark:text-amber-400 dark:border-amber-800",
  destructive: "bg-red-100 text-red-800 border-red-200 dark:bg-red-900/30 dark:text-red-400 dark:border-red-800",
  outline: "bg-transparent text-foreground border-border",
  info: "bg-blue-100 text-blue-800 border-blue-200 dark:bg-blue-900/30 dark:text-blue-400 dark:border-blue-800",
};

export function Badge({ className, variant = "default", dot, icon, removable, onRemove, children, ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors",
        variantStyles[variant],
        className
      )}
      {...props}
    >
      {dot && (
        <span className={cn("h-1.5 w-1.5 rounded-full", {
          "bg-primary": variant === "default",
          "bg-green-500": variant === "success",
          "bg-amber-500": variant === "warning",
          "bg-red-500": variant === "destructive",
          "bg-blue-500": variant === "info",
          "bg-muted-foreground": variant === "secondary" || variant === "outline",
        })} />
      )}
      {icon && <span className="shrink-0">{icon}</span>}
      {children}
      {removable && (
        <button
          type="button"
          onClick={onRemove}
          className="ml-0.5 h-3.5 w-3.5 rounded-full hover:bg-foreground/20 inline-flex items-center justify-center"
          aria-label="Remove"
        >
          ×
        </button>
      )}
    </span>
  );
}
