import React, { useEffect } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { useThemeStore } from "@/stores/themeStore";
import { GuestLayout } from "@/layouts/GuestLayout";
import { AppLayout } from "@/layouts/AppLayout";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { I18nProvider } from "@/i18n";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { RetryBoundary } from "@/components/RetryBoundary";
import { OfflineBanner } from "@/components/OfflineBanner";
import { OnboardingTour } from "@/components/OnboardingTour";
import { ShowcasePanel } from "@/components/ShowcasePanel";
import { ToastContainer, SkipToContent } from "@/components/ui";
import { registerServiceWorker } from "@/lib/registerSW";
import { initializeConfig, isFeatureEnabled } from "@/lib/config";

// Lazy-loaded page components for bundle optimization
const Login = React.lazy(() => import("@/pages/Login"));
const Dashboard = React.lazy(() => import("@/pages/Dashboard"));
const Catalog = React.lazy(() => import("@/pages/Catalog"));
const Cart = React.lazy(() => import("@/pages/Cart"));
const Checkout = React.lazy(() => import("@/pages/Checkout"));
const Orders = React.lazy(() => import("@/pages/Orders"));
const Inventory = React.lazy(() => import("@/pages/Inventory"));
const Users = React.lazy(() => import("@/pages/Users"));
const AdminDashboard = React.lazy(() => import("@/pages/AdminDashboard"));
const TenantAdmin = React.lazy(() => import("@/pages/TenantAdmin"));
const Landing = React.lazy(() => import("@/pages/Landing"));
const Unauthorized = React.lazy(() => import("@/pages/Unauthorized"));
const NotFound = React.lazy(() => import("@/pages/NotFound"));

// Initialize TanStack Query Client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 1000 * 60 * 5, // 5 minutes cache TTL
    },
  },
});

export const App: React.FC = () => {
  const { applyTheme } = useThemeStore();

  // Apply theme class (dark/light) on initial page load, register SW, and load config
  useEffect(() => {
    applyTheme();

    if (isFeatureEnabled("enablePWA")) {
      registerServiceWorker();
    }

    // Load runtime feature flags and kill switches
    initializeConfig();
  }, [applyTheme]);

  return (
    <ErrorBoundary>
      <I18nProvider>
        <QueryClientProvider client={queryClient}>
          <BrowserRouter>
            {/* Accessibility: Skip link for keyboard users */}
            <SkipToContent targetId="main-content" />

            <React.Suspense
              fallback={
                <div className="min-h-screen flex items-center justify-center bg-background" role="status" aria-label="Loading">
                  <div className="h-10 w-10 border-b-2 border-primary rounded-full animate-spin"></div>
                </div>
              }
            >
              <RetryBoundary maxRetries={3}>
                <Routes>
                  {/* ── Public Routes ─────────────────────────────────────────────────── */}
                  <Route path="/" element={<Landing />} />

                  {/* ── Guest Routes ────────────────────────────────────────────────── */}
                  <Route element={<GuestLayout />}>
                    <Route path="/login" element={<Login />} />
                  </Route>

                  {/* ── Protected Application Routes ────────────────────────────────── */}
                  <Route element={<ProtectedRoute />}>
                    <Route element={<AppLayout />}>
                      <Route path="/dashboard" element={<Dashboard />} />
                      <Route path="/products" element={<Catalog />} />
                      <Route path="/cart" element={<Cart />} />
                      <Route path="/checkout" element={<Checkout />} />
                      <Route path="/orders" element={<Orders />} />
                      <Route path="/inventory" element={<Inventory />} />
                      <Route path="/users" element={<Users />} />
                      <Route path="/admin" element={<AdminDashboard />} />
                      <Route path="/workspace" element={<TenantAdmin />} />
                      <Route path="/settings" element={<div className="text-xl font-bold dark:text-white">Settings Page</div>} />
                      <Route path="/unauthorized" element={<Unauthorized />} />
                    </Route>
                  </Route>

                  {/* ── Fallback Routes ──────────────────────────────────────────────── */}
                  <Route path="/404" element={<NotFound />} />
                  <Route path="*" element={<Navigate to="/404" replace />} />
                </Routes>
              </RetryBoundary>
            </React.Suspense>

            {/* Global overlays */}
            {isFeatureEnabled("enableOfflineBanner") && <OfflineBanner />}
            {isFeatureEnabled("enableOnboarding") && <OnboardingTour />}
            <ShowcasePanel />
          </BrowserRouter>
          <ToastContainer />
        </QueryClientProvider>
      </I18nProvider>
    </ErrorBoundary>
  );
};

export default App;
