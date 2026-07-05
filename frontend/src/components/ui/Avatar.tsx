import React from "react";
import { cn } from "@/lib/utils";
import { User } from "lucide-react";

type AvatarSize = "xs" | "sm" | "md" | "lg" | "xl";

interface AvatarProps {
  src?: string | null;
  alt?: string;
  fallback?: string;
  size?: AvatarSize;
  status?: "online" | "offline" | "busy" | "away";
  className?: string;
}

const sizeStyles: Record<AvatarSize, string> = {
  xs: "h-6 w-6 text-xs",
  sm: "h-8 w-8 text-sm",
  md: "h-10 w-10 text-base",
  lg: "h-12 w-12 text-lg",
  xl: "h-16 w-16 text-xl",
};

const statusColors = {
  online: "bg-green-500",
  offline: "bg-gray-400",
  busy: "bg-red-500",
  away: "bg-amber-500",
};

function getInitials(name: string): string {
  return name
    .split(" ")
    .map((w) => w[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();
}

export function Avatar({ src, alt, fallback, size = "md", status, className }: AvatarProps) {
  const [imgError, setImgError] = React.useState(false);

  return (
    <div className={cn("relative inline-flex shrink-0", sizeStyles[size], className)}>
      {src && !imgError ? (
        <img
          src={src}
          alt={alt || "Avatar"}
          onError={() => setImgError(true)}
          className="h-full w-full rounded-full object-cover"
        />
      ) : fallback ? (
        <span className="flex h-full w-full items-center justify-center rounded-full bg-primary/10 text-primary font-semibold">
          {getInitials(fallback)}
        </span>
      ) : (
        <span className="flex h-full w-full items-center justify-center rounded-full bg-muted">
          <User className="h-1/2 w-1/2 text-muted-foreground" />
        </span>
      )}
      {status && (
        <span
          className={cn(
            "absolute bottom-0 right-0 h-1/4 w-1/4 min-h-2 min-w-2 rounded-full ring-2 ring-background",
            statusColors[status]
          )}
          aria-label={status}
        />
      )}
    </div>
  );
}
