"use client";

import Link from "next/link";
import { useRuns } from "@/lib/api";
import { Header } from "@/components/layout/Header";
import { RunProgress } from "@/components/runs/RunProgress";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  PlusCircle,
  History,
  TrendingUp,
  Clock,
  CheckCircle,
  BarChart3,
  ArrowRight,
} from "lucide-react";
import { formatTimestamp, formatDuration } from "@/lib/api";

export default function DashboardPage() {
  const { data: runs, isLoading } = useRuns();

  // Find any currently running run
  const runningRun = runs?.find((r) => r.status === "running" || r.status === "pending");
  
  // Get recent completed runs
  const recentRuns = runs?.filter((r) => r.status === "completed").slice(0, 5) || [];
  
  // Calculate stats
  const totalRuns = runs?.filter((r) => r.status === "completed").length || 0;
  const totalCells = runs
    ?.filter((r) => r.status === "completed")
    .reduce((sum, r) => sum + (r.successful_cells || 0), 0) || 0;

  return (
    <>
      <Header
        title="Dashboard"
        description="Overview of your competitive analysis"
        actions={
          <Link href="/runs/new">
            <Button>
              <PlusCircle className="h-4 w-4 mr-2" />
              New Analysis
            </Button>
          </Link>
        }
      />

      <div className="p-6 space-y-6">
        {/* Active Run Section */}
        {runningRun && (
          <div className="space-y-2">
            <h2 className="text-lg font-semibold flex items-center gap-2">
              <TrendingUp className="h-5 w-5 text-primary" />
              Active Run
            </h2>
            <RunProgress runId={runningRun.id} />
          </div>
        )}

        {/* Stats Cards */}
        <div className="grid gap-4 md:grid-cols-3">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Analyses</CardTitle>
              <History className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <Skeleton className="h-8 w-16" />
              ) : (
                <div className="text-2xl font-bold">{totalRuns}</div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Research Cells</CardTitle>
              <BarChart3 className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <Skeleton className="h-8 w-20" />
              ) : (
                <div className="text-2xl font-bold">{totalCells.toLocaleString()}</div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Latest Analysis</CardTitle>
              <Clock className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <Skeleton className="h-8 w-32" />
              ) : recentRuns.length > 0 ? (
                <div className="text-sm text-muted-foreground">
                  {formatTimestamp(recentRuns[0].created_at)}
                </div>
              ) : (
                <div className="text-sm text-muted-foreground">No runs yet</div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Recent Runs */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Recent Analyses</CardTitle>
                <CardDescription>
                  Your latest competitive analysis runs
                </CardDescription>
              </div>
              <Link href="/runs">
                <Button variant="ghost" size="sm">
                  View all
                  <ArrowRight className="h-4 w-4 ml-1" />
                </Button>
              </Link>
            </div>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="space-y-4">
                {Array.from({ length: 3 }).map((_, i) => (
                  <div key={i} className="flex items-center justify-between">
                    <Skeleton className="h-5 w-48" />
                    <Skeleton className="h-5 w-24" />
                  </div>
                ))}
              </div>
            ) : recentRuns.length > 0 ? (
              <div className="space-y-4">
                {recentRuns.map((run) => (
                  <Link
                    key={run.id}
                    href={`/runs/${run.id}`}
                    className="flex items-center justify-between py-2 hover:bg-muted/50 -mx-2 px-2 rounded-lg transition-colors"
                  >
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <CheckCircle className="h-4 w-4 text-green-500" />
                        <span className="font-medium text-sm">{run.id}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        {run.companies.slice(0, 3).map((company) => (
                          <Badge key={company} variant="outline" className="text-xs">
                            {company}
                          </Badge>
                        ))}
                        {run.companies.length > 3 && (
                          <span className="text-xs text-muted-foreground">
                            +{run.companies.length - 3} more
                          </span>
                        )}
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-sm text-muted-foreground">
                        {run.successful_cells}/{run.total_cells} cells
                      </div>
                      <div className="text-xs text-muted-foreground">
                        {formatTimestamp(run.created_at)}
                      </div>
                    </div>
                  </Link>
                ))}
              </div>
            ) : (
              <div className="text-center py-8">
                <div className="rounded-full bg-muted p-3 w-fit mx-auto mb-3">
                  <BarChart3 className="h-6 w-6 text-muted-foreground" />
                </div>
                <p className="text-muted-foreground mb-4">
                  No analyses yet. Start your first one!
                </p>
                <Link href="/runs/new">
                  <Button>
                    <PlusCircle className="h-4 w-4 mr-2" />
                    New Analysis
                  </Button>
                </Link>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Quick Start Guide (shown only when no runs) */}
        {!isLoading && totalRuns === 0 && (
          <Card>
            <CardHeader>
              <CardTitle>Getting Started</CardTitle>
              <CardDescription>
                Learn how to run competitive analyses
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ol className="space-y-4 list-decimal list-inside text-sm">
                <li className="flex items-start gap-2">
                  <span className="font-medium min-w-[24px]">1.</span>
                  <div>
                    <span className="font-medium">Add companies</span>
                    <p className="text-muted-foreground mt-1">
                      Enter the companies you want to analyze (e.g., Stripe, PayPal, Square)
                    </p>
                  </div>
                </li>
                <li className="flex items-start gap-2">
                  <span className="font-medium min-w-[24px]">2.</span>
                  <div>
                    <span className="font-medium">Select variables</span>
                    <p className="text-muted-foreground mt-1">
                      Choose what aspects to research (pricing, features, market share, etc.)
                    </p>
                  </div>
                </li>
                <li className="flex items-start gap-2">
                  <span className="font-medium min-w-[24px]">3.</span>
                  <div>
                    <span className="font-medium">Start research</span>
                    <p className="text-muted-foreground mt-1">
                      Our AI will search the web and compile detailed analysis for each cell
                    </p>
                  </div>
                </li>
                <li className="flex items-start gap-2">
                  <span className="font-medium min-w-[24px]">4.</span>
                  <div>
                    <span className="font-medium">View results</span>
                    <p className="text-muted-foreground mt-1">
                      Explore the interactive table and export to HTML, CSV, or JSON
                    </p>
                  </div>
                </li>
              </ol>
            </CardContent>
          </Card>
        )}
      </div>
    </>
  );
}
