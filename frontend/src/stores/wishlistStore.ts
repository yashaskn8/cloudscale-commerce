import { create } from "zustand";
import { persist } from "zustand/middleware";

interface WishlistState {
  itemIds: string[];
  toggleWishlist: (productId: string) => void;
  isWishlisted: (productId: string) => boolean;
  clearWishlist: () => void;
}

export const useWishlistStore = create<WishlistState>()(
  persist(
    (set, get) => ({
      itemIds: [],
      toggleWishlist: (productId) => {
        const current = get().itemIds;
        const exists = current.includes(productId);
        if (exists) {
          set({ itemIds: current.filter((id) => id !== productId) });
        } else {
          set({ itemIds: [...current, productId] });
        }
      },
      isWishlisted: (productId) => {
        return get().itemIds.includes(productId);
      },
      clearWishlist: () => {
        set({ itemIds: [] });
      },
    }),
    {
      name: "cloudscale-wishlist-store",
    }
  )
);
