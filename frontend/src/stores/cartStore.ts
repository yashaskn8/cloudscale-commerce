import { create } from "zustand";
import { persist } from "zustand/middleware";

export interface CartItem {
  product_id: string;
  sku: string;
  name: string;
  price: number;
  quantity: number;
}

interface CartState {
  items: CartItem[];
  shippingCost: number;
  taxRate: number;
  couponCode: string | null;
  discountValue: number;
  
  addItem: (item: Omit<CartItem, "quantity">) => void;
  removeItem: (product_id: string) => void;
  updateQuantity: (product_id: string, quantity: number) => void;
  applyCoupon: (code: string) => void;
  clearCart: () => void;
  
  getCartTotals: () => {
    subtotal: number;
    discount: number;
    tax: number;
    total: number;
  };
}

export const useCartStore = create<CartState>()(
  persist(
    (set, get) => ({
      items: [],
      shippingCost: 9.99,
      taxRate: 0.08, // 8% sales tax
      couponCode: null,
      discountValue: 0,

      addItem: (newItem) => {
        const currentItems = get().items;
        const existingItem = currentItems.find((item) => item.product_id === newItem.product_id);

        if (existingItem) {
          set({
            items: currentItems.map((item) =>
              item.product_id === newItem.product_id
                ? { ...item, quantity: item.quantity + 1 }
                : item
            ),
          });
        } else {
          set({ items: [...currentItems, { ...newItem, quantity: 1 }] });
        }
      },

      removeItem: (product_id) => {
        set({ items: get().items.filter((item) => item.product_id !== product_id) });
      },

      updateQuantity: (product_id, quantity) => {
        if (quantity <= 0) {
          get().removeItem(product_id);
          return;
        }
        set({
          items: get().items.map((item) =>
            item.product_id === product_id ? { ...item, quantity } : item
          ),
        });
      },

      applyCoupon: (code) => {
        if (code.toUpperCase() === "CLOUDSCALE10") {
          set({ couponCode: code, discountValue: 0.1 }); // 10% Off
        } else {
          set({ couponCode: null, discountValue: 0 });
        }
      },

      clearCart: () => {
        set({ items: [], couponCode: null, discountValue: 0 });
      },

      getCartTotals: () => {
        const { items, shippingCost, taxRate, discountValue } = get();
        const subtotal = items.reduce((acc, item) => acc + item.price * item.quantity, 0);
        const discount = subtotal * discountValue;
        const taxableAmount = subtotal - discount;
        const tax = taxableAmount * taxRate;
        const total = subtotal > 0 ? taxableAmount + tax + shippingCost : 0;

        return {
          subtotal: parseFloat(subtotal.toFixed(2)),
          discount: parseFloat(discount.toFixed(2)),
          tax: parseFloat(tax.toFixed(2)),
          total: parseFloat(total.toFixed(2)),
        };
      },
    }),
    {
      name: "cloudscale-cart-store",
    }
  )
);
