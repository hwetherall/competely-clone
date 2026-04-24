"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  AlertCircle,
  CheckCircle2,
  ExternalLink,
  Loader2,
  Play,
  RefreshCw,
  Search,
} from "lucide-react";
import { Header } from "@/components/layout/Header";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useDiscovery } from "@/lib/api";
import type { CompetitorCandidate, DiscoveryFraming } from "@/lib/types";
import { cn } from "@/lib/utils";

const FRAMING_LABELS: Record<DiscoveryFraming, string> = {
  direct: "Direct",
  problem_sharer: "Problem-Sharer",
  category_sharer: "Category-Sharer",
  adjacency: "Adjacency",
};

function domainFromUrl(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}

function confidenceLabel(confidence: number): string {
  if (confidence >= 0.75) return "High";
  if (confidence >= 0.45) return "Medium";
  return "Low";
}

function confidenceClass(confidence: number): string {
  if (confidence >= 0.75) return "bg-green-100 text-green-800 hover:bg-green-100";
  if (confidence >= 0.45) return "bg-yellow-100 text-yellow-800 hover:bg-yellow-100";
  return "bg-slate-100 text-slate-800 hover:bg-slate-100";
}

function candidateRationale(candidate: CompetitorCandidate): string {
  const rationale = candidate.framings
    .map((framing) => candidate.rationales[framing])
    .find((value) => value && value.trim());
  return rationale?.trim() ?? "";
}

