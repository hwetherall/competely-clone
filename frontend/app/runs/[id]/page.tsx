"use client";

import { use, useEffect } from "react";
import { useRun, useRunProgress } from "@/lib/api";
import { Header } from "@/components/layout/Header";
import { ResultsTable } from "@/components/runs/ResultsTable";
import { RunProgress } from "@/components/runs/RunProgress";
import { PageLoadingState } from "@/components/common/LoadingState";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Download,
  FileJson,
  FileSpreadsheet,
  FileText,
  Clock,
  CheckCircle,
  AlertCircle,
  RefreshCw,
} from "lucide-react";
import { formatDuration, formatTimestamp } from "@/lib/api";

interface PageProps {
  params: Promise<{ id: string }>;
}

export default function RunResultPage({ params }: PageProps) {
  const { id } = use(params);
  
  // Try to get the completed run data
  const { data, isLoading, error, refetch } = useRun(id);
  
  // Also check the progress status
  const { data: progress, isLoading: progressLoading } = useRunProgress(
    id,
    // Enable polling if we don't have data yet
    !data
  );

  // Determine if the run is still in progress
  const isInProgress = progress?.status === "running" || progress?.status === "pending";
  const isCompleted = data && !error;

  // Refetch when progress completes
  useEffect(() => {
    if (progress?.status === "completed" && !data) {
      refetch();
    }
  }, [progress?.status, data, refetch]);

  // If loading both, show loading state
  if (isLoading && progressLoading) {
    return (
      <>
        <Header title="Loading..." />
        <PageLoadingState />
      </>
    );
  }

  // If run is in progress, show the progress monitor
  if (isInProgress && !isCompleted) {
    return (
      <>
        <Header title={`Run: ${id}`} />
        <div className="p-6 space-y-6">
          <RunProgress 
            runId={id} 
            onComplete={() => {
              // Refetch the run data when complete
              refetch();
            }}
          />
          
          <p className="text-center text-sm text-muted-foreground">
            Results will appear here once the analysis is complete
          </p>
        </div>
      </>
    );
  }

  // If error and not in progress, show error
  // Wait for progress check to complete before showing error
  if (error && !isInProgress && !progressLoading) {
    return (
      <>
        <Header title="Error" />
        <div className="p-6">
          <Card>
            <CardContent className="flex flex-col items-center justify-center py-12">
              <AlertCircle className="h-12 w-12 text-destructive mb-4" />
              <h2 className="text-lg font-semibold mb-2">Failed to load results</h2>
              <p className="text-muted-foreground text-center mb-4">
                {error?.message || "The requested run could not be found."}
              </p>
              <Button onClick={() => refetch()} variant="outline">
                <RefreshCw className="h-4 w-4 mr-2" />
                Try Again
              </Button>
            </CardContent>
          </Card>
        </div>
      </>
    );
  }

  // No data yet
  if (!data) {
    return (
      <>
        <Header title="Loading..." />
        <PageLoadingState />
      </>
    );
  }

  const handleExport = (format: "json" | "csv" | "html") => {
    // For now, just link to the API - in production you'd implement proper download
    const baseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    window.open(`${baseUrl}/api/runs/${id}`, "_blank");
  };

  return (
    <>
      <Header
        title={`Results: ${id}`}
        actions={
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={() => handleExport("json")}>
              <FileJson className="h-4 w-4 mr-2" />
              JSON
            </Button>
            <Button variant="outline" size="sm" onClick={() => handleExport("csv")}>
              <FileSpreadsheet className="h-4 w-4 mr-2" />
              CSV
            </Button>
            <Button variant="outline" size="sm" onClick={() => handleExport("html")}>
              <FileText className="h-4 w-4 mr-2" />
              HTML
            </Button>
          </div>
        }
      />

      <div className="p-6 space-y-6">
        {/* Summary Card */}
        <Card>
          <CardContent className="py-4">
            <div className="flex flex-wrap items-center gap-6">
              {/* Status */}
              <div className="flex items-center gap-2">
                <CheckCircle className="h-5 w-5 text-green-500" />
                <span className="font-medium">Completed</span>
              </div>

              {/* Timestamp */}
              <div className="flex items-center gap-2 text-muted-foreground">
                <Clock className="h-4 w-4" />
                <span>{formatTimestamp(data.timestamp)}</span>
              </div>

              {/* Duration */}
              <div className="text-muted-foreground">
                Duration: {formatDuration(data.metadata.elapsed_seconds)}
              </div>

              {/* Stats */}
              <div className="flex items-center gap-2">
                <Badge variant="secondary">
                  {data.metadata.successful_cells}/{data.metadata.total_cells} cells
                </Badge>
                {data.metadata.failed_cells > 0 && (
                  <Badge variant="destructive">
                    {data.metadata.failed_cells} failed
                  </Badge>
                )}
              </div>

              {/* Companies */}
              <div className="flex items-center gap-2">
                {data.companies.map((company) => (
                  <Badge key={company} variant="outline">
                    {company}
                  </Badge>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Results Table */}
        <ResultsTable data={data} />

        {/* Help Text */}
        <p className="text-center text-sm text-muted-foreground">
          Click any cell to see the full analysis with sources
        </p>
      </div>
    </>
  );
}
