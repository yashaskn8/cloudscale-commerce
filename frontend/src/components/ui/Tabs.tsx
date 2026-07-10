import React, { useState } from "react";
import { cn } from "@/lib/utils";

interface Tab {
  id: string;
  label: string;
  icon?: React.ReactNode;
  badge?: string | number;
  disabled?: boolean;
  content: React.ReactNode;
}

interface TabsProps {
  tabs: Tab[];
  defaultTab?: string;
  onChange?: (tabId: string) => void;
  variant?: "underline" | "pills" | "bordered";
  className?: string;
}

export function Tabs({ tabs, defaultTab, onChange, variant = "underline", className }: TabsProps) {
  const [active, setActive] = useState(defaultTab || tabs[0]?.id);

  const select = (id: string) => {
    setActive(id);
    onChange?.(id);
  };

  return (
    <div className={cn("w-full", className)}>
      <div
        className={cn("flex", {
          "border-b": variant === "underline",
          "gap-1 bg-muted p-1 rounded-lg": variant === "pills",
          "gap-0": variant === "bordered",
        })}
        role="tablist"
      >
        {tabs.map((tab) => (
          <button
            key={tab.id}
            role="tab"
            aria-selected={active === tab.id}
            aria-controls={`tabpanel-${tab.id}`}
            disabled={tab.disabled}
            onClick={() => !tab.disabled && select(tab.id)}
            className={cn(
              "inline-flex items-center gap-2 px-4 py-2 text-sm font-medium transition-colors whitespace-nowrap",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
              tab.disabled && "opacity-50 cursor-not-allowed",
              variant === "underline" && [
                "-mb-px border-b-2",
                active === tab.id
                  ? "border-primary text-primary"
                  : "border-transparent text-muted-foreground hover:text-foreground hover:border-border",
              ],
              variant === "pills" && [
                "rounded-md",
                active === tab.id
                  ? "bg-background text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground",
              ],
              variant === "bordered" && [
                "border rounded-t-lg -mb-px",
                active === tab.id
                  ? "border-border border-b-background bg-background text-foreground"
                  : "border-transparent text-muted-foreground hover:text-foreground",
              ]
            )}
          >
            {tab.icon}
            {tab.label}
            {tab.badge !== undefined && (
              <span className="rounded-full bg-primary/10 text-primary px-1.5 py-0.5 text-xs font-bold">
                {tab.badge}
              </span>
            )}
          </button>
        ))}
      </div>
      {tabs.map((tab) => (
        <div
          key={tab.id}
          id={`tabpanel-${tab.id}`}
          role="tabpanel"
          hidden={active !== tab.id}
          className="pt-4"
        >
          {active === tab.id && tab.content}
        </div>
      ))}
    </div>
  );
}
