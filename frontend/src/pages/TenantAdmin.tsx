import React, { useState, useMemo } from "react";
import { useTenantStore } from "@/stores/tenantStore";
import { useAuthStore } from "@/stores/authStore";
import {
  Building2,
  CreditCard,
  Shield,
  Activity,
  CheckCircle2,
  ArrowRight,
  Zap,
  Crown,
  Rocket,
  BarChart3,
  Clock,
  FileText,
  Sparkles,
} from "lucide-react";

// ── Plan Configuration ─────────────────────────────────────────────────────────
const PLANS = [
  {
    id: "free" as const,
    name: "Starter",
    price: 0,
    icon: Zap,
    color: "from-gray-500 to-gray-600",
    badge: "bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300",
    features: [
      "Up to 10 products",
      "Up to 15 orders/month",
      "Basic analytics",
      "Email support",
      "Single workspace",
    ],
    limits: { maxProducts: 10, maxOrders: 15 },
  },
  {
    id: "growth" as const,
    name: "Growth",
    price: 49,
    icon: Rocket,
    color: "from-purple-500 to-indigo-600",
    badge: "bg-purple-100 text-purple-700 dark:bg-purple-950/40 dark:text-purple-300",
    popular: true,
    features: [
      "Up to 100 products",
      "Up to 200 orders/month",
      "Advanced analytics & AI",
      "Priority support",
      "3 workspaces",
      "Custom domain",
    ],
    limits: { maxProducts: 100, maxOrders: 200 },
  },
  {
    id: "enterprise" as const,
    name: "Enterprise",
    price: 199,
    icon: Crown,
    color: "from-amber-500 to-orange-600",
    badge: "bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300",
    features: [
      "Up to 10,000 products",
      "Up to 20,000 orders/month",
      "Full AI & recommendation engine",
      "Dedicated account manager",
      "Unlimited workspaces",
      "SSO & SAML",
      "SLA guarantee",
      "Audit logs",
    ],
    limits: { maxProducts: 10000, maxOrders: 20000 },
  },
] as const;

// ── Simulated Audit Events ─────────────────────────────────────────────────────
const AUDIT_EVENTS = [
  { id: 1, action: "plan.upgraded", actor: "admin@company.com", detail: "Plan upgraded from Starter to Growth", ts: "2 hours ago", severity: "info" as const },
  { id: 2, action: "user.invited", actor: "admin@company.com", detail: "Invited dev@company.com as Editor", ts: "5 hours ago", severity: "info" as const },
  { id: 3, action: "product.bulk_import", actor: "ops@company.com", detail: "Imported 47 products via CSV", ts: "1 day ago", severity: "info" as const },
  { id: 4, action: "security.mfa_enabled", actor: "admin@company.com", detail: "Enabled MFA for organization", ts: "2 days ago", severity: "success" as const },
  { id: 5, action: "billing.invoice_paid", actor: "system", detail: "Invoice #INV-2026-0042 paid — $49.00", ts: "3 days ago", severity: "success" as const },
  { id: 6, action: "quota.warning", actor: "system", detail: "Product catalog at 87% capacity", ts: "4 days ago", severity: "warning" as const },
];

// ── Usage Meter Component ──────────────────────────────────────────────────────
const UsageMeter: React.FC<{
  label: string;
  current: number;
  max: number;
  unit: string;
  isSecondary?: boolean;
}> = ({ label, current, max, unit, isSecondary }) => {
  const percentage = Math.min((current / max) * 100, 100);

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-sm">
        <span className="font-medium text-gray-400">{label}</span>
        <span className="text-gray-300 font-mono">
          {current.toLocaleString()} / {max.toLocaleString()} {unit}
        </span>
      </div>
      <div className="h-2.5 bg-white/5 rounded-full overflow-hidden progress-track">
        <div
          className={`h-full rounded-full transition-all duration-1000 ease-out ${
            isSecondary ? "progress-fill-secondary" : "progress-fill-primary"
          }`}
          style={{ width: `${percentage}%` }}
          role="progressbar"
          aria-valuenow={current}
          aria-valuemin={0}
          aria-valuemax={max}
          aria-label={`${label}: ${current} of ${max} ${unit} used`}
        />
      </div>
      {percentage >= 90 && (
        <p className="text-xs text-red-400 font-medium animate-pulse">
          ⚠ Critical Quota Alert — upgrade plan immediately
        </p>
      )}
    </div>
  );
};

// ── Severity Badge ─────────────────────────────────────────────────────────────
const SeverityDot: React.FC<{ severity: "info" | "success" | "warning" }> = ({ severity }) => {
  const colors = {
    info: "bg-indigo-400 shadow-[0_0_8px_#6366f1]",
    success: "bg-emerald-400 shadow-[0_0_8px_#10b981]",
    warning: "bg-amber-400 shadow-[0_0_8px_#f59e0b]",
  };
  return <span className={`inline-block w-2.5 h-2.5 rounded-full ${colors[severity]}`} />;
};

