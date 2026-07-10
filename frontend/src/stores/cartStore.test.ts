import { describe, it, expect, beforeEach } from "vitest";
import { useCartStore } from "./cartStore";

describe("Cart Zustand Store", () => {
  beforeEach(() => {
    useCartStore.getState().clearCart();
  });

  it("adds items to the cart", () => {
    const store = useCartStore.getState();
    store.addItem({
      product_id: "p1",
      sku: "SKU123",
      name: "Product 1",
      price: 100,
    });

    const items = useCartStore.getState().items;
    expect(items.length).toBe(1);
    expect(items[0].product_id).toBe("p1");
    expect(items[0].quantity).toBe(1);
  });

  it("updates item quantity", () => {
    const store = useCartStore.getState();
    store.addItem({
      product_id: "p1",
      sku: "SKU123",
      name: "Product 1",
      price: 100,
    });

    useCartStore.getState().updateQuantity("p1", 5);
    const items = useCartStore.getState().items;
    expect(items[0].quantity).toBe(5);
  });

  it("calculates totals with tax and shipping", () => {
    const store = useCartStore.getState();
    store.addItem({
      product_id: "p1",
      sku: "SKU123",
      name: "Product 1",
      price: 100,
    });
    // Add second quantity
    store.addItem({
      product_id: "p1",
      sku: "SKU123",
      name: "Product 1",
      price: 100,
    });

    const totals = useCartStore.getState().getCartTotals();
    expect(totals.subtotal).toBe(200);
    // tax is 8%, shipping is 9.99
    expect(totals.tax).toBe(16);
    expect(totals.total).toBe(225.99); // 200 - 0 + 16 + 9.99
  });

  it("applies promo coupon code", () => {
    const store = useCartStore.getState();
    store.addItem({
      product_id: "p1",
      sku: "SKU123",
      name: "Product 1",
      price: 100,
    });

    // CLOUDSCALE10 = 10% discount
    useCartStore.getState().applyCoupon("CLOUDSCALE10");
    const state = useCartStore.getState();
    expect(state.couponCode).toBe("CLOUDSCALE10");
    expect(state.discountValue).toBe(0.1);

    const totals = useCartStore.getState().getCartTotals();
    expect(totals.discount).toBe(10);
    expect(totals.total).toBe(100 - 10 + 7.2 + 9.99); // subtotal - discount + tax(8%) + shipping(9.99)
  });
});

