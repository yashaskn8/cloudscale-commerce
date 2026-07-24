import { describe, it, expect, vi, beforeEach } from "vitest";
import React, { useState } from "react";
import { render, screen, fireEvent } from "@testing-library/react";

// Top-level mocks
vi.mock("@/lib/observability", () => ({
  observability: {
    logError: vi.fn(),
    getCorrelationId: vi.fn(() => "test-correlation-id"),
    logEvent: vi.fn(),
  },
}));

vi.mock("framer-motion", () => ({
  motion: {
    div: React.forwardRef(({ children, ...props }: any, ref: any) =>
      React.createElement("div", { ...props, ref }, children)
    ),
  },
  AnimatePresence: ({ children }: any) => children,
}));

import { ErrorBoundary } from "@/components/ErrorBoundary";
import { observability } from "@/lib/observability";
import { MetricCard } from "@/components/ui/MetricCard";
import { PageHeader } from "@/components/ui/PageHeader";

const ThrowingComponent = ({ shouldThrow }: { shouldThrow: boolean }) => {
  if (shouldThrow) throw new Error("Test crash");
  return <div>Healthy Content</div>;
};

describe("ErrorBoundary", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(console, "error").mockImplementation(() => {});
  });

  it("renders children when no error occurs", () => {
    render(
      <ErrorBoundary>
        <div>Safe content</div>
      </ErrorBoundary>
    );
    expect(screen.getByText("Safe content")).toBeTruthy();
  });

  it("renders fallback UI when child throws", () => {
    render(
      <ErrorBoundary>
        <ThrowingComponent shouldThrow={true} />
      </ErrorBoundary>
    );
    expect(screen.getByText("Something went wrong")).toBeTruthy();
    expect(screen.getByText("Try Again")).toBeTruthy();
    expect(screen.getByText("Reload Page")).toBeTruthy();
  });

  it("logs error to observability system on crash", () => {
    render(
      <ErrorBoundary>
        <ThrowingComponent shouldThrow={true} />
      </ErrorBoundary>
    );
    expect(observability.logError).toHaveBeenCalledTimes(1);
    const call = (observability.logError as any).mock.calls[0];
    expect(call[0]).toBeInstanceOf(Error);
    expect(call[0].message).toBe("Test crash");
    expect(call[1]).toHaveProperty("correlationId", "test-correlation-id");
  });

  it("recovers in-place when Try Again is clicked after fixing state", () => {
    const StatefulContainer = () => {
      const [shouldThrow, setShouldThrow] = useState(true);
      return (
        <div>
          <button onClick={() => setShouldThrow(false)}>Fix Error</button>
          <ErrorBoundary>
            <ThrowingComponent shouldThrow={shouldThrow} />
          </ErrorBoundary>
        </div>
      );
    };

    render(<StatefulContainer />);
    expect(screen.getByText("Something went wrong")).toBeTruthy();

    fireEvent.click(screen.getByText("Fix Error"));
    fireEvent.click(screen.getByText("Try Again"));
    expect(screen.getByText("Healthy Content")).toBeTruthy();
  });

  it("renders custom fallback when provided", () => {
    render(
      <ErrorBoundary fallback={<div>Custom fallback</div>}>
        <ThrowingComponent shouldThrow={true} />
      </ErrorBoundary>
    );
    expect(screen.getByText("Custom fallback")).toBeTruthy();
  });
});

describe("MetricCard", () => {
  it("renders title and value", () => {
    render(<MetricCard title="Revenue" value="$12,345" />);
    expect(screen.getByText("Revenue")).toBeTruthy();
    expect(screen.getByText("$12,345")).toBeTruthy();
  });

  it("shows loading skeleton when loading", () => {
    const { container } = render(<MetricCard title="Revenue" value="$0" loading={true} />);
    expect(container.querySelector(".animate-pulse")).toBeTruthy();
  });

  it("renders trend indicator", () => {
    render(<MetricCard title="Growth" value="42" trend="+14.8%" trendPositive={true} />);
    expect(screen.getByText("+14.8%")).toBeTruthy();
  });
});

describe("PageHeader", () => {
  it("renders title and subtitle", () => {
    render(<PageHeader title="Orders" subtitle="View your order history" />);
    expect(screen.getByText("Orders")).toBeTruthy();
    expect(screen.getByText("View your order history")).toBeTruthy();
  });

  it("renders action buttons", () => {
    render(
      <PageHeader
        title="Dashboard"
        actions={<button>Export</button>}
      />
    );
    expect(screen.getByText("Export")).toBeTruthy();
  });
});
