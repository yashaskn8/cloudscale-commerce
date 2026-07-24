// Observability framework integration (OpenTelemetry + Sentry)
export interface PerformanceMetric {
  name: string;
  value: number;
  rating: "good" | "needs-improvement" | "poor";
}

class ObservabilityManager {
  private correlationId: string | null = null;

  constructor() {
    this.generateCorrelationId();
    this.setupWebVitals();
  }

  private generateCorrelationId() {
    this.correlationId = crypto.randomUUID();
    // Expose window context Sentry handler mock if needed
    if (typeof window !== "undefined") {
      (window as any).__CORRELATION_ID__ = this.correlationId;
      (window as any).__SENTRY_CAPTURE__ = (error: Error) => {
        console.error("[Sentry Mock Capture]", error, { correlationId: this.correlationId });
      };
    }
  }

  public getCorrelationId(): string {
    if (!this.correlationId) this.generateCorrelationId();
    return this.correlationId!;
  }

  public logEvent(name: string, attributes: Record<string, unknown> = {}) {
    console.log(`[Telemetry Event] ${name}:`, {
      ...attributes,
      correlationId: this.getCorrelationId(),
      timestamp: new Date().toISOString(),
    });
  }

  public logError(error: Error, attributes: Record<string, unknown> = {}) {
    console.error(`[Telemetry Error] ${error.message}:`, {
      ...attributes,
      correlationId: this.getCorrelationId(),
      stack: error.stack,
      timestamp: new Date().toISOString(),
    });
  }

  private setupWebVitals() {
    if (typeof window === "undefined" || !("PerformanceObserver" in window)) return;

    // Track Largest Contentful Paint (LCP)
    try {
      const lcpObserver = new PerformanceObserver((entryList) => {
        const entries = entryList.getEntries();
        const lastEntry = entries[entries.length - 1];
        this.logMetric("LCP", lastEntry.startTime);
      });
      lcpObserver.observe({ type: "largest-contentful-paint", buffered: true });
    } catch {}

    // Track First Input Delay (FID)
    try {
      const fidObserver = new PerformanceObserver((entryList) => {
        const entries = entryList.getEntries();
        entries.forEach((entry) => {
          this.logMetric("FID", entry.duration);
        });
      });
      fidObserver.observe({ type: "first-input", buffered: true });
    } catch {}

    // Track Cumulative Layout Shift (CLS)
    try {
      let clsValue = 0;
      const clsObserver = new PerformanceObserver((entryList) => {
        for (const entry of entryList.getEntries()) {
          if (!(entry as any).hadRecentInput) {
            clsValue += (entry as any).value as number;
          }
        }
        this.logMetric("CLS", clsValue);
      });
      clsObserver.observe({ type: "layout-shift", buffered: true });
    } catch {}
  }

  private logMetric(name: string, value: number) {
    let rating: "good" | "needs-improvement" | "poor" = "good";
    if (name === "LCP") {
      rating = value > 4000 ? "poor" : value > 2500 ? "needs-improvement" : "good";
    } else if (name === "FID") {
      rating = value > 300 ? "poor" : value > 100 ? "needs-improvement" : "good";
    } else if (name === "CLS") {
      rating = value > 0.25 ? "poor" : value > 0.1 ? "needs-improvement" : "good";
    }

    this.logEvent("web-vital", { metricName: name, metricValue: value, rating });
  }
}

export const observability = new ObservabilityManager();
export default observability;