export default function DiscoveryDetailPage() {
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const discoveryId = params.id;
  const { data: discovery, isLoading, error, refetch, isFetching } = useDiscovery(discoveryId);
  const [manualSelectedNames, setManualSelectedNames] = useState<string[] | null>(null);

  const candidates = useMemo(
    () => [...(discovery?.candidates ?? [])].sort((a, b) => b.confidence - a.confidence),
    [discovery?.candidates],
  );

  const defaultSelectedNames = useMemo(() => {
    if (!discovery || discovery.status !== "complete") return [];
    const defaults = candidates.filter((candidate) => candidate.confidence >= 0.45).map((candidate) => candidate.name);
    const fallback = candidates.slice(0, 10).map((candidate) => candidate.name);
    return defaults.length > 0 ? defaults : fallback;
  }, [candidates, discovery]);

  const selectedNames = manualSelectedNames ?? defaultSelectedNames;

  const toggleCandidate = (name: string, checked: boolean) => {
    setManualSelectedNames((prev) => {
      const current = prev ?? defaultSelectedNames;
      return checked
        ? [...new Set([...current, name])]
        : current.filter((candidateName) => candidateName !== name);
    });
  };

  const toggleAll = (checked: boolean) => {
    setManualSelectedNames(checked ? candidates.map((candidate) => candidate.name) : []);
  };

  const handleRunAnalysis = () => {
    const params = new URLSearchParams();
    params.set("companies", selectedNames.join("\n"));
    params.set("parameter_path", "innovera");
    router.push(`/runs/new?${params.toString()}`);
  };

  const allSelected = candidates.length > 0 && selectedNames.length === candidates.length;

  return (
    <>
      <Header
        title="Discovery Results"
        description={discovery ? `${discovery.target_profile.company_name} competitor set` : discoveryId}
        actions={
          <div className="flex items-center gap-2">
            <Button variant="outline" onClick={() => refetch()} disabled={isFetching}>
              <RefreshCw className={cn("h-4 w-4", isFetching && "animate-spin")} />
              Refresh
            </Button>
            <Link href="/discovery/new">
              <Button variant="outline">
                <Search className="h-4 w-4" />
                New Discovery
              </Button>
            </Link>
          </div>
        }
      />

      <div className="mx-auto max-w-6xl space-y-6 p-6">
        {isLoading ? (
          <Card>
            <CardContent className="space-y-3 py-6">
              <Skeleton className="h-6 w-56" />
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-2/3" />
            </CardContent>
          </Card>
        ) : error ? (
          <Card>
            <CardContent className="flex flex-col items-center justify-center py-12 text-center">
              <AlertCircle className="mb-4 h-10 w-10 text-destructive" />
              <h2 className="text-lg font-semibold">Discovery unavailable</h2>
              <p className="mt-2 max-w-xl text-sm text-muted-foreground">
                {error instanceof Error ? error.message : "Could not load this discovery run."}
              </p>
            </CardContent>
          </Card>
        ) : discovery ? (
          <>
            <Card>
              <CardContent className="flex flex-col gap-4 py-5 md:flex-row md:items-center md:justify-between">
                <div className="space-y-2">
                  <div className="flex flex-wrap items-center gap-2">
                    <StatusBadge status={discovery.status} />
                    <Badge variant="outline">{candidates.length} candidates</Badge>
                    <Badge variant="outline">{selectedNames.length} selected</Badge>
                  </div>
                  <p className="max-w-3xl text-sm text-muted-foreground">
                    {discovery.target_profile.industry || "Discovery"} for{" "}
                    {discovery.target_profile.audience || discovery.target_profile.company_name}
                  </p>
                </div>
                <Button
                  size="lg"
                  onClick={handleRunAnalysis}
                  disabled={discovery.status !== "complete" || selectedNames.length === 0}
                >
                  <Play className="h-4 w-4" />
                  Run Analysis
                </Button>
              </CardContent>
            </Card>

            {discovery.status === "running" && (
              <Card>
                <CardContent className="flex items-center gap-3 py-5 text-sm text-muted-foreground">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Discovery is still running. Results will refresh automatically.
                </CardContent>
              </Card>
            )}

            {discovery.status === "failed" && (
              <Card>
                <CardContent className="flex items-start gap-3 py-5 text-sm text-destructive">
                  <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                  <span>{discovery.error || "Discovery failed."}</span>
                </CardContent>
              </Card>
            )}

            <Card>
              <CardHeader>
                <CardTitle>Candidate Shortlist</CardTitle>
              </CardHeader>
              <CardContent>
                {candidates.length > 0 ? (
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="w-10">
                          <Checkbox
                            checked={allSelected}
                            onCheckedChange={(checked) => toggleAll(checked === true)}
                            aria-label="Select all candidates"
                          />
                        </TableHead>
                        <TableHead>Company</TableHead>
                        <TableHead>Framing</TableHead>
                        <TableHead>Confidence</TableHead>
                        <TableHead>Rationale</TableHead>
                        <TableHead>Evidence</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {candidates.map((candidate, index) => (
                        <TableRow
                          key={`${candidate.canonical_domain || candidate.name}-${index}`}
                          data-state={selectedNames.includes(candidate.name) ? "selected" : undefined}
                        >
                          <TableCell>
                            <Checkbox
                              checked={selectedNames.includes(candidate.name)}
                              onCheckedChange={(checked) => toggleCandidate(candidate.name, checked === true)}
                              aria-label={`Select ${candidate.name}`}
                            />
                          </TableCell>
                          <TableCell>
                            <div className="font-medium">{candidate.name}</div>
                            {candidate.canonical_domain && (
                              <div className="text-xs text-muted-foreground">{candidate.canonical_domain}</div>
                            )}
                          </TableCell>
                          <TableCell>
                            <div className="flex max-w-52 flex-wrap gap-1">
                              {candidate.framings.map((framing) => (
                                <Badge key={framing} variant="outline" className="text-xs">
                                  {FRAMING_LABELS[framing]}
                                </Badge>
                              ))}
                            </div>
                          </TableCell>
                          <TableCell>
                            <Badge className={confidenceClass(candidate.confidence)}>
                              {confidenceLabel(candidate.confidence)} {Math.round(candidate.confidence * 100)}%
                            </Badge>
                          </TableCell>
                          <TableCell className="max-w-[360px] whitespace-normal text-sm text-muted-foreground">
                            {candidateRationale(candidate) || "No rationale captured."}
                          </TableCell>
                          <TableCell>
                            <div className="flex max-w-64 flex-col gap-1">
                              {candidate.evidence_urls.slice(0, 2).map((url) => (
                                <a
                                  key={url}
                                  href={url}
                                  target="_blank"
                                  rel="noreferrer"
                                  className="inline-flex items-center gap-1 truncate text-xs text-primary hover:underline"
                                >
                                  <ExternalLink className="h-3 w-3 shrink-0" />
                                  {domainFromUrl(url)}
                                </a>
                              ))}
                            </div>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                ) : (
                  <div className="flex flex-col items-center justify-center py-12 text-center">
                    <Search className="mb-4 h-10 w-10 text-muted-foreground" />
                    <h2 className="text-lg font-semibold">No candidates yet</h2>
                    <p className="mt-2 text-sm text-muted-foreground">
                      The discovery agent has not returned shortlist candidates.
                    </p>
                  </div>
                )}
              </CardContent>
            </Card>
          </>
        ) : null}
      </div>
    </>
  );
}

function StatusBadge({ status }: { status: string }) {
  if (status === "complete") {
    return (
      <Badge className="bg-green-100 text-green-800 hover:bg-green-100">
        <CheckCircle2 className="h-3 w-3" />
        Complete
      </Badge>
    );
  }
  if (status === "running") {
    return (
      <Badge className="bg-blue-100 text-blue-800 hover:bg-blue-100">
        <Loader2 className="h-3 w-3 animate-spin" />
        Running
      </Badge>
    );
  }
  return (
    <Badge className="bg-red-100 text-red-800 hover:bg-red-100">
      <AlertCircle className="h-3 w-3" />
      Failed
    </Badge>
  );
}
