import { cn } from "@/lib/utils";
import { X } from "lucide-react";

type ChipVariant = "filled" | "outlined" | "interactive";

interface ChipProps extends Omit<React.HTMLAttributes<HTMLSpanElement>, "color"> {
  variant?: ChipVariant;
  selected?: boolean;
  onSelect?: () => void;
  onRemove?: () => void;
  icon?: React.ReactNode;
  disabled?: boolean;
}

export function Chip({
  className,
  variant = "filled",
  selected = false,
  onSelect,
  onRemove,
  icon,
  disabled = false,
  children,
  ...props
}: ChipProps) {
  const isClickable = !!onSelect && !disabled;

  return (
    <span
      onClick={() => isClickable && onSelect?.()}
      className={cn(
        "inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium transition-all select-none",
        disabled && "opacity-50 cursor-not-allowed pointer-events-none",
        variant === "filled" && (selected ? "bg-primary text-white" : "bg-muted text-muted-foreground hover:bg-muted/80"),
        variant === "outlined" && (selected ? "border border-primary text-primary bg-primary/5" : "border border-input text-muted-foreground hover:bg-accent"),
        variant === "interactive" && (selected ? "bg-primary/10 text-primary border border-primary/20" : "border border-input text-muted-foreground hover:bg-accent/50"),
        isClickable && "cursor-pointer hover:scale-102 active:scale-98",
        className
      )}
      {...props}
    >
      {icon && <span className="shrink-0">{icon}</span>}
      <span>{children}</span>
      {onRemove && (
        <button
          type="button"
          disabled={disabled}
          onClick={(e) => {
            e.stopPropagation();
            onRemove();
          }}
          className="ml-1 rounded-full p-0.5 hover:bg-black/10 dark:hover:bg-white/20 inline-flex items-center justify-center transition-colors"
          aria-label="Remove filter"
        >
          <X className="h-3 w-3" />
        </button>
      )}
    </span>
  );
}
