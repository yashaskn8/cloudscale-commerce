import React, { useState } from "react";
import { Link } from "react-router";
import { useCartStore } from "@/stores/cartStore";
import { Trash2, ShoppingBag, ArrowRight } from "lucide-react";

export const Cart: React.FC = () => {
  const { items, updateQuantity, removeItem, couponCode, applyCoupon, getCartTotals } = useCartStore();
  const [couponInput, setCouponInput] = useState("");

  const { subtotal, discount, tax, total } = getCartTotals();

  const handleApplyCoupon = (e: React.FormEvent) => {
    e.preventDefault();
    applyCoupon(couponInput);
  };

  if (items.length === 0) {
    return (
      <div className="min-h-[60vh] flex flex-col items-center justify-center text-center px-4">
        <div className="p-4 bg-gray-100 dark:bg-gray-800 rounded-2xl mb-4 text-gray-500">
          <ShoppingBag className="h-12 w-12" />
        </div>
        <h1 className="text-3xl font-extrabold text-gray-900 dark:text-white mb-2">
          Your Cart is Empty
        </h1>
        <p className="text-gray-500 dark:text-gray-400 max-w-md mb-6">
          You haven't added any products to your shopping cart yet.
        </p>
        <Link
          to="/products"
          className="px-5 py-2.5 bg-primary text-white font-semibold rounded-lg shadow-sm hover:bg-primary/95"
        >
          Start Shopping
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Shopping Cart</h1>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Cart Item List */}
        <div className="lg:col-span-2 space-y-4">
          {items.map((item) => (
            <div
              key={item.product_id}
              className="flex items-center justify-between p-4 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-2xl shadow-sm"
            >
              <div className="flex-1 min-w-0 pr-4">
                <span className="text-xs font-mono text-gray-400 uppercase">{item.sku}</span>
                <h3 className="text-lg font-bold text-gray-900 dark:text-white truncate">{item.name}</h3>
                <p className="text-sm font-semibold text-primary mt-1">${item.price}</p>
              </div>

              {/* Quantity control */}
              <div className="flex items-center space-x-3 mr-6">
                <button
                  onClick={() => updateQuantity(item.product_id, item.quantity - 1)}
                  className="px-2.5 py-1 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-600 dark:text-gray-300 hover:bg-gray-100"
                >
                  -
                </button>
                <span className="font-semibold dark:text-white">{item.quantity}</span>
                <button
                  onClick={() => updateQuantity(item.product_id, item.quantity + 1)}
                  className="px-2.5 py-1 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-600 dark:text-gray-300 hover:bg-gray-100"
                >
                  +
                </button>
              </div>

              {/* Remove button */}
              <button
                onClick={() => removeItem(item.product_id)}
                className="p-2 text-red-500 hover:bg-red-50 dark:hover:bg-red-950/20 rounded-lg"
              >
                <Trash2 className="h-5 w-5" />
              </button>
            </div>
          ))}
        </div>

        {/* Pricing Summary Panel */}
        <div className="space-y-6">
          <div className="bg-white dark:bg-gray-800 p-6 border border-gray-200 dark:border-gray-700 rounded-2xl shadow-sm">
            <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-4">Summary</h3>

            {/* Coupons form */}
            <form onSubmit={handleApplyCoupon} className="mb-6 flex gap-2">
              <input
                type="text"
                placeholder="Promo Code"
                value={couponInput}
                onChange={(e) => setCouponInput(e.target.value)}
                className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg shadow-sm focus:ring-primary focus:border-primary dark:bg-gray-700 dark:text-white"
              />
              <button
                type="submit"
                className="px-4 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 font-semibold rounded-lg hover:bg-gray-50"
              >
                Apply
              </button>
            </form>

            <div className="space-y-3.5 border-b border-gray-100 dark:border-gray-750 pb-4 mb-4 text-sm text-gray-500 dark:text-gray-400">
              <div className="flex justify-between">
                <span>Subtotal</span>
                <span className="font-semibold text-gray-900 dark:text-white">${subtotal}</span>
              </div>
              {discount > 0 && (
                <div className="flex justify-between text-green-500">
                  <span>Discount ({couponCode})</span>
                  <span>-${discount}</span>
                </div>
              )}
              <div className="flex justify-between">
                <span>Estimated Tax</span>
                <span className="font-semibold text-gray-900 dark:text-white">${tax}</span>
              </div>
              <div className="flex justify-between">
                <span>Shipping</span>
                <span className="font-semibold text-gray-900 dark:text-white">$9.99</span>
              </div>
            </div>

            <div className="flex justify-between text-lg font-bold text-gray-900 dark:text-white mb-6">
              <span>Total</span>
              <span>${total}</span>
            </div>

            <Link
              to="/checkout"
              className="w-full flex items-center justify-center py-2.5 bg-primary text-white font-semibold rounded-lg shadow-sm hover:bg-primary/95"
            >
              Checkout <ArrowRight className="h-4 w-4 ml-2" />
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
};
export default Cart;
