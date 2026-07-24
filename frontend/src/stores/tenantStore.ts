import { create } from "zustand";
import { persist } from "zustand/middleware";

interface TenantLimits {
  maxProducts: number;
  maxOrders: number;
}

interface TenantState {
  activeTenantId: string;
  planTier: "free" | "growth" | "enterprise";
  limits: TenantLimits;
  switchTenant: (tenantId: string) => void;
  upgradePlan: (tier: "free" | "growth" | "enterprise") => void;
  resetTenant: () => void;
}

const PLAN_LIMITS: Record<"free" | "growth" | "enterprise", TenantLimits> = {
  free: { maxProducts: 10, maxOrders: 15 },
  growth: { maxProducts: 100, maxOrders: 200 },
  enterprise: { maxProducts: 10000, maxOrders: 20000 },
};

export const useTenantStore = create<TenantState>()(
  persist(
    (set) => ({
      activeTenantId: "default-tenant",
      planTier: "free",
      limits: PLAN_LIMITS.free,

      switchTenant: (tenantId) => {
        set({ activeTenantId: tenantId });
      },

      upgradePlan: (tier) => {
        set({
          planTier: tier,
          limits: PLAN_LIMITS[tier]
        });
      },

      resetTenant: () => {
        set({
          activeTenantId: "default-tenant",
          planTier: "free",
          limits: PLAN_LIMITS.free
        });
      }
    }),
    {
      name: "cloudscale-tenant-store",
    }
  )
);
export default useTenantStore;
