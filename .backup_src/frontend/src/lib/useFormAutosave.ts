import { useEffect, useRef } from "react";

interface AutosaveOptions<T> {
  key: string;
  data: T;
  onSave?: (data: T) => void;
  delay?: number;
  enabled?: boolean;
}

export function useFormAutosave<T>({
  key,
  data,
  onSave,
  delay = 2000,
  enabled = true,
}: AutosaveOptions<T>) {
  const timerRef = useRef<any>(null);
  const initialMount = useRef(true);

  // Load initial draft from localStorage
  const getSavedDraft = (): T | null => {
    try {
      const saved = localStorage.getItem(`draft_${key}`);
      return saved ? JSON.parse(saved) : null;
    } catch {
      return null;
    }
  };

  // Clear saved draft
  const clearDraft = () => {
    try {
      localStorage.removeItem(`draft_${key}`);
    } catch {}
  };

  useEffect(() => {
    if (!enabled) return;

    // Skip autosave on initial render/mount to avoid overwriting existing loaded data
    if (initialMount.current) {
      initialMount.current = false;
      return;
    }

    clearTimeout(timerRef.current);

    timerRef.current = setTimeout(() => {
      try {
        localStorage.setItem(`draft_${key}`, JSON.stringify(data));
        onSave?.(data);
      } catch (err) {
        console.error("Failed to autosave draft", err);
      }
    }, delay);

    return () => clearTimeout(timerRef.current);
  }, [data, key, delay, enabled, onSave]);

  return { getSavedDraft, clearDraft };
}
