import React from "react";
import { cn } from "@/lib/utils";

interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  error?: string;
  hint?: string;
  charCount?: boolean;
}

export const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, label, error, hint, charCount, maxLength, id, value, ...props }, ref) => {
    const inputId = id || label?.toLowerCase().replace(/\s+/g, "-");
    const currentLength = typeof value === "string" ? value.length : 0;

    return (
      <div className="w-full space-y-1.5">
        {label && (
          <label htmlFor={inputId} className="block text-sm font-medium text-foreground">
            {label}
            {props.required && <span className="text-destructive ml-1">*</span>}
          </label>
        )}
        <textarea
          ref={ref}
          id={inputId}
          value={value}
          maxLength={maxLength}
          aria-invalid={!!error}
          aria-describedby={error ? `${inputId}-error` : hint ? `${inputId}-hint` : undefined}
          className={cn(
            "flex min-h-[80px] w-full rounded-lg border bg-background px-3 py-2 text-sm transition-colors resize-y",
            "placeholder:text-muted-foreground",
            "focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-1",
            "disabled:cursor-not-allowed disabled:opacity-50",
            error ? "border-destructive focus:ring-destructive/40" : "border-input",
            className
          )}
          {...props}
        />
        <div className="flex justify-between">
          {error && (
            <p id={`${inputId}-error`} className="text-xs text-destructive" role="alert">{error}</p>
          )}
          {hint && !error && (
            <p id={`${inputId}-hint`} className="text-xs text-muted-foreground">{hint}</p>
          )}
          {charCount && maxLength && (
            <p className={cn("text-xs ml-auto", currentLength >= maxLength ? "text-destructive" : "text-muted-foreground")}>
              {currentLength}/{maxLength}
            </p>
          )}
        </div>
      </div>
    );
  }
);
Textarea.displayName = "Textarea";
