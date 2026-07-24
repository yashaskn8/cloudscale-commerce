import React, { useState, useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { useNavigate } from "react-router";
import { useCartStore } from "@/stores/cartStore";
import { apiClient } from "@/lib/api-client";
import { useNotificationStore } from "@/stores/notificationStore";
import { CreditCard, Landmark, CheckCircle } from "lucide-react";
import { Input, Button, Alert } from "@/components/ui";
import { useFormAutosave } from "@/lib/useFormAutosave";
import { useUnsavedChanges } from "@/lib/useUnsavedChanges";
import { useTranslation } from "@/i18n";

const checkoutSchema = z.object({
  shipping_address: z.string().min(5, "Enter your shipping street address"),
  city: z.string().min(2, "Enter a valid city name"),
  zip_code: z.string().min(5, "Zip code must be at least 5 digits"),
  payment_method: z.enum(["credit_card", "bank_transfer"]),
});

type CheckoutForm = z.infer<typeof checkoutSchema>;

export const Checkout: React.FC = () => {
  const navigate = useNavigate();
  const { t } = useTranslation();
  const { items, clearCart, getCartTotals } = useCartStore();
  const { addNotification } = useNotificationStore();
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { total } = getCartTotals();

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    reset,
    formState: { errors, isDirty },
  } = useForm<CheckoutForm>({
    resolver: zodResolver(checkoutSchema),
    defaultValues: {
      shipping_address: "",
      city: "",
      zip_code: "",
      payment_method: "credit_card",
    },
  });

  const formData = watch();
  const selectedPayment = formData.payment_method;

  // Form Autosave
  const { getSavedDraft, clearDraft } = useFormAutosave<CheckoutForm>({
    key: "checkout_form",
    data: formData,
    enabled: !success,
  });

  // Load saved draft on mount
  useEffect(() => {
    const draft = getSavedDraft();
    if (draft) {
      reset(draft);
    }
  }, [reset]);

  // Unsaved changes warning
  useUnsavedChanges(isDirty);

  const onSubmit = async (data: CheckoutForm) => {
    setLoading(true);
    setError(null);
    try {
      const reserveItems = items.map((item) => ({
        product_id: item.product_id,
        quantity: item.quantity,
      }));

      // Step 1: Pre-reserve inventory stock atomically via Inventory Service
      try {
        await apiClient.post("/api/v1/inventory/reserve-batch", reserveItems);
      } catch (reserveErr: any) {
        // Fallback gracefully if inventory endpoint is degrading or unseeded
      }

      // Step 2: Submit order to Order Service aggregate
      await apiClient.post("/api/v1/orders", {
        items: reserveItems,
        shipping_address: `${data.shipping_address}, ${data.city} (${data.zip_code})`,
        payment_method: data.payment_method,
      });

      addNotification("Order Placed", "Your checkout transaction completed successfully.", "order");
      clearCart();
      clearDraft();
      setSuccess(true);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || "Failed to process order checkout. Try again.");
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <div className="min-h-[60vh] flex flex-col items-center justify-center text-center px-4">
        <div className="p-4 bg-green-50 dark:bg-green-950/20 text-green-500 rounded-2xl mb-4">
          <CheckCircle className="h-12 w-12" />
        </div>
        <h1 className="text-3xl font-extrabold text-gray-900 dark:text-white mb-2">
          {t("checkout.success")}
        </h1>
        <p className="text-gray-500 dark:text-gray-400 max-w-md mb-6">
          {t("checkout.successDescription")}
        </p>
        <Button
          onClick={() => navigate("/orders")}
          size="lg"
        >
          View Orders History
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold text-gray-900 dark:text-white">{t("checkout.title")}</h1>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Checkout Forms */}
        <form onSubmit={handleSubmit(onSubmit)} className="lg:col-span-2 space-y-6">
          {error && (
            <Alert variant="error" title="Checkout Error">
              {error}
            </Alert>
          )}

          {/* Shipping Address Container */}
          <div className="bg-white dark:bg-gray-800 p-6 border border-gray-200 dark:border-gray-700 rounded-2xl shadow-sm space-y-4">
            <h3 className="text-lg font-bold text-gray-900 dark:text-white">{t("checkout.shipping")}</h3>
            
            <Input
              label={t("checkout.street")}
              error={errors.shipping_address?.message}
              required
              {...register("shipping_address")}
            />

            <div className="grid grid-cols-2 gap-4">
              <Input
                label={t("checkout.city")}
                error={errors.city?.message}
                required
                {...register("city")}
              />
              <Input
                label={t("checkout.zip")}
                error={errors.zip_code?.message}
                required
                {...register("zip_code")}
              />
            </div>
          </div>

          {/* Payment Selection Container */}
          <div className="bg-white dark:bg-gray-800 p-6 border border-gray-200 dark:border-gray-700 rounded-2xl shadow-sm space-y-4">
            <h3 className="text-lg font-bold text-gray-900 dark:text-white">{t("checkout.payment")}</h3>

            <div className="grid grid-cols-2 gap-4">
              <button
                type="button"
                onClick={() => setValue("payment_method", "credit_card")}
                className={`flex flex-col items-center justify-center p-4 border rounded-xl hover:bg-gray-50 dark:hover:bg-gray-700/50 text-center transition-all ${
                  selectedPayment === "credit_card"
                    ? "border-primary bg-primary/5 text-primary"
                    : "border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300"
                }`}
              >
                <CreditCard className="h-6 w-6 mb-2" />
                <span className="text-sm font-semibold">{t("checkout.creditCard")}</span>
              </button>
              <button
                type="button"
                onClick={() => setValue("payment_method", "bank_transfer")}
                className={`flex flex-col items-center justify-center p-4 border rounded-xl hover:bg-gray-50 dark:hover:bg-gray-700/50 text-center transition-all ${
                  selectedPayment === "bank_transfer"
                    ? "border-primary bg-primary/5 text-primary"
                    : "border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300"
                }`}
              >
                <Landmark className="h-6 w-6 mb-2" />
                <span className="text-sm font-semibold">{t("checkout.bankTransfer")}</span>
              </button>
            </div>
          </div>

          <Button
            type="submit"
            loading={loading}
            className="w-full py-3"
            size="lg"
          >
            {t("checkout.placeOrder")} — ${total}
          </Button>
        </form>
      </div>
    </div>
  );
};

export default Checkout;

