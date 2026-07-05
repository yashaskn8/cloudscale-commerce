/**
 * Enterprise Configuration System
 *
 * Provides runtime configuration, feature flags, kill switches,
 * maintenance mode detection, and build metadata for the frontend.
 */

// ── Build Metadata ─────────────────────────────────────────────────────────────

export const buildMeta = {
  version: import.meta.env.VITE_APP_VERSION || "1.0.0",
  buildTime: import.meta.env.VITE_BUILD_TIME || new Date().toISOString(),
  commitSha: import.meta.env.VITE_COMMIT_SHA || "dev",
  environment: import.meta.env.VITE_ENVIRONMENT || "development",
} as const;

// ── Feature Flags ──────────────────────────────────────────────────────────────

export interface FeatureFlags {
  enableWebSocket: boolean;
  enablePWA: boolean;
  enableOnboarding: boolean;
  enableSearchHistory: boolean;
  enableNotificationPreferences: boolean;
  enableVirtualizedTables: boolean;
  enableOfflineBanner: boolean;
  enableObservability: boolean;
  enableCSRFProtection: boolean;
}

const defaultFlags: FeatureFlags = {
  enableWebSocket: true,
  enablePWA: true,
  enableOnboarding: true,
  enableSearchHistory: true,
  enableNotificationPreferences: true,
  enableVirtualizedTables: true,
  enableOfflineBanner: true,
  enableObservability: true,
  enableCSRFProtection: true,
};

let runtimeFlags: Partial<FeatureFlags> = {};

/**
 * Load feature flags from a remote endpoint or environment variables.
 * Falls back to defaults if the fetch fails.
 */
export async function loadFeatureFlags(): Promise<FeatureFlags> {
  try {
    const flagsUrl = import.meta.env.VITE_FEATURE_FLAGS_URL;
    if (flagsUrl) {
      const response = await fetch(flagsUrl, { cache: "no-store" });
      if (response.ok) {
        runtimeFlags = await response.json();
      }
    }
  } catch {
    // Silently fall back to defaults
    console.warn("[Config] Feature flags endpoint unavailable, using defaults.");
  }
  return getFeatureFlags();
}

export function getFeatureFlags(): FeatureFlags {
  return { ...defaultFlags, ...runtimeFlags };
}

export function isFeatureEnabled(flag: keyof FeatureFlags): boolean {
  return getFeatureFlags()[flag];
}

// ── Kill Switches ──────────────────────────────────────────────────────────────

export interface KillSwitches {
  disableCheckout: boolean;
  disableRegistration: boolean;
  disableAdminPanel: boolean;
  maintenanceMode: boolean;
}

const defaultKillSwitches: KillSwitches = {
  disableCheckout: false,
  disableRegistration: false,
  disableAdminPanel: false,
  maintenanceMode: false,
};

let runtimeKillSwitches: Partial<KillSwitches> = {};

export async function loadKillSwitches(): Promise<KillSwitches> {
  try {
    const ksUrl = import.meta.env.VITE_KILL_SWITCHES_URL;
    if (ksUrl) {
      const response = await fetch(ksUrl, { cache: "no-store" });
      if (response.ok) {
        runtimeKillSwitches = await response.json();
      }
    }
  } catch {
    console.warn("[Config] Kill switches endpoint unavailable, using defaults.");
  }
  return getKillSwitches();
}

export function getKillSwitches(): KillSwitches {
  return { ...defaultKillSwitches, ...runtimeKillSwitches };
}

export function isMaintenanceMode(): boolean {
  return getKillSwitches().maintenanceMode;
}

// ── Environment Abstraction ────────────────────────────────────────────────────

export function isDevelopment(): boolean {
  return buildMeta.environment === "development";
}

export function isProduction(): boolean {
  return buildMeta.environment === "production";
}

export function isStaging(): boolean {
  return buildMeta.environment === "staging";
}

// ── Runtime Configuration Loader ───────────────────────────────────────────────

export async function initializeConfig(): Promise<void> {
  await Promise.all([loadFeatureFlags(), loadKillSwitches()]);

  if (isDevelopment()) {
    console.log("[Config] Build metadata:", buildMeta);
    console.log("[Config] Feature flags:", getFeatureFlags());
    console.log("[Config] Kill switches:", getKillSwitches());
  }
}
