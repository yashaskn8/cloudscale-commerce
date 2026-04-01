import React, { useEffect, useCallback, useRef } from "react";
import { cn } from "@/lib/utils";
import { X } from "lucide-react";
import { useFocusTrap } from "@/hooks/useFocusTrap";

interface ModalProps {
  open: boolean;
  onClose: () => void;
  title?: string;
  description?: string;
  children: React.ReactNode;
  size?: "sm" | "md" | "lg" | "xl" | "full";
  className?: string;
}

const sizeStyles = {
  sm: "max-w-sm",
  md: "max-w-md",
  lg: "max-w-lg",
  xl: "max-w-2xl",
  full: "max-w-[90vw]",
};

export function Modal({ open, onClose, title, description, children, size = "md", className }: ModalProps) {
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
    <div className="fixed inset-0 z-50 flex items-center justify-center" role="dialog" aria-modal="true" aria-label={title}>
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/60 backdrop-blur-sm animate-in fade-in-0" onClick={onClose} />
      {/* Content */}
      <div
        ref={containerRef}
        className={cn(
          "relative z-50 w-full rounded-xl border bg-background p-6 shadow-2xl animate-in fade-in-0 zoom-in-95",
          sizeStyles[size],
          className
        )}
      >
        {title && (
          <div className="mb-4">
            <h2 className="text-lg font-semibold text-foreground">{title}</h2>
            {description && <p className="text-sm text-muted-foreground mt-1">{description}</p>}
          </div>
        )}
        <button
          onClick={onClose}
          className="absolute right-4 top-4 rounded-md p-1 text-muted-foreground hover:text-foreground hover:bg-accent transition-colors focus-visible:ring-2 focus-visible:ring-ring"
          aria-label="Close"
        >
          <X className="h-4 w-4" />
        </button>
        {children}
      </div>
    </div>
  );
}

interface ModalFooterProps {
  children: React.ReactNode;
  className?: string;
}

export function ModalFooter({ children, className }: ModalFooterProps) {
  return (
    <div className={cn("mt-6 flex justify-end gap-3", className)}>{children}</div>
  );
}
