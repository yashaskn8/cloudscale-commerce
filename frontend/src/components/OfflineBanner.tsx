import { useState, useEffect } from "react";
import { WifiOff, Wifi } from "lucide-react";
import { cn } from "@/lib/utils";

export function OfflineBanner() {
  const [isOnline, setIsOnline] = useState(() => {
    if (typeof navigator === "undefined") return true;
    return navigator.onLine;
  });
  const [showStatus, setShowStatus] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined") return;

    const handleOnline = () => {
      setIsOnline(true);
      setShowStatus(true);
      // Hide back after 4 seconds
      const timer = setTimeout(() => setShowStatus(false), 4000);
      return () => clearTimeout(timer);
    };

    const handleOffline = () => {
      setIsOnline(false);
      setShowStatus(true);
    };

    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);

    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, []);

  if (!showStatus && isOnline) return null;

  return (
    <div
      role="status"
      aria-live="polite"
      className={cn(
        "fixed bottom-4 left-4 z-50 flex items-center gap-3 px-4 py-3 rounded-xl border shadow-xl transition-all duration-300 animate-in slide-in-from-bottom-10",
        isOnline
          ? "bg-green-500/10 border-green-500/30 text-green-700 dark:text-green-400"
          : "bg-red-500/10 border-red-500/30 text-red-700 dark:text-red-400"
      )}
    >
      {isOnline ? (
        <>
          <Wifi className="h-5 w-5 animate-pulse text-green-500" />
          <div className="text-xs">
            <span className="font-bold">Online Connection Restored</span>
            <p className="opacity-90">All real-time actions are operational.</p>
          </div>
        </>
      ) : (
        <>
          <WifiOff className="h-5 w-5 animate-bounce text-red-500" />
          <div className="text-xs">
            <span className="font-bold">Working Offline Mode</span>
            <p className="opacity-90">Changes will synchronize when connection resolves.</p>
          </div>
        </>
      )}
    </div>
  );
}
export default OfflineBanner;