// ── Main Component ─────────────────────────────────────────────────────────────
const TenantAdmin: React.FC = () => {
  const { activeTenantId, planTier, limits, upgradePlan, switchTenant } = useTenantStore();
  const { user } = useAuthStore();
  const [selectedTab, setSelectedTab] = useState<"overview" | "billing" | "audit">("overview");
  const [isUpgrading, setIsUpgrading] = useState(false);

  // Simulated usage data — in production, these come from quota API
  const usage = useMemo(
    () => ({
      products: Math.min(Math.floor(limits.maxProducts * 0.63), limits.maxProducts),
      orders: Math.min(Math.floor(limits.maxOrders * 0.41), limits.maxOrders),
    }),
    [limits]
  );

  const currentPlan = PLANS.find((p) => p.id === planTier) ?? PLANS[0];

  const handlePlanUpgrade = async (tier: "free" | "growth" | "enterprise") => {
    if (tier === planTier) return;
    setIsUpgrading(true);
    // Simulate API call latency
    await new Promise((r) => setTimeout(r, 800));
    upgradePlan(tier);
    setIsUpgrading(false);
  };

  const tabs = [
    { id: "overview" as const, label: "Overview", icon: BarChart3 },
    { id: "billing" as const, label: "Billing & Plans", icon: CreditCard },
    { id: "audit" as const, label: "Audit Log", icon: Shield },
  ];

  return (
    <div className="relative min-h-[calc(100vh-120px)] space-y-6 text-gray-200">
      {/* Ambient Background Glows */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden z-0">
        <div className="absolute top-[-10%] left-[-10%] w-[350px] h-[350px] bg-purple-500/10 rounded-full blur-[100px]" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[350px] h-[350px] bg-emerald-500/5 rounded-full blur-[100px]" />
      </div>

      <div className="relative z-10 space-y-6">
        {/* ── Page Header ────────────────────────────────────────────────────────── */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-white flex items-center gap-2 tracking-tight">
              <Building2 className="h-7 w-7 text-primary text-glow-primary" />
              Workspace Administration
            </h1>
            <p className="text-sm text-gray-400 mt-1">
              Configure multi-tenant routing, plan tiers, limits, and security logs
            </p>
          </div>
          <div className="flex items-center gap-3">
            <span className="inline-flex items-center px-3 py-1.5 rounded-full text-xs font-semibold bg-white/5 border border-white/10 text-white shadow-inner">
              <currentPlan.icon className="h-3.5 w-3.5 mr-1.5 text-primary text-glow-primary animate-pulse" />
              {currentPlan.name} Plan
            </span>
            <span className="text-xs text-gray-400 font-mono bg-white/5 border border-white/5 px-2.5 py-1 rounded">
              {activeTenantId}
            </span>
          </div>
        </div>

        {/* ── Tab Navigation ─────────────────────────────────────────────────────── */}
        <div className="border-b border-white/10">
          <nav className="flex gap-6" aria-label="Admin sections">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setSelectedTab(tab.id)}
                className={`flex items-center gap-2 pb-3 px-1 text-sm font-medium border-b-2 transition-colors relative ${
                  selectedTab === tab.id
                    ? "border-primary text-primary text-glow-primary font-semibold"
                    : "border-transparent text-gray-400 hover:text-gray-200"
                }`}
                aria-current={selectedTab === tab.id ? "page" : undefined}
              >
                {selectedTab === tab.id && (
                  <span className="absolute bottom-0 left-0 right-0 h-[2px] bg-primary shadow-[0_0_8px_#a3a6ff]" />
                )}
                <tab.icon className="h-4 w-4" />
                {tab.label}
              </button>
            ))}
          </nav>
        </div>

        {/* ── Tab Content ────────────────────────────────────────────────────────── */}

        {/* Overview Tab */}
        {selectedTab === "overview" && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Organization Info */}
            <div className="lg:col-span-2 glass-panel rounded-xl p-6 space-y-6 relative">
              <div className="absolute top-0 left-0 right-0 h-[1px] bg-gradient-to-r from-white/20 via-white/5 to-transparent" />
              
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold text-white flex items-center gap-2">
                  <Sparkles className="h-5 w-5 text-primary text-glow-primary" />
                  Workspace Details
                </h2>
                <Activity className="h-5 w-5 text-emerald-400 text-glow-secondary animate-pulse" />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 text-sm">
                <div>
                  <label className="text-gray-400 text-xs uppercase tracking-wider font-semibold">Workspace Name</label>
                  <p className="mt-1 font-medium text-white">CloudScale Commerce</p>
                </div>
                <div>
                  <label className="text-gray-400 text-xs uppercase tracking-wider font-semibold">Administrator</label>
                  <p className="mt-1 font-medium text-white">{user?.full_name ?? "Administrator"}</p>
                </div>
                <div>
                  <label className="text-gray-400 text-xs uppercase tracking-wider font-semibold">Tenant Context ID</label>
                  <p className="mt-1 font-mono text-xs text-primary text-glow-primary">{activeTenantId}</p>
                </div>
                <div>
                  <label className="text-gray-400 text-xs uppercase tracking-wider font-semibold">Region</label>
                  <p className="mt-1 font-medium text-white">us-east-1 (Virginia)</p>
                </div>
              </div>

              <hr className="border-white/5" />

              {/* Usage Meters */}
              <div className="space-y-4">
                <h3 className="text-sm font-semibold text-gray-300">Resource Utilization Limits</h3>
                <UsageMeter label="Products Catalog Limit" current={usage.products} max={limits.maxProducts} unit="items" />
                <UsageMeter label="Monthly Orders Quota" current={usage.orders} max={limits.maxOrders} unit="orders" isSecondary />
              </div>
            </div>

            {/* Quick Stats Sidebar */}
            <div className="space-y-4">
              <div className="glass-panel-elevated rounded-xl p-5 relative">
                <div className="absolute top-0 left-0 right-0 h-[1px] bg-gradient-to-r from-white/20 via-white/5 to-transparent" />
                
                <div className="flex items-center gap-3 mb-4">
                  <div className={`h-10 w-10 rounded-lg bg-gradient-to-br ${currentPlan.color} flex items-center justify-center`}>
                    <currentPlan.icon className="h-5 w-5 text-white" />
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-white">{currentPlan.name}</p>
                    <p className="text-xs text-gray-400">
                      {currentPlan.price === 0 ? "Free forever" : `$${currentPlan.price}/mo`}
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => setSelectedTab("billing")}
                  className="w-full mt-2 text-sm text-primary hover:text-primary/80 font-medium flex items-center justify-center gap-1 py-2.5 rounded-lg border border-primary/20 hover:bg-primary/5 transition-colors shadow-inner"
                >
                  Manage Plan <ArrowRight className="h-3.5 w-3.5" />
                </button>
              </div>

              <div className="glass-panel rounded-xl p-5 space-y-3 relative">
                <div className="absolute top-0 left-0 right-0 h-[1px] bg-gradient-to-r from-white/20 via-white/5 to-transparent" />
                
                <h3 className="text-sm font-semibold text-white">Active Tenant Switcher</h3>
                <div className="space-y-2">
                  {["default-tenant", "acme-corp", "demo-sandbox"].map((tid) => (
                    <button
                      key={tid}
                      onClick={() => switchTenant(tid)}
                      className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors border ${
                        activeTenantId === tid
                          ? "bg-primary/10 text-primary font-semibold border-primary/30 glow-border-primary"
                          : "text-gray-400 hover:bg-white/5 border-transparent"
                      }`}
                    >
                      <Building2 className="h-4 w-4" />
                      <span className="font-mono text-xs truncate">{tid}</span>
                      {activeTenantId === tid && <CheckCircle2 className="h-4 w-4 ml-auto text-primary" />}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Billing Tab */}
        {selectedTab === "billing" && (
          <div className="space-y-6">
            {/* Plan Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {PLANS.map((plan) => {
                const isActive = plan.id === planTier;
                const PlanIcon = plan.icon;
                return (
                  <div
                    key={plan.id}
                    className={`relative rounded-xl border-2 transition-all duration-300 p-6 flex flex-col ${
                      isActive
                        ? "glass-panel-elevated glow-border-primary border-2 shadow-lg scale-[1.02]"
                        : "glass-panel border-transparent hover:border-white/10"
                    }`}
                  >
                    {plan.popular && (
                      <span className="absolute -top-3 left-1/2 -translate-x-1/2 bg-gradient-to-r from-emerald-500 to-teal-500 text-white text-[10px] font-bold px-3 py-0.5 rounded-full uppercase tracking-wider shadow-[0_0_10px_#10b981]">
                        Most Popular
                      </span>
                    )}
                    <div className="flex items-center gap-3 mb-4">
                      <div className={`h-10 w-10 rounded-lg bg-gradient-to-br ${plan.color} flex items-center justify-center shrink-0`}>
                        <PlanIcon className="h-5 w-5 text-white" />
                      </div>
                      <div>
                        <h3 className="font-semibold text-white">{plan.name}</h3>
                        <p className="text-2xl font-bold text-white">
                          {plan.price === 0 ? "Free" : `$${plan.price}`}
                          {plan.price > 0 && <span className="text-sm font-normal text-gray-400">/mo</span>}
                        </p>
                      </div>
                    </div>

                    <ul className="space-y-2 mb-6 flex-1">
                      {plan.features.map((f, i) => (
                        <li key={i} className="flex items-start gap-2 text-sm text-gray-400">
                          <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0 mt-0.5" />
                          {f}
                        </li>
                      ))}
                    </ul>

                    <button
                      onClick={() => handlePlanUpgrade(plan.id)}
                      disabled={isActive || isUpgrading}
                      className={`w-full py-2.5 rounded-lg text-sm font-semibold transition-all ${
                        isActive
                          ? "bg-white/5 border border-white/10 text-gray-400 cursor-default"
                          : `bg-gradient-to-r ${plan.color} text-white hover:shadow-lg hover:scale-[1.02] active:scale-[0.98]`
                      } disabled:opacity-60`}
                    >
                      {isActive ? "Current Plan" : isUpgrading ? "Upgrading..." : "Select Plan"}
                    </button>
                  </div>
                );
              })}
            </div>

            {/* Invoice History */}
            <div className="glass-panel rounded-xl p-6 relative">
              <div className="absolute top-0 left-0 right-0 h-[1px] bg-gradient-to-r from-white/20 via-white/5 to-transparent" />
              
              <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                <FileText className="h-5 w-5 text-primary text-glow-primary" />
                Invoice History
              </h3>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-white/5">
                      <th className="text-left py-3 px-4 text-xs uppercase tracking-wider text-gray-400 font-semibold">Invoice</th>
                      <th className="text-left py-3 px-4 text-xs uppercase tracking-wider text-gray-400 font-semibold">Date</th>
                      <th className="text-left py-3 px-4 text-xs uppercase tracking-wider text-gray-400 font-semibold">Plan</th>
                      <th className="text-right py-3 px-4 text-xs uppercase tracking-wider text-gray-400 font-semibold">Amount</th>
                      <th className="text-right py-3 px-4 text-xs uppercase tracking-wider text-gray-400 font-semibold">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5">
                    {[
                      { id: "INV-2026-0042", date: "Jul 1, 2026", plan: "Growth", amount: 49.0, status: "paid" },
                      { id: "INV-2026-0035", date: "Jun 1, 2026", plan: "Growth", amount: 49.0, status: "paid" },
                      { id: "INV-2026-0028", date: "May 1, 2026", plan: "Starter", amount: 0.0, status: "free" },
                    ].map((inv) => (
                      <tr key={inv.id} className="hover:bg-white/5 transition-colors">
                        <td className="py-3 px-4 font-mono text-xs text-primary">{inv.id}</td>
                        <td className="py-3 px-4 text-gray-400">{inv.date}</td>
                        <td className="py-3 px-4 text-gray-300">{inv.plan}</td>
                        <td className="py-3 px-4 text-right font-semibold text-white">
                          {inv.amount === 0 ? "—" : `$${inv.amount.toFixed(2)}`}
                        </td>
                        <td className="py-3 px-4 text-right">
                          <span
                            className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                              inv.status === "paid"
                                ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                                : "bg-white/5 text-gray-400 border border-white/10"
                            }`}
                          >
                            {inv.status === "paid" ? "Paid" : "Free Tier"}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* Audit Log Tab */}
        {selectedTab === "audit" && (
          <div className="glass-panel rounded-xl p-6 relative">
            <div className="absolute top-0 left-0 right-0 h-[1px] bg-gradient-to-r from-white/20 via-white/5 to-transparent" />
            
            <h3 className="text-lg font-semibold text-white mb-6 flex items-center gap-2">
              <Shield className="h-5 w-5 text-primary text-glow-primary" />
              Security & Audit Timeline
            </h3>
            <div className="space-y-0">
              {AUDIT_EVENTS.map((event, idx) => (
                <div key={event.id} className="flex gap-4 group">
                  {/* Timeline Line */}
                  <div className="flex flex-col items-center">
                    <SeverityDot severity={event.severity} />
                    {idx < AUDIT_EVENTS.length - 1 && (
                      <div className="w-px flex-1 bg-white/5 my-1" />
                    )}
                  </div>

                  {/* Event Content */}
                  <div className="pb-5 -mt-1">
                    <p className="text-sm font-medium text-white">{event.detail}</p>
                    <div className="flex items-center gap-2 mt-0.5">
                      <span className="text-xs font-mono text-primary">{event.action}</span>
                      <span className="text-xs text-gray-500">·</span>
                      <span className="text-xs text-gray-400">{event.actor}</span>
                      <span className="text-xs text-gray-500">·</span>
                      <span className="text-xs text-gray-400 flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        {event.ts}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default TenantAdmin;
