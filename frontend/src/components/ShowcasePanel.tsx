import React, { useState, useCallback } from "react";
import { useAuthStore } from "@/stores/authStore";
import { useTenantStore } from "@/stores/tenantStore";
import { useNotificationStore } from "@/stores/notificationStore";
import {
  Sparkles,
  X,
  Play,
  User,
  ShieldCheck,
  Store,
  RefreshCw,
  ChevronRight,
  Fingerprint,
  Zap,
  Database,
  Globe,
  Layers,
  Check,
} from "lucide-react";

// ── Demo Persona Definitions ───────────────────────────────────────────────────
const DEMO_PERSONAS = [
  {
    id: "admin",
    name: "Platform Admin",
    email: "admin@cloudscale.io",
    role: "admin" as const,
    icon: ShieldCheck,
    color: "from-red-500 to-rose-600",
    description: "Full platform access — workspace management, billing, user administration, and audit logs.",
  },
  {
    id: "merchant",
    name: "Merchant Operator",
    email: "merchant@acme-store.com",
    role: "merchant" as const,
    icon: Store,
    color: "from-blue-500 to-indigo-600",
    description: "Catalog management, order fulfillment, inventory tracking, and analytics dashboards.",
  },
  {
    id: "customer",
    name: "End Customer",
    email: "jane@example.com",
    role: "customer" as const,
    icon: User,
    color: "from-emerald-500 to-teal-600",
    description: "Product browsing, cart management, checkout flow, and order history.",
  },
];

// ── Architecture Highlights ────────────────────────────────────────────────────
const ARCHITECTURE_HIGHLIGHTS = [
  { icon: Layers, label: "Event-Driven Microservices", detail: "Saga orchestration, inbox/outbox, DLQ" },
  { icon: Database, label: "CQRS + Read Replicas", detail: "Write/read engine split, Redis caching" },
  { icon: Globe, label: "Multi-Tenant Isolation", detail: "Context-var middleware, row-level security" },
  { icon: Fingerprint, label: "Zero-Trust Auth", detail: "JWT rotation, RBAC, CSRF, MFA-ready" },
  { icon: Zap, label: "AI Recommendation Engine", detail: "Cosine similarity, Jaccard scoring" },
  { icon: RefreshCw, label: "Observability Stack", detail: "OpenTelemetry, Prometheus, structured logs" },
];

