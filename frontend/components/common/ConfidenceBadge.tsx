"use client";

import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

interface ConfidenceBadgeProps {
  confidence: string;
  showDot?: boolean;
  className?: string;
}

export function ConfidenceBadge({
  confidence,
  showDot = true,
  className,
}: ConfidenceBadgeProps) {
  const getStyles = () => {
    switch (confidence.toLowerCase()) {
      case "high":
        return {
          badge: "bg-green-100 text-green-800 border-green-200 hover:bg-green-100",
          dot: "bg-green-500",
        };
      case "medium":
        return {
          badge: "bg-yellow-100 text-yellow-800 border-yellow-200 hover:bg-yellow-100",
          dot: "bg-yellow-500",
        };
      case "low":
        return {
          badge: "bg-red-100 text-red-800 border-red-200 hover:bg-red-100",
          dot: "bg-red-500",
        };
      default:
        return {
          badge: "bg-gray-100 text-gray-800 border-gray-200 hover:bg-gray-100",
          dot: "bg-gray-400",
        };
    }
  };

  const styles = getStyles();

  return (
    <Badge variant="outline" className={cn(styles.badge, className)}>
      {showDot && (
        <span className={cn("mr-1.5 h-2 w-2 rounded-full", styles.dot)} />
      )}
      <span className="capitalize">{confidence}</span>
    </Badge>
  );
}
