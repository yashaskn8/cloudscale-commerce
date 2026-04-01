import React, { useState, useRef, useEffect } from "react";
import { cn } from "@/lib/utils";

interface PopoverProps {
  trigger: React.ReactNode;
  children: React.ReactNode;
  align?: "left" | "right" | "center";
  className?: string;
}

export function Popover({ trigger, children, align = "left", className }: PopoverProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Escape") setOpen(false);
  };

  return (
    <div ref={ref} className="relative inline-block" onKeyDown={handleKeyDown}>
      <div onClick={() => setOpen(!open)} className="cursor-pointer">
        {trigger}
      </div>
      {open && (
        <div
          className={cn(
            "absolute z-50 mt-2 rounded-lg border bg-background p-4 shadow-xl animate-in fade-in-0 zoom-in-95 focus:outline-none",
            align === "left" && "left-0",
            align === "right" && "right-0",
            align === "center" && "left-1/2 -translate-x-1/2",
            className
          )}
        >
          {children}
        </div>
      )}
    </div>
  );
}
