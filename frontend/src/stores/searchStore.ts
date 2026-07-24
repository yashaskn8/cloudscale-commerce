import { create } from "zustand";
import { persist } from "zustand/middleware";

interface SearchState {
  recentSearches: string[];
  addSearch: (term: string) => void;
  removeSearch: (term: string) => void;
  clearHistory: () => void;
}

export const useSearchStore = create<SearchState>()(
  persist(
    (set, get) => ({
      recentSearches: [],
      addSearch: (term) => {
        const cleaned = term.trim();
        if (!cleaned) return;
        const current = get().recentSearches;
        const filtered = current.filter((x) => x.toLowerCase() !== cleaned.toLowerCase());
        // Keep last 8 searches
        set({ recentSearches: [cleaned, ...filtered].slice(0, 8) });
      },
      removeSearch: (term) => {
        const current = get().recentSearches;
        set({ recentSearches: current.filter((x) => x !== term) });
      },
      clearHistory: () => {
        set({ recentSearches: [] });
      },
    }),
    {
      name: "cloudscale-search-store",
    }
  )
);
