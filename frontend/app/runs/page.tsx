"use client";

import Link from "next/link";
import { useRuns } from "@/lib/api";
import { Header } from "@/components/layout/Header";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  PlusCircle,
  Clock,
  CheckCircle,
  Loader2,
  AlertCircle,
  ChevronRight,
} from "lucide-react";
import { formatDuration, formatTimestamp } from "@/lib/api";

export default function RunsListPage() {
  const { data: runs, isLoading, error } = useRuns();

  return (
    <>
      <Header
        title="Past Runs"
        description="View all completed competitive analysis runs"
        actions={
          <Link href="/runs/new">
            <Button>
              <PlusCircle className="h-4 w-4 mr-2" />
              New Analysis
            </Button>
          </Link>
        }
      />

      <div className="p-6">
        {isLoading ? (
          <div className="space-y-4">
            {Array.from({ length: 3 }).map((_, i) => (
              <Card key={i}>
                <CardContent className="py-4">
                  <Skeleton className="h-6 w-64 mb-2" />
                  <Skeleton className="h-4 w-48" />
                </CardContent>
              </Card>
            ))}
          </div>
        ) : error ? (
          <Card>
            <CardContent className="flex flex-col items-center justify-center py-12">
              <AlertCircle className="h-12 w-12 text-destructive mb-4" />
              <h2 className="text-lg font-semibold mb-2">Failed to load runs</h2>
              <p className="text-muted-foreground">
                Make sure the API server is running at http://localhost:8000
              </p>
            </CardContent>
          </Card>
        ) : runs && runs.length > 0 ? (
          <div className="space-y-4">
            {runs.map((run) => (
              <Link key={run.id} href={`/runs/${run.id}`}>
                <Card className="transition-colors hover:bg-muted/50 cursor-pointer">
                  <CardContent className="py-4">
                    <div className="flex items-center justify-between">
                      <div className="space-y-1">
                        <div className="flex items-center gap-3">
                          <h3 className="font-semibold">{run.id}</h3>
                          <StatusBadge status={run.status} />
                          {run.version === "v2" && (
                            <Badge variant="outline" className="text-xs">
                              V2 Relational
                            </Badge>
                          )}
                        </div>
                        <div className="flex items-center gap-4 text-sm text-muted-foreground">
                          <span className="flex items-center gap-1">
                            <Clock className="h-3.5 w-3.5" />
                            {formatTimestamp(run.created_at)}
                          </span>
                          <span>
                            {run.companies.length} companies × {run.variables.length} variables
                          </span>
                          {run.successful_cells !== undefined && (
                            <span>
                              {run.successful_cells}/{run.total_cells} cells
                            </span>
                          )}
                        </div>
                        <div className="flex items-center gap-2 pt-1">
                          {run.companies.map((company) => (
                            <Badge key={company} variant="outline" className="text-xs">
                              {company}
                            </Badge>
                          ))}
                        </div>
                      </div>
                      <ChevronRight className="h-5 w-5 text-muted-foreground" />
                    </div>
                  </CardContent>
                </Card>
              </Link>
            ))}
          </div>
        ) : (
          <Card>
            <CardContent className="flex flex-col items-center justify-center py-12">
              <div className="rounded-full bg-muted p-4 mb-4">
                <Clock className="h-8 w-8 text-muted-foreground" />
              </div>
              <h2 className="text-lg font-semibold mb-2">No runs yet</h2>
              <p className="text-muted-foreground mb-4">
                Start your first competitive analysis
              </p>
              <Link href="/runs/new">
                <Button>
                  <PlusCircle className="h-4 w-4 mr-2" />
                  New Analysis
                </Button>
              </Link>
            </CardContent>
          </Card>
        )}
      </div>
    </>
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
    case "failed":
      return (
        <Badge className="bg-red-100 text-red-800 hover:bg-red-100">
          <AlertCircle className="h-3 w-3 mr-1" />
          Failed
        </Badge>
      );
    default:
      return (
        <Badge variant="secondary">
          {status}
        </Badge>
      );
  }
}
