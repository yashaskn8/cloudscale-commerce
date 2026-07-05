import React, { useEffect, useState, useRef, useMemo } from "react";
import { useNavigate } from "react-router";
import { Search, ShoppingBag, Layers, ShieldCheck, X, History, Trash2 } from "lucide-react";
import { useSearchStore } from "@/stores/searchStore";
import { fuzzySearch } from "@/lib/fuzzySearch";
import { useFocusTrap } from "@/hooks/useFocusTrap";
import { cn } from "@/lib/utils";

interface CommandItem {
  name: string;
  path: string;
  icon: React.ComponentType<{ className?: string }>;
  category: "Navigation" | "Admin";
}

export const CommandPalette: React.FC = () => {
  const navigate = useNavigate();
  const { recentSearches, addSearch, clearHistory } = useSearchStore();
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [activeIndex, setActiveIndex] = useState(0);

  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Trap focus inside command palette when open
  useFocusTrap(containerRef, isOpen);

  // Static commands list
  const commands: CommandItem[] = useMemo(() => [
    { name: "Browse Products Catalog", path: "/products", icon: ShoppingBag, category: "Navigation" },
    { name: "Checkout Cart", path: "/checkout", icon: ShoppingBag, category: "Navigation" },
    { name: "Orders Transaction History", path: "/orders", icon: Layers, category: "Navigation" },
    { name: "Warehouse Inventory levels", path: "/inventory", icon: Layers, category: "Navigation" },
    { name: "User Account Profiles", path: "/users", icon: ShieldCheck, category: "Admin" },
    { name: "SaaS Systems Admin Dashboard", path: "/admin", icon: ShieldCheck, category: "Admin" },
  ], []);

  // Keyboard shortcut listener to toggle palette
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setIsOpen((open) => !open);
        setQuery("");
        setActiveIndex(0);
      } else if (e.key === "Escape" && isOpen) {
        setIsOpen(false);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen]);

  // Focus input automatically on open
  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isOpen]);

  // Fuzzy match commands
  const filteredCommands = useMemo(() => {
    if (!query) {
      return commands.map((c) => ({ item: c, score: 1.0 }));
    }
    return fuzzySearch(commands, query, (cmd) => [cmd.name, cmd.category]);
  }, [query, commands]);

  // Handle keyboard list navigation
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (filteredCommands.length === 0) return;

    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActiveIndex((prev) => (prev + 1) % filteredCommands.length);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActiveIndex((prev) => (prev - 1 + filteredCommands.length) % filteredCommands.length);
    } else if (e.key === "Enter") {
      e.preventDefault();
      const active = filteredCommands[activeIndex];
      if (active) {
        addSearch(query || active.item.name);
        navigate(active.item.path);
        setIsOpen(false);
      }
    }
  };

  const handleSelectRecent = (term: string) => {
    setQuery(term);
    inputRef.current?.focus();
  };

  if (!isOpen) return null;

  return (
    <div
      ref={containerRef}
      className="fixed inset-0 z-50 flex items-start justify-center pt-20 bg-black/60 backdrop-blur-sm px-4"
    >
      <div
        className="relative w-full max-w-lg bg-background border rounded-2xl shadow-2xl overflow-hidden animate-in fade-in-0 zoom-in-95"
        role="combobox"
        aria-expanded={isOpen}
        aria-haspopup="listbox"
        aria-controls="command-listbox"
      >
        {/* Input Header */}
        <div className="flex items-center px-4 py-3.5 border-b">
          <Search className="h-5 w-5 text-muted-foreground mr-3" />
          <input
            ref={inputRef}
            type="text"
            placeholder="Search commands, pages... (Ctrl + K to close)"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setActiveIndex(0);
            }}
            onKeyDown={handleKeyDown}
            aria-autocomplete="list"
            aria-controls="command-listbox"
            aria-activedescendant={
              filteredCommands[activeIndex] ? `cmd-item-${activeIndex}` : undefined
            }
            className="flex-1 bg-transparent text-sm focus:outline-none text-foreground placeholder:text-muted-foreground"
          />
          <button
            onClick={() => setIsOpen(false)}
            className="p-1 rounded hover:bg-muted text-muted-foreground transition-colors"
            aria-label="Close search"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Search History segment */}
        {!query && recentSearches.length > 0 && (
          <div className="p-3 border-b bg-muted/20">
            <div className="flex items-center justify-between text-xs text-muted-foreground font-semibold px-2 mb-2">
              <span className="flex items-center gap-1.5">
                <History className="h-3.5 w-3.5" /> Recent Searches
              </span>
              <button
                onClick={clearHistory}
                className="hover:text-destructive flex items-center gap-1 transition-colors"
              >
                <Trash2 className="h-3 w-3" /> Clear History
              </button>
            </div>
            <div className="flex flex-wrap gap-1.5 px-1">
              {recentSearches.map((term, index) => (
                <button
                  key={index}
                  onClick={() => handleSelectRecent(term)}
                  className="px-2.5 py-1 text-xs bg-muted rounded-lg hover:bg-primary/10 hover:text-primary transition-colors text-foreground"
                >
                  {term}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Command listbox */}
        <div id="command-listbox" role="listbox" className="max-h-80 overflow-y-auto p-2 space-y-1">
          {filteredCommands.length === 0 ? (
            <div className="text-center py-8 text-sm text-muted-foreground">
              No matching pages or commands found.
            </div>
          ) : (
            filteredCommands.map((res, index) => {
              const cmd = res.item;
              const Icon = cmd.icon;
              const isSelected = index === activeIndex;

              return (
                <button
                  id={`cmd-item-${index}`}
                  key={cmd.name}
                  role="option"
                  aria-selected={isSelected}
                  onClick={() => {
                    addSearch(query || cmd.name);
                    navigate(cmd.path);
                    setIsOpen(false);
                  }}
                  onMouseEnter={() => setActiveIndex(index)}
                  className={cn(
                    "w-full flex items-center px-4 py-3 rounded-xl text-left text-sm transition-all duration-150 outline-none",
                    isSelected
                      ? "bg-primary text-white scale-102 shadow-md"
                      : "text-foreground hover:bg-muted"
                  )}
                >
                  <Icon className={cn("h-4 w-4 mr-3 shrink-0", isSelected ? "text-white" : "text-muted-foreground")} />
                  <span className="flex-1 font-medium">{cmd.name}</span>
                  <span
                    className={cn(
                      "text-[10px] uppercase font-mono tracking-wider px-2 py-0.5 rounded-full border transition-colors",
                      isSelected
                        ? "bg-white/20 border-white/20 text-white"
                        : "bg-muted border-border text-muted-foreground"
                    )}
                  >
                    {cmd.category}
                  </span>
                </button>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
};
