import React from "react";
import { cn } from "@/lib/utils";
import { Check } from "lucide-react";

interface CheckboxProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, "type"> {
  label?: string;
  description?: string;
  error?: string;
}

export const Checkbox = React.forwardRef<HTMLInputElement, CheckboxProps>(
  ({ className, label, description, error, id, ...props }, ref) => {
    const inputId = id || label?.toLowerCase().replace(/\s+/g, "-");

    return (
      <div className="flex items-start gap-3">
        <div className="relative flex items-center">
          <input
            ref={ref}
            id={inputId}
            type="checkbox"
            className="peer sr-only"
            aria-invalid={!!error}
            {...props}
          />
          <label
            htmlFor={inputId}
            className={cn(
              "flex h-5 w-5 shrink-0 items-center justify-center rounded border-2 cursor-pointer transition-all",
              "border-input peer-focus-visible:ring-2 peer-focus-visible:ring-ring peer-focus-visible:ring-offset-2",
              "peer-checked:bg-primary peer-checked:border-primary peer-checked:text-white",
              "peer-disabled:cursor-not-allowed peer-disabled:opacity-50",
              error && "border-destructive",
              className
            )}
          >
            <Check className="h-3 w-3 opacity-0 peer-checked:opacity-100 transition-opacity" />
          </label>
        </div>
        {(label || description) && (
          <div className="space-y-0.5">
            {label && (
              <label htmlFor={inputId} className="text-sm font-medium cursor-pointer text-foreground">
                {label}
              </label>
            )}
            {description && <p className="text-xs text-muted-foreground">{description}</p>}
            {error && <p className="text-xs text-destructive" role="alert">{error}</p>}
          </div>
        )}
      </div>
    );
  }
);
Checkbox.displayName = "Checkbox";