// ── Showcase Panel Component ───────────────────────────────────────────────────
export const ShowcasePanel: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [activePersona, setActivePersona] = useState<string | null>(null);
  const [seedingData, setSeedingData] = useState(false);
  const { addNotification } = useNotificationStore();
  const { switchTenant, upgradePlan } = useTenantStore();

  const handlePersonaSwitch = useCallback(
    (persona: (typeof DEMO_PERSONAS)[number]) => {
      setActivePersona(persona.id);
      // Simulate switching auth context
      const authStore = useAuthStore.getState();
      authStore.setUser({
        id: persona.id,
        email: persona.email,
        full_name: persona.name,
        role: persona.role,
      });

      addNotification({
        id: `persona-${Date.now()}`,
        title: "Demo Context Switched",
        message: `Now viewing as ${persona.name} (${persona.role})`,
        type: "info",
        read: false,
        timestamp: new Date().toISOString(),
      });
    },
    [addNotification]
  );

  const handleSeedData = useCallback(async () => {
    setSeedingData(true);
    // Set up demo workspace and upgrade plan for rich data
    switchTenant("demo-sandbox");
    upgradePlan("growth");

    // Simulate seeding delay
    await new Promise((r) => setTimeout(r, 1200));

    addNotification({
      id: `seed-${Date.now()}`,
      title: "Demo Data Seeded",
      message: "Sample products, orders, and inventory populated in demo-sandbox workspace",
      type: "success",
      read: false,
      timestamp: new Date().toISOString(),
    });

    setSeedingData(false);
  }, [addNotification, switchTenant, upgradePlan]);

  return (
    <>
      {/* ── Floating Trigger Button ──────────────────────────────────────────── */}
      <button
        onClick={() => setIsOpen(true)}
        className="fixed bottom-6 right-6 z-50 group flex items-center gap-2 px-4 py-3 bg-gradient-to-r from-violet-600 to-purple-600 text-white rounded-full shadow-2xl shadow-purple-500/25 hover:shadow-purple-500/40 hover:scale-105 active:scale-95 transition-all duration-200"
        aria-label="Open portfolio showcase panel"
      >
        <Sparkles className="h-5 w-5 animate-pulse" />
        <span className="text-sm font-semibold hidden sm:inline">Showcase</span>
      </button>

      {/* ── Slide-Over Drawer ────────────────────────────────────────────────── */}
      {isOpen && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm transition-opacity"
            onClick={() => setIsOpen(false)}
            aria-hidden="true"
          />

          {/* Panel */}
          <aside
            className="fixed right-0 top-0 bottom-0 z-50 w-full max-w-md bg-white dark:bg-gray-900 shadow-2xl overflow-y-auto animate-in slide-in-from-right duration-300"
            role="dialog"
            aria-label="Portfolio showcase panel"
          >
            {/* Header */}
            <div className="sticky top-0 z-10 bg-gradient-to-r from-violet-600 to-purple-600 p-6">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-lg font-bold text-white flex items-center gap-2">
                    <Sparkles className="h-5 w-5" />
                    CloudScale Commerce
                  </h2>
                  <p className="text-violet-200 text-sm mt-1">Enterprise SaaS Platform Demo</p>
                </div>
                <button
                  onClick={() => setIsOpen(false)}
                  className="p-2 rounded-lg text-white/80 hover:text-white hover:bg-white/10 transition-colors"
                  aria-label="Close showcase panel"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>
            </div>

            <div className="p-6 space-y-8">
              {/* ── Role Switcher ──────────────────────────────────────────────── */}
              <section>
                <h3 className="text-sm font-semibold text-gray-900 dark:text-white uppercase tracking-wider mb-3">
                  Demo Personas
                </h3>
                <p className="text-xs text-gray-500 dark:text-gray-400 mb-4">
                  Switch between user roles to experience different permission levels and UI views.
                </p>
                <div className="space-y-2">
                  {DEMO_PERSONAS.map((persona) => {
                    const PersonaIcon = persona.icon;
                    const isActive = activePersona === persona.id;
                    return (
                      <button
                        key={persona.id}
                        onClick={() => handlePersonaSwitch(persona)}
                        className={`w-full flex items-center gap-3 p-3 rounded-xl transition-all duration-200 text-left ${
                          isActive
                            ? "bg-primary/5 border-2 border-primary/30 shadow-sm"
                            : "bg-gray-50 dark:bg-gray-800 border-2 border-transparent hover:border-gray-200 dark:hover:border-gray-700"
                        }`}
                      >
                        <div className={`h-10 w-10 rounded-lg bg-gradient-to-br ${persona.color} flex items-center justify-center shrink-0`}>
                          <PersonaIcon className="h-5 w-5 text-white" />
                        </div>
                        <div className="min-w-0 flex-1">
                          <p className="text-sm font-semibold text-gray-900 dark:text-white">{persona.name}</p>
                          <p className="text-xs text-gray-500 dark:text-gray-400 truncate">{persona.description}</p>
                        </div>
                        {isActive ? (
                          <Check className="h-5 w-5 text-primary shrink-0" />
                        ) : (
                          <ChevronRight className="h-4 w-4 text-gray-400 shrink-0" />
                        )}
                      </button>
                    );
                  })}
                </div>
              </section>

              {/* ── Seed Demo Data ─────────────────────────────────────────────── */}
              <section>
                <h3 className="text-sm font-semibold text-gray-900 dark:text-white uppercase tracking-wider mb-3">
                  Quick Actions
                </h3>
                <button
                  onClick={handleSeedData}
                  disabled={seedingData}
                  className="w-full flex items-center justify-center gap-2 py-3 px-4 bg-gradient-to-r from-emerald-500 to-teal-500 text-white rounded-xl font-semibold text-sm hover:shadow-lg hover:shadow-emerald-500/25 hover:scale-[1.02] active:scale-[0.98] transition-all disabled:opacity-60"
                >
                  {seedingData ? (
                    <>
                      <RefreshCw className="h-4 w-4 animate-spin" />
                      Seeding Demo Data...
                    </>
                  ) : (
                    <>
                      <Play className="h-4 w-4" />
                      Seed Sample Data & Switch Workspace
                    </>
                  )}
                </button>
              </section>

              {/* ── Architecture Highlights ────────────────────────────────────── */}
              <section>
                <h3 className="text-sm font-semibold text-gray-900 dark:text-white uppercase tracking-wider mb-3">
                  Architecture Highlights
                </h3>
                <div className="grid grid-cols-1 gap-2">
                  {ARCHITECTURE_HIGHLIGHTS.map((item, idx) => {
                    const ItemIcon = item.icon;
                    return (
                      <div
                        key={idx}
                        className="flex items-center gap-3 p-3 bg-gray-50 dark:bg-gray-800 rounded-lg"
                      >
                        <ItemIcon className="h-5 w-5 text-violet-500 shrink-0" />
                        <div className="min-w-0">
                          <p className="text-sm font-medium text-gray-900 dark:text-white">{item.label}</p>
                          <p className="text-xs text-gray-500 dark:text-gray-400">{item.detail}</p>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </section>

              {/* ── Tech Stack ─────────────────────────────────────────────────── */}
              <section>
                <h3 className="text-sm font-semibold text-gray-900 dark:text-white uppercase tracking-wider mb-3">
                  Technology Stack
                </h3>
                <div className="flex flex-wrap gap-2">
                  {[
                    "React 19",
                    "TypeScript",
                    "Tailwind v4",
                    "Zustand",
                    "TanStack Query",
                    "FastAPI",
                    "SQLAlchemy",
                    "PostgreSQL",
                    "Redis",
                    "Kafka",
                    "gRPC",
                    "Docker",
                    "Kubernetes",
                    "OpenTelemetry",
                    "Prometheus",
                  ].map((tech) => (
                    <span
                      key={tech}
                      className="inline-flex items-center px-2.5 py-1 bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 rounded-md text-xs font-medium"
                    >
                      {tech}
                    </span>
                  ))}
                </div>
              </section>
            </div>
          </aside>
        </>
      )}
    </>
  );
};

export default ShowcasePanel;
