import React from "react";
import { cn } from "@/lib/utils";
import { Calendar as CalendarIcon } from "lucide-react";

interface DatePickerProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, "type" | "onChange"> {
  label?: string;
  error?: string;
  hint?: string;
  value?: string; // YYYY-MM-DD
  onChange?: (date: string) => void;
}

export const DatePicker = React.forwardRef<HTMLInputElement, DatePickerProps>(
  ({ className, label, error, hint, value = "", onChange, id, ...props }, ref) => {
    const inputId = id || label?.toLowerCase().replace(/\s+/g, "-");

    return (
      <div className="w-full space-y-1.5">
        {label && (
          <label htmlFor={inputId} className="block text-sm font-medium text-foreground">
            {label}
            {props.required && <span className="text-destructive ml-1">*</span>}
          </label>
        )}
        <div className="relative">
          <CalendarIcon className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <input
            ref={ref}
            id={inputId}
            type="date"
            value={value}
            onChange={(e) => onChange?.(e.target.value)}
            aria-invalid={!!error}
            aria-describedby={error ? `${inputId}-error` : hint ? `${inputId}-hint` : undefined}
            className={cn(
              "flex h-10 w-full rounded-lg border bg-background pl-10 pr-3 text-sm transition-colors",
              "focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-1",
              "disabled:cursor-not-allowed disabled:opacity-50",
              "scheme-light dark:scheme-dark", // ensures dark mode calendar icon dropdown works nicely
              error ? "border-destructive focus:ring-destructive/40" : "border-input",
              className
            )}
            {...props}
          />
        </div>
        {error && (
          <p id={`${inputId}-error`} className="text-xs text-destructive" role="alert">
            {error}
          </p>
        )}
        {hint && !error && (
          <p id={`${inputId}-hint`} className="text-xs text-muted-foreground">
            {hint}
          </p>
        )}
      </div>
    );
  }
);
DatePicker.displayName = "DatePicker";
