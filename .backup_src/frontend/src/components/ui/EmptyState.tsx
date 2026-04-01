import React from "react";
import { cn } from "@/lib/utils";
import { Inbox, Search, AlertTriangle, WifiOff, FileQuestion } from "lucide-react";

type EmptyVariant = "default" | "search" | "error" | "offline" | "notfound";

interface EmptyStateProps {
  variant?: EmptyVariant;
  title?: string;
  description?: string;
  icon?: React.ReactNode;
  action?: React.ReactNode;
  className?: string;
}

const defaultIcons: Record<EmptyVariant, React.ReactNode> = {
  default: <Inbox className="h-12 w-12" />,
  search: <Search className="h-12 w-12" />,
  error: <AlertTriangle className="h-12 w-12" />,
  offline: <WifiOff className="h-12 w-12" />,
  notfound: <FileQuestion className="h-12 w-12" />,
};

const defaultTitles: Record<EmptyVariant, string> = {
  default: "No data yet",
  search: "No results found",
  error: "Something went wrong",
  offline: "You're offline",
  notfound: "Not found",
};

const defaultDescriptions: Record<EmptyVariant, string> = {
  default: "There's nothing here at the moment. Try adding some items.",
  search: "Try adjusting your search or filters to find what you're looking for.",
  error: "We encountered an error. Please try again later.",
  offline: "Check your internet connection and try again.",
  notfound: "The resource you're looking for doesn't exist.",
};

export function EmptyState({ variant = "default", title, description, icon, action, className }: EmptyStateProps) {
  return (
    <div className={cn("flex flex-col items-center justify-center py-16 px-4 text-center", className)}>
      <div className="text-muted-foreground/50 mb-4">
        {icon || defaultIcons[variant]}
      </div>
      <h3 className="text-lg font-semibold text-foreground mb-1">
        {title || defaultTitles[variant]}
      </h3>
      <p className="text-sm text-muted-foreground max-w-sm mb-6">
        {description || defaultDescriptions[variant]}
      </p>
      {action}
    </div>
  );
}
