"use client";

import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { usePlan, useLaunchPlan } from "@/lib/api";
import { Header } from "@/components/layout/Header";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { AlertCircle, Play, Loader2 } from "lucide-react";

export default function PlanDetailPage() {
  const params = useParams();
  const router = useRouter();
  const planId = params.id as string;
  const { data: plan, isLoading, error } = usePlan(planId);
  const launchPlan = useLaunchPlan();

  const handleLaunch = async () => {
    try {
      const res = await launchPlan.mutateAsync(planId);
      router.push(`/runs/${res.run_id}`);
    } catch (e) {
      console.error(e);
    }
  };

  if (isLoading || !plan) {
    return (
      <>
        <Header title="Research Plan" description="Loading..." />
        <div className="p-6">
          <Skeleton className="h-32 w-full" />
          <Skeleton className="h-48 w-full mt-4" />
        </div>
      </>
    );
  }

  if (error) {
    return (
      <>
        <Header title="Research Plan" description="Error" />
        <div className="p-6">
          <Card>
            <CardContent className="py-12 flex flex-col items-center">
              <AlertCircle className="h-12 w-12 text-destructive mb-4" />
              <p className="text-muted-foreground">Failed to load plan.</p>
            </CardContent>
          </Card>
        </div>
      </>
    );
  }

  const companies = plan.companies ?? [];
  const companyNames = companies.map((c: { official_name?: string; name?: string }) => c.official_name ?? c.name);

  return (
    <>
      <Header
        title={plan.title ?? "Research Plan"}
        description={`Status: ${plan.status}`}
        actions={
          plan.status === "draft" && (
            <div className="flex gap-2">
              <Link href={`/plans/new?edit=${planId}`}>
                <Button variant="outline">Edit</Button>
              </Link>
              <Button onClick={handleLaunch} disabled={launchPlan.isPending}>
                {launchPlan.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin mr-2" />
                ) : (
                  <Play className="h-4 w-4 mr-2" />
                )}
                Launch research
              </Button>
            </div>
          )
        }
      />

      <div className="p-6 max-w-4xl mx-auto space-y-6">
        <Card>
          <CardHeader>
            <CardTitle>Companies</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {companyNames.map((name: string) => (
                <Badge key={name} variant="secondary">
                  {name}
                </Badge>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Mission</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground whitespace-pre-wrap">
              {plan.mission_statement || "—"}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Key questions</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="list-disc list-inside text-sm space-y-1">
              {(plan.key_questions ?? []).map((q: string, i: number) => (
                <li key={i}>{q}</li>
              ))}
            </ul>
          </CardContent>
        </Card>

        {plan.run_id && (
          <Card>
            <CardContent className="py-4">
              <Link href={`/runs/${plan.run_id}`} className="text-primary hover:underline">
                View run: {plan.run_id}
              </Link>
            </CardContent>
          </Card>
        )}
      </div>
    </>
  );
}
