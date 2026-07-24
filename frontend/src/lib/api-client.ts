import axios, { AxiosError } from "axios";
import type { InternalAxiosRequestConfig } from "axios";
import { useAuthStore } from "@/stores/authStore";
import { useTenantStore } from "@/stores/tenantStore";
import { mapAPIError } from "./errorMapper";

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8001";

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    "Content-Type": "application/json",
  },
});

// Flag to prevent multiple concurrent token rotation calls
let isRefreshing = false;
let failedQueue: Array<{
  resolve: (token: string) => void;
  reject: (err: any) => void;
}> = [];

const processQueue = (error: any, token: string | null = null) => {
  failedQueue.forEach((prom) => {
    if (token) {
      prom.resolve(token);
    } else {
      prom.reject(error);
    }
  });
  failedQueue = [];
};

// ── 1. Request Interceptor ─────────────────────────────────────────────────────
import { observability } from "@/lib/observability";
import { getCSRFToken } from "@/lib/security";

apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const { accessToken } = useAuthStore.getState();
    if (accessToken && config.headers) {
      config.headers.Authorization = `Bearer ${accessToken}`;
    }
    
    // Inject consistent correlation header, CSRF validation headers, and Idempotency key for mutating requests
    if (config.headers) {
      config.headers["X-Correlation-ID"] = observability.getCorrelationId();
      config.headers["X-CSRF-Token"] = getCSRFToken();
      
      // Multi-tenant context propagation
      const { activeTenantId } = useTenantStore.getState();
      config.headers["X-Tenant-ID"] = activeTenantId;

      // Auto-generate Idempotency-Key for state-mutating HTTP methods
      const mutatingMethods = ["post", "put", "patch", "delete"];
      if (config.method && mutatingMethods.includes(config.method.toLowerCase())) {
        if (!config.headers["Idempotency-Key"]) {
          config.headers["Idempotency-Key"] = crypto.randomUUID ? crypto.randomUUID() : `idemp-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
        }
      }
    }
    
    // Track API trigger event
    observability.logEvent("api-request", { url: config.url, method: config.method });
    
    return config;
  },
  (error) => {
    observability.logError(new Error("Request configuration failed"), { error });
    return Promise.reject(error);
  }
);

// ── 2. Response Interceptor (Handling Token Rotation) ──────────────────────────

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

    // If response is 401 Unauthorized and not already retried
    if (error.response?.status === 401 && !originalRequest._retry) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({
            resolve: (token: string) => {
              if (originalRequest.headers) {
                originalRequest.headers.Authorization = `Bearer ${token}`;
              }
              resolve(apiClient(originalRequest));
            },
            reject: (err: any) => reject(err),
          });
        });
      }

      originalRequest._retry = true;
      isRefreshing = true;

      const { refreshToken, logout, setCredentials } = useAuthStore.getState();

      if (!refreshToken) {
        logout();
        return Promise.reject(error);
      }

      try {
        // Run token refresh query against Auth service
        const refreshResponse = await axios.post(`${API_BASE_URL}/api/v1/auth/refresh`, {
          refresh_token: refreshToken,
        });

        const { access_token, refresh_token: new_refresh_token, user } = refreshResponse.data;

        // Update local credentials store
        setCredentials(user, access_token, new_refresh_token);

        isRefreshing = false;
        processQueue(null, access_token);

        if (originalRequest.headers) {
          originalRequest.headers.Authorization = `Bearer ${access_token}`;
        }
        return apiClient(originalRequest);
      } catch (refreshError) {
        isRefreshing = false;
        processQueue(refreshError, null);
        logout();
        
        const mapped = mapAPIError(refreshError);
        observability.logError(new Error(`Refresh token rotation failed: ${mapped.message}`), { mapped });
        return Promise.reject(mapped);
      }
    }

    const mapped = mapAPIError(error);
    observability.logError(new Error(`API request failed: ${mapped.message}`), { mapped });
    return Promise.reject(mapped);
  }
);
