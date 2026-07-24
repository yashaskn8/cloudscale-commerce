import React from "react";
import { motion } from "framer-motion";
import { Badge } from "./Badge";

export interface MetricCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon?: React.ReactNode;
  badgeText?: string;
  badgeVariant?: "success" | "warning" | "destructive" | "info" | "default";
  trend?: string;
  trendPositive?: boolean;
  onClick?: () => void;
  loading?: boolean;
  className?: string;
}

export const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  subtitle,
  icon,
  badgeText,
  badgeVariant = "info",
  trend,
  trendPositive = true,
  onClick,
  loading = false,
  className = "",
}) => {
  return (
    <motion.div
      whileHover={{ y: onClick ? -4 : 0 }}
      onClick={onClick}
      className={`bg-card p-6 rounded-2xl border shadow-sm transition-colors space-y-4 ${
        onClick ? "cursor-pointer hover:bg-card/85" : ""
      } ${className}`}
    >
      <div className="flex justify-between items-start">
        {icon && (
          <div className="p-3 bg-primary/10 text-primary rounded-xl">
            {icon}
          </div>
        )}
        {badgeText && (
          <Badge variant={badgeVariant}>
            {badgeText}
          </Badge>
        )}
      </div>

      <div>
        <p className="text-xs text-muted-foreground font-semibold uppercase tracking-wider">
          {title}
        </p>
        {loading ? (
          <div className="h-8 w-24 bg-muted animate-pulse rounded mt-2" />
        ) : (
          <h3 className="text-3xl font-extrabold mt-1 text-foreground">
            {value}
          </h3>
        )}
        {(subtitle || trend) && (
          <p className="text-xs text-muted-foreground mt-1.5 flex items-center gap-1">
            {trend && (
              <span
                className={`font-semibold ${
                  trendPositive ? "text-green-500" : "text-amber-500"
                }`}
              >
                {trend}
              </span>
            )}
            {subtitle}
          </p>
        )}
      </div>
    </motion.div>
  );
};
