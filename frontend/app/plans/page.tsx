"use client";

import Link from "next/link";
import { usePlans } from "@/lib/api";
import { Header } from "@/components/layout/Header";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { FileText, PlusCircle, ChevronRight, AlertCircle } from "lucide-react";
import { formatTimestamp } from "@/lib/api";

export default function PlansListPage() {
  const { data, isLoading, error } = usePlans();
  const plans = data?.plans ?? [];

  return (
    <>
      <Header
        title="Research Plans"
        description="Create and manage research plans before launching the deep-dive"
        actions={
          <Link href="/plans/new">
            <Button>
              <PlusCircle className="h-4 w-4 mr-2" />
              New Plan
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
              <h2 className="text-lg font-semibold mb-2">Failed to load plans</h2>
              <p className="text-muted-foreground text-center max-w-md">
                Make sure the API server is running (e.g.{" "}
                <code className="text-xs bg-muted px-1.5 py-0.5 rounded">
                  uvicorn api.main:app --reload --port 8000
                </code>{" "}
                from the project root).
              </p>
            </CardContent>
          </Card>
        ) : plans.length > 0 ? (
          <div className="space-y-4">
            {plans.map((plan) => (
              <Link key={plan.id} href={`/plans/${plan.id}`}>
                <Card className="transition-colors hover:bg-muted/50 cursor-pointer">
                  <CardContent className="py-4">
                    <div className="flex items-center justify-between">
                      <div className="space-y-1">
                        <div className="flex items-center gap-3">
                          <h3 className="font-semibold">{plan.title}</h3>
                          <Badge variant={plan.status === "launched" ? "default" : "secondary"}>
                            {plan.status}
                          </Badge>
                          {plan.run_id && (
                            <Badge variant="outline" className="text-xs">
                              Run: {plan.run_id}
                            </Badge>
                          )}
                        </div>
                        <div className="flex items-center gap-4 text-sm text-muted-foreground">
                          <span>{formatTimestamp(plan.updated_at)}</span>
                          <span>{plan.companies?.length ?? 0} companies</span>
                        </div>
                        {Array.isArray(plan.companies) && plan.companies.length > 0 && (
                          <div className="flex gap-2 pt-1 flex-wrap">
                            {plan.companies.slice(0, 5).map((c: string) => (
                              <Badge key={c} variant="outline" className="text-xs">
                                {c}
                              </Badge>
                            ))}
                            {(plan.companies.length ?? 0) > 5 && (
                              <span className="text-xs text-muted-foreground">
                                +{plan.companies.length - 5} more
                              </span>
                            )}
                          </div>
                        )}
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
                <FileText className="h-8 w-8 text-muted-foreground" />
              </div>
              <h2 className="text-lg font-semibold mb-2">No plans yet</h2>
              <p className="text-muted-foreground mb-4">
                Create a research plan in ~5 minutes, then launch the full analysis
              </p>
              <Link href="/plans/new">
                <Button>
                  <PlusCircle className="h-4 w-4 mr-2" />
                  New Plan
                </Button>
              </Link>
            </CardContent>
          </Card>
        )}
      </div>
    </>
  );
}
