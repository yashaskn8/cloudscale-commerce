import React, { useEffect, useCallback, useRef } from "react";
import { cn } from "@/lib/utils";
import { X } from "lucide-react";
import { useFocusTrap } from "@/hooks/useFocusTrap";

interface DrawerProps {
  open: boolean;
  onClose: () => void;
  title?: string;
  description?: string;
  children: React.ReactNode;
  side?: "left" | "right";
  size?: "sm" | "md" | "lg";
  className?: string;
}

const sizeMap = { sm: "max-w-sm", md: "max-w-md", lg: "max-w-lg" };
const slideIn = { left: "animate-slide-in-left", right: "animate-slide-in-right" };

export function Drawer({ open, onClose, title, description, children, side = "right", size = "md", className }: DrawerProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  // Trap focus when open
  useFocusTrap(containerRef, open);

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    },
    [onClose]
  );

  useEffect(() => {
    if (open) {
      document.addEventListener("keydown", handleKeyDown);
      document.body.style.overflow = "hidden";
    }
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = "";
    };
  }, [open, handleKeyDown]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50" role="dialog" aria-modal="true" aria-label={title}>
      <div className="fixed inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
      <div
        ref={containerRef}
        className={cn(
          "fixed inset-y-0 flex flex-col w-full bg-background border shadow-2xl",
          side === "right" ? "right-0" : "left-0",
          sizeMap[size],
          slideIn[side],
          className
        )}
      >
        <div className="flex items-center justify-between border-b px-6 py-4">
          <div>
            {title && <h2 className="text-lg font-semibold text-foreground">{title}</h2>}
            {description && <p className="text-sm text-muted-foreground">{description}</p>}
          </div>
          <button
            onClick={onClose}
            className="rounded-md p-1 text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
            aria-label="Close drawer"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-6">{children}</div>
      </div>
    </div>
  );
}
