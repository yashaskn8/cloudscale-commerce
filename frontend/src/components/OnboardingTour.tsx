import { useState, useEffect } from "react";
import { ArrowRight, HelpCircle, X } from "lucide-react";
import { Button } from "./ui";

interface TourStep {
  target: string;
  title: string;
  content: string;
}

const TOUR_STEPS: TourStep[] = [
  {
    target: "dashboard-link",
    title: "Real-time Metrics",
    content: "Welcome! This dashboard logs spending metrics, orders completed, and monthly growths.",
  },
  {
    target: "catalog-link",
    title: "Unified Catalog",
    content: "View, filter, and buy merchandise. Add items directly to your shopping cart.",
  },
  {
    target: "command-link",
    title: "Command Shortcuts",
    content: "Type Ctrl + K anywhere on the platform to search pages, inventory records, or users.",
  },
];

export function OnboardingTour() {
  const [step, setStep] = useState(0);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const isCompleted = localStorage.getItem("cloudscale-tour-complete");
    if (!isCompleted) {
      // Delay presentation slightly for better user transition
      const timer = setTimeout(() => setVisible(true), 2500);
      return () => clearTimeout(timer);
    }
  }, []);

  const handleNext = () => {
    if (step < TOUR_STEPS.length - 1) {
      setStep(step + 1);
    } else {
      handleComplete();
    }
  };

  const handleComplete = () => {
    localStorage.setItem("cloudscale-tour-complete", "true");
    setVisible(false);
  };

  if (!visible) return null;

  const current = TOUR_STEPS[step];

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Welcome Tour"
      className="fixed bottom-6 right-6 z-50 max-w-sm w-full bg-card border rounded-2xl p-5 shadow-2xl animate-in slide-in-from-bottom-5 border-primary/20"
    >
      <div className="flex justify-between items-start gap-4 mb-3">
        <h4 className="font-extrabold text-sm text-foreground flex items-center gap-1.5">
          <HelpCircle className="h-4 w-4 text-primary" /> {current.title}
        </h4>
        <button
          onClick={handleComplete}
          className="text-muted-foreground hover:text-foreground p-0.5 rounded transition-colors"
          aria-label="Skip tour"
        >
          <X className="h-4 w-4" />
        </button>
      </div>
      <p className="text-xs text-muted-foreground leading-relaxed mb-4">
        {current.content}
      </p>
      <div className="flex items-center justify-between">
        <div className="text-[10px] text-muted-foreground font-mono">
          Step {step + 1} of {TOUR_STEPS.length}
        </div>
        <Button
          size="sm"
          onClick={handleNext}
          icon={<ArrowRight className="h-3.5 w-3.5" />}
        >
          {step === TOUR_STEPS.length - 1 ? "Complete" : "Next"}
        </Button>
      </div>
    </div>
  );
}
export default OnboardingTour;
