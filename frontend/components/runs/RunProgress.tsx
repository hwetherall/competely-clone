"use client";

import { useEffect } from "react";
import { useRunProgress } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { ConfidenceBadge } from "@/components/common/ConfidenceBadge";
import { formatDuration } from "@/lib/api";
import {
  Loader2,
  CheckCircle,
  AlertCircle,
  Clock,
  Activity,
  ArrowRight,
} from "lucide-react";

interface RunProgressProps {
  runId: string;
  onComplete?: () => void;
}

export function RunProgress({ runId, onComplete }: RunProgressProps) {
  const { data: progress, isLoading, error } = useRunProgress(
    runId,
    true // Enable polling
  );

  // Call onComplete when run finishes
  useEffect(() => {
    if (progress?.status === "completed" && onComplete) {
      onComplete();
    }
  }, [progress?.status, onComplete]);

  if (isLoading) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </CardContent>
      </Card>
    );
  }

  if (error || !progress) {
    return (
      <Card>
        <CardContent className="flex flex-col items-center justify-center py-12">
          <AlertCircle className="h-8 w-8 text-muted-foreground mb-2" />
          <p className="text-muted-foreground">Failed to load progress</p>
        </CardContent>
      </Card>
    );
  }

  const { status, progress: progressData, elapsed_seconds, estimated_remaining_seconds, recent_activity } = progress;
  const percentComplete = progressData.total > 0 
    ? Math.round((progressData.completed / progressData.total) * 100) 
    : 0;

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">Run Progress</CardTitle>
          <StatusBadge status={status} />
        </div>
      </CardHeader>

      <CardContent className="space-y-6">
        {/* Progress Bar */}
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="font-medium">
              {progressData.completed}/{progressData.total} cells complete
            </span>
            <span className="text-muted-foreground">{percentComplete}%</span>
          </div>
          <Progress value={percentComplete} className="h-3" />
        </div>

        {/* Current Task */}
        {status === "running" && progressData.current && (
          <div className="rounded-lg border bg-muted/50 p-4">
            <p className="text-sm text-muted-foreground mb-1">Currently researching:</p>
            <div className="flex items-center gap-2">
              <Loader2 className="h-4 w-4 animate-spin text-primary" />
              {(progressData.current.company || progressData.current.variable) ? (
                <>
                  <span className="font-medium">{progressData.current.company}</span>
                  <ArrowRight className="h-4 w-4 text-muted-foreground" />
                  <span>{progressData.current.variable}</span>
                </>
              ) : (
                <span className="font-medium">
                  {progressData.current.step || "Starting..."}
                </span>
              )}
            </div>
            {progressData.current.step && (progressData.current.company || progressData.current.variable) && (
              <p className="mt-1 text-xs text-muted-foreground">
                {progressData.current.step}
              </p>
            )}
          </div>
        )}

        {/* Time Stats */}
        <div className="flex items-center gap-6 text-sm">
          <div className="flex items-center gap-2">
            <Clock className="h-4 w-4 text-muted-foreground" />
            <span>Elapsed: {formatDuration(elapsed_seconds)}</span>
          </div>
          {estimated_remaining_seconds !== undefined && estimated_remaining_seconds > 0 && status === "running" && (
            <div className="flex items-center gap-2">
              <Activity className="h-4 w-4 text-muted-foreground" />
              <span>Est. remaining: ~{formatDuration(estimated_remaining_seconds)}</span>
            </div>
          )}
        </div>

        <Separator />

        {/* Recent Activity */}
        <div>
          <h4 className="text-sm font-semibold mb-3">Recent Activity</h4>
          {recent_activity.length > 0 ? (
            <div className="space-y-2 max-h-[200px] overflow-y-auto">
              {recent_activity.slice().reverse().map((activity, index) => (
                <div
                  key={index}
                  className="flex items-center justify-between text-sm py-1"
                >
                  <div className="flex items-center gap-2">
                    {activity.status === "completed" ? (
                      <CheckCircle className="h-4 w-4 text-green-500" />
                    ) : activity.status === "failed" ? (
                      <AlertCircle className="h-4 w-4 text-red-500" />
                    ) : (
                      <Loader2 className="h-4 w-4 animate-spin text-blue-500" />
                    )}
                    <span className="font-medium">{activity.company}</span>
                    <span className="text-muted-foreground">-</span>
                    <span>{activity.variable}</span>
                  </div>
                  <ConfidenceBadge 
                    confidence={activity.confidence} 
                    className="text-xs"
                  />
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">
              No activity yet...
            </p>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

function StatusBadge({ status }: { status: string }) {
  switch (status) {
    case "completed":
      return (
        <Badge className="bg-green-100 text-green-800 hover:bg-green-100">
          <CheckCircle className="h-3 w-3 mr-1" />
          Completed
        </Badge>
      );
    case "running":
      return (
        <Badge className="bg-blue-100 text-blue-800 hover:bg-blue-100">
          <Loader2 className="h-3 w-3 mr-1 animate-spin" />
          Running
        </Badge>
      );
    case "pending":
      return (
        <Badge className="bg-yellow-100 text-yellow-800 hover:bg-yellow-100">
          <Clock className="h-3 w-3 mr-1" />
          Pending
        </Badge>
      );
    case "failed":
      return (
        <Badge className="bg-red-100 text-red-800 hover:bg-red-100">
          <AlertCircle className="h-3 w-3 mr-1" />
          Failed
        </Badge>
      );
    default:
      return <Badge variant="secondary">{status}</Badge>;
  }
}
