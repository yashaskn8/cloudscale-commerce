import { cn } from "@/lib/utils";

interface RadioOption {
  value: string;
  label: string;
  description?: string;
  disabled?: boolean;
}

interface RadioGroupProps {
  name: string;
  label?: string;
  options: RadioOption[];
  value?: string;
  onChange?: (value: string) => void;
  error?: string;
  orientation?: "horizontal" | "vertical";
  className?: string;
}

export function RadioGroup({
  name,
  label,
  options,
  value,
  onChange,
  error,
  orientation = "vertical",
  className,
}: RadioGroupProps) {
  return (
    <fieldset className={cn("space-y-2", className)} role="radiogroup" aria-label={label}>
      {label && <legend className="text-sm font-medium text-foreground mb-2">{label}</legend>}
      <div className={cn("flex gap-3", orientation === "vertical" ? "flex-col" : "flex-row flex-wrap")}>
        {options.map((opt) => (
          <label
            key={opt.value}
            className={cn(
              "relative flex items-start gap-3 cursor-pointer rounded-lg border p-3 transition-all",
              value === opt.value
                ? "border-primary bg-primary/5 ring-1 ring-primary"
                : "border-input hover:bg-accent/50",
              opt.disabled && "cursor-not-allowed opacity-50"
            )}
          >
            <input
              type="radio"
              name={name}
              value={opt.value}
              checked={value === opt.value}
              disabled={opt.disabled}
              onChange={() => onChange?.(opt.value)}
              className="peer sr-only"
            />
            <span
              className={cn(
                "mt-0.5 h-4 w-4 shrink-0 rounded-full border-2 transition-colors",
                value === opt.value ? "border-primary" : "border-muted-foreground"
              )}
            >
              {value === opt.value && (
                <span className="block h-full w-full rounded-full scale-50 bg-primary" />
              )}
            </span>
            <div className="space-y-0.5">
              <span className="text-sm font-medium text-foreground">{opt.label}</span>
              {opt.description && <p className="text-xs text-muted-foreground">{opt.description}</p>}
            </div>
          </label>
        ))}
      </div>
      {error && <p className="text-xs text-destructive mt-1" role="alert">{error}</p>}
    </fieldset>
  );
}
