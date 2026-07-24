import { useState, useRef, useEffect } from "react";
import { cn } from "@/lib/utils";
import { Search, X } from "lucide-react";

interface SearchBoxProps {
  value?: string;
  onChange?: (value: string) => void;
  onSearch?: (value: string) => void;
  placeholder?: string;
  debounce?: number;
  loading?: boolean;
  className?: string;
}

export function SearchBox({
  value: controlledValue,
  onChange,
  onSearch,
  placeholder = "Search…",
  debounce = 300,
  loading,
  className,
}: SearchBoxProps) {
  const [internalValue, setInternalValue] = useState(controlledValue || "");
  const value = controlledValue !== undefined ? controlledValue : internalValue;
  const timerRef = useRef<any>(null);

  const handleChange = (val: string) => {
    setInternalValue(val);
    onChange?.(val);
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => onSearch?.(val), debounce);
  };

  const clear = () => {
    handleChange("");
    onSearch?.("");
  };

  useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, []);

  return (
    <div className={cn("relative", className)}>
      <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
      <input
        type="search"
        value={value}
        onChange={(e) => handleChange(e.target.value)}
        placeholder={placeholder}
        className={cn(
          "h-10 w-full rounded-lg border border-input bg-background pl-10 pr-10 text-sm transition-colors",
          "placeholder:text-muted-foreground",
          "focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-1"
        )}
        role="searchbox"
      />
      {value && (
        <button
          onClick={clear}
          className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
          aria-label="Clear search"
        >
          <X className="h-4 w-4" />
        </button>
      )}
      {loading && (
        <div className="absolute right-10 top-1/2 -translate-y-1/2">
          <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
        </div>
      )}
    </div>
  );
}
