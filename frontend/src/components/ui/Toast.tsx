import { useEffect } from "react";
import { cn } from "@/lib/utils";
import { X, CheckCircle, AlertTriangle, AlertCircle, Info } from "lucide-react";
import { create } from "zustand";

type ToastVariant = "success" | "error" | "warning" | "info";

interface Toast {
  id: string;
  title: string;
  description?: string;
  variant: ToastVariant;
  duration?: number;
}

interface ToastStore {
  toasts: Toast[];
  add: (toast: Omit<Toast, "id">) => void;
  remove: (id: string) => void;
}

export const useToastStore = create<ToastStore>((set) => ({
  toasts: [],
  add: (toast) =>
    set((state) => ({
      toasts: [...state.toasts, { ...toast, id: crypto.randomUUID() }],
    })),
  remove: (id) =>
    set((state) => ({
      toasts: state.toasts.filter((t) => t.id !== id),
    })),
}));

export function toast(title: string, opts?: { description?: string; variant?: ToastVariant; duration?: number }) {
  useToastStore.getState().add({
    title,
    description: opts?.description,
    variant: opts?.variant || "info",
    duration: opts?.duration || 5000,
  });
}

const icons: Record<ToastVariant, React.ReactNode> = {
  success: <CheckCircle className="h-5 w-5 text-green-500" />,
  error: <AlertCircle className="h-5 w-5 text-red-500" />,
  warning: <AlertTriangle className="h-5 w-5 text-amber-500" />,
  info: <Info className="h-5 w-5 text-blue-500" />,
};

const variantBorder: Record<ToastVariant, string> = {
  success: "border-l-green-500",
  error: "border-l-red-500",
  warning: "border-l-amber-500",
  info: "border-l-blue-500",
};

function ToastItem({ toast: t, onRemove }: { toast: Toast; onRemove: () => void }) {
  useEffect(() => {
    const timer = setTimeout(onRemove, t.duration || 5000);
    return () => clearTimeout(timer);
  }, [t.duration, onRemove]);

  return (
    <div
      role="alert"
      className={cn(
        "flex items-start gap-3 rounded-lg border border-l-4 bg-background p-4 shadow-lg",
        "animate-in slide-in-from-right-full",
        variantBorder[t.variant]
      )}
    >
      <span className="shrink-0 mt-0.5">{icons[t.variant]}</span>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-semibold text-foreground">{t.title}</p>
        {t.description && <p className="text-xs text-muted-foreground mt-0.5">{t.description}</p>}
      </div>
      <button onClick={onRemove} className="shrink-0 text-muted-foreground hover:text-foreground transition-colors" aria-label="Dismiss">
        <X className="h-4 w-4" />
      </button>
    </div>
  );
}

export function ToastContainer() {
  const { toasts, remove } = useToastStore();

  if (toasts.length === 0) return null;

  return (
    <div className="fixed bottom-4 right-4 z-[100] flex flex-col gap-2 max-w-sm w-full" aria-live="polite">
      {toasts.map((t) => (
        <ToastItem key={t.id} toast={t} onRemove={() => remove(t.id)} />
      ))}
    </div>
  );
}
