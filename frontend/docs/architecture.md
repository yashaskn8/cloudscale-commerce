# CloudScale Commerce — Enterprise Frontend Architecture & Developer Guide

Production-grade frontend architecture documentation for the CloudScale Commerce React 19 / TypeScript application.

---

## 1. Architectural Overview & Design Principles

The frontend application is built as a highly responsive, multi-tenant enterprise SaaS interface.

### Core Stack:
- **UI Framework**: React 19 with TypeScript (~6.0)
- **Routing**: React Router v7 (`react-router`) with route-level `React.lazy()` code splitting and Suspense fallbacks
- **State Management**:
  - **Zustand** (`v5`): Lightweight, transient UI state management (`authStore`, `cartStore`, `tenantStore`, `themeStore`, `notificationStore`, `uiStore`, `searchStore`, `wishlistStore`).
  - **TanStack Query** (`v5`): Server entity caching, background refetching, optimistic updates, and invalidations.
- **Styling**: Tailwind CSS (`v4`) with CSS variables (`hsl(var(...))`) for dynamic Dark/Light mode tokens.
- **Primitives**: Radix UI headless components combined into design system primitives under `components/ui`.
- **HTTP Client**: Axios with automated authorization, correlation tracking (`X-Correlation-ID`), CSRF validation (`X-CSRF-Token`), multi-tenant header propagation (`X-Tenant-ID`), and automatic `Idempotency-Key` UUID generation.

---

## 2. Design System Governance & Component Primitives

All reusable UI primitives reside strictly in `src/components/ui/` as a single source of truth.

### Primary UI Primitives:
- **`PageHeader`**: Standardized page headers, title, subtitle, breadcrumb navigation, and responsive actions.
- **`MetricCard`**: Standardized KPI cards with glassmorphic styling, trend indicators, icons, and micro-animations.
- **`FilterBar`**: Standardized search, filter chips, and sorting controls across views.
- **`DataTable`**: Enterprise data table supporting loading skeletons, empty state illustrations, sorting, pagination, column visibility, keyboard navigation, and virtualization (`useVirtualizer`).

---

## 3. Data Fetching & Query Architecture Standards

All server interactions strictly enforce predictable state handling:

```ts
// Example Query Configuration
const { data, isLoading, isError, refetch } = useQuery({
  queryKey: ["orders", tenantId, filters],
  queryFn: () => apiClient.get("/api/v1/orders"),
  staleTime: 1000 * 60 * 5, // 5 minutes cache
  gcTime: 1000 * 60 * 30, // 30 minutes garbage collection
  retry: 1,
});
```

### Mutation Rules:
- **Optimistic Updates**: Apply state updates optimistically and rollback on error via `onError` context handlers.
- **Cache Invalidation**: Trigger targeted `queryClient.invalidateQueries({ queryKey })` upon successful mutation.
- **Feedback**: Emit standardized toasts via `useToastStore` / `toast()`.

---

## 4. Frontend Security & Observability

### Security Protocols:
- **Token Security**: JWT access tokens are managed in memory/Zustand; logout triggers server-side revocation (`POST /api/v1/auth/logout`) to blacklist the token `jti` in Redis.
- **CSRF & Correlation**: Automatically inject `X-CSRF-Token` and `X-Correlation-ID` into every HTTP request header.
- **Zero Trust Client**: All client-side route guards (`ProtectedRoute`, `RoleChecker`) mirror backend security policies.

### Observability:
- **Uncaught Error Capture**: Global `ErrorBoundary` catches unexpected React render crashes and logs errors to `observability.logError()`.
- **Unhandled Promise Rejections**: Captured via global `window.onunhandledrejection` handlers.

---

## 5. Testing & Quality Assurance

### Vitest Unit & Integration Tests:
```bash
npm run test
```
Tests cart store operations, security encryption, local storage corruption detection, and component rendering.

### Playwright End-to-End Tests:
```bash
npm run test:e2e
```
Tests end-to-end user journeys: Authentication, Catalog browsing, Cart management, Checkout flow, Dashboard analytics, and Tenant context switching.

---

## 6. Build & Bundle Optimization

```bash
npm run build
```
Vite applies manual chunk splitting (`vendor-react`, `vendor-recharts`, `vendor-motion`, `vendor-tanstack`, `vendor-icons`) to minimize initial JavaScript parse times and deliver sub-2.5s LCP performance.
