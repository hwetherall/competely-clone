"use client";

import { useState } from "react";
import type { ResearchPlan, ConfidencePreview } from "@/lib/types";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { AlertTriangle, Download, Save, Play, CheckCircle2, FileText, Target, Users, Zap, Edit2, ChevronDown, ChevronUp, ListFilter, Skull } from "lucide-react";
import { cn } from "@/lib/utils";

interface PlanReviewProps {
  plan: Partial<ResearchPlan>;
  confidencePreview: ConfidencePreview | null;
  onEditStep: (step: number) => void;
  onSaveDraft: () => void;
  onLaunch: () => void;
  onExport: () => void;
  isSaving?: boolean;
  isLaunching?: boolean;
}

export function PlanReview({
  plan,
  confidencePreview,
  onEditStep,
  onSaveDraft,
  onLaunch,
  onExport,
  isSaving,
  isLaunching,
}: PlanReviewProps) {
  const [showParams, setShowParams] = useState(false);

  // Merge initial companies with accepted suggestions
  const companies = plan.companies ?? [];
  const suggested = plan.suggested_companies ?? [];
  const acceptedIds = plan.accepted_suggestions ?? [];
  
  const allCompanyNames = [
    ...companies.map((c) => (typeof c === "string" ? c : c.official_name ?? c.input_name)),
    ...suggested.filter(s => acceptedIds.includes(s.id)).map(s => s.name)
  ];

  // Prepare parameters list
  const selectedIds = plan.selected_variable_ids ?? [];
  const dynamicVars = plan.dynamic_variables ?? [];
  
  const parameters = selectedIds.map(id => {
    const dynamic = dynamicVars.find(d => d.id === id);
    if (dynamic) {
      return {
        id,
        name: dynamic.name,
        description: dynamic.rationale || dynamic.research_prompt,
        isDynamic: true
      };
    }
    // Fallback for static variables: format ID to Title Case
    const name = id.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
    return {
      id,
      name,
      description: plan.parameter_contexts?.[id] || "Standard competitive parameter.",
      isDynamic: false
    };
  });

  return (
    <div className="space-y-8 max-w-4xl mx-auto">
      {/* Feasibility / Pre-flight Check */}
      {confidencePreview && (
        <Card className="border-l-4 border-l-amber-500 shadow-sm bg-amber-50/30 dark:bg-amber-950/10">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <AlertTriangle className="h-5 w-5 text-amber-600 dark:text-amber-500" />
                <CardTitle className="text-lg text-amber-900 dark:text-amber-100">
                  Feasibility Check
                </CardTitle>
              </div>
              <Badge 
                variant="outline" 
                className={cn(
                  "capitalize font-medium",
                  confidencePreview.overall_level === "high" && "border-green-500 text-green-700 bg-green-50",
                  confidencePreview.overall_level === "medium" && "border-amber-500 text-amber-700 bg-amber-50",
                  confidencePreview.overall_level === "low" && "border-red-500 text-red-700 bg-red-50"
                )}
              >
                {confidencePreview.overall_level} Confidence
              </Badge>
            </div>
            <CardDescription className="text-amber-800/80 dark:text-amber-200/70">
              AI assessment of data availability and research complexity.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {confidencePreview.company_confidences.map((c) => (
                <div
                  key={c.company_id}
                  className={cn(
                    "flex flex-col gap-1 rounded-lg border p-3 text-sm bg-background/80 backdrop-blur-sm",
                    c.level === "high" && "border-green-200/60 dark:border-green-900/30",
                    c.level === "medium" && "border-amber-200/60 dark:border-amber-900/30",
                    c.level === "low" && "border-red-200/60 dark:border-red-900/30"
                  )}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-semibold truncate pr-2">{c.company_name}</span>
                    <div className={cn(
                      "h-2 w-2 rounded-full",
                      c.level === "high" ? "bg-green-500" : c.level === "medium" ? "bg-amber-500" : "bg-red-500"
                    )} />
                  </div>
                  <p className="text-xs text-muted-foreground line-clamp-2" title={c.reason}>
                    {c.reason}
                  </p>
                </div>
              ))}
            </div>
            
            {(confidencePreview.warnings.length > 0 || confidencePreview.suggestions.length > 0) && (
              <div className="rounded-md bg-background/50 border p-3 text-sm space-y-2">
                {confidencePreview.warnings.map((w, i) => (
                  <div key={i} className="flex gap-2 text-amber-700 dark:text-amber-400">
                    <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
                    <span>{w}</span>
                  </div>
                ))}
                {confidencePreview.suggestions.map((s, i) => (
                  <div key={i} className="flex gap-2 text-blue-700 dark:text-blue-400">
                    <CheckCircle2 className="h-4 w-4 shrink-0 mt-0.5" />
                    <span>{s}</span>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Main Plan Document */}
      <div className="relative rounded-xl border bg-card text-card-foreground shadow-sm overflow-hidden">
        {/* Document Header */}
        <div className="bg-muted/30 border-b p-6 md:p-8">
          <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-4">
            <div className="space-y-1.5">
              <div className="flex items-center gap-2 text-sm text-muted-foreground uppercase tracking-wider font-semibold">
                <FileText className="h-4 w-4" />
                Research Plan
              </div>
              <h1 className="text-2xl md:text-3xl font-bold tracking-tight">
                {plan.industry_context ? `Competitive Analysis: ${plan.industry_context}` : "Competitive Analysis Plan"}
              </h1>
              <div className="flex flex-wrap gap-3 pt-2">
                <Badge variant="secondary" className="px-2 py-0.5">
                  {allCompanyNames.length} Companies
                </Badge>
                <Badge variant="secondary" className="px-2 py-0.5">
                  {parameters.length} Parameters
                </Badge>
                <Badge variant={plan.parameter_path !== "competely" ? "default" : "secondary"} className="px-2 py-0.5">
                  {plan.parameter_path === "avis"
                    ? "AVIS"
                    : plan.parameter_path === "innovera"
                      ? "Innovera Lens"
                      : "Competely"} Framework
                </Badge>
                <Badge variant="secondary" className="px-2 py-0.5 capitalize">
                  {plan.depth ?? "Standard"} Depth
                </Badge>
              </div>
            </div>
            <Button variant="ghost" size="sm" onClick={() => onEditStep(1)} className="shrink-0">
              <Edit2 className="h-4 w-4 mr-2" />
              Edit Plan
            </Button>
          </div>
        </div>

        <div className="p-6 md:p-8 space-y-8">
          {/* Mission Section */}
          <section className="space-y-3">
            <h3 className="text-lg font-semibold flex items-center gap-2">
              <Target className="h-5 w-5 text-primary" />
              Research Mission
            </h3>
            <div className="rounded-lg bg-muted/30 p-4 text-sm md:text-base leading-relaxed border border-muted/50">
              {plan.mission_statement || "No mission statement defined."}
            </div>
          </section>

          <div className="grid md:grid-cols-2 gap-8">
            {/* Key Questions */}
            <section className="space-y-3">
              <h3 className="text-lg font-semibold flex items-center gap-2">
                <Zap className="h-5 w-5 text-amber-500" />
                Key Questions
              </h3>
              <ul className="space-y-2">
                {(plan.key_questions ?? []).map((q, i) => (
                  <li key={i} className="flex gap-3 text-sm">
                    <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-primary/10 text-[10px] font-bold text-primary mt-0.5">
                      {i + 1}
                    </span>
                    <span className="text-muted-foreground">{q}</span>
                  </li>
                ))}
                {(plan.key_questions?.length ?? 0) === 0 && (
                  <li className="text-sm text-muted-foreground italic">No key questions defined.</li>
                )}
              </ul>
            </section>

            {/* Scope & Config */}
            <section className="space-y-6">
              <div className="space-y-3">
                <h3 className="text-lg font-semibold flex items-center gap-2">
                  <Users className="h-5 w-5 text-blue-500" />
                  Target Audience
                </h3>
                <div className="rounded-md border p-3 text-sm">
                  <div className="font-medium capitalize">{plan.audience?.replace("_", " ") || "General"}</div>
                  <p className="text-xs text-muted-foreground mt-1">
                    Tailored for {plan.audience === "vc" ? "investors and financial analysis" : 
                                  plan.audience === "product" ? "product strategy and feature comparison" : 
                                  plan.audience === "board" ? "executive decision making" : "general competitive overview"}.
                  </p>
                </div>
              </div>

              <div className="space-y-3">
                <h3 className="text-lg font-semibold">Companies in Scope</h3>
                <div className="flex flex-wrap gap-2">
                  {allCompanyNames.map((name, i) => (
                    <Badge key={i} variant="outline" className="text-sm py-1 px-2.5">
                      {name}
                    </Badge>
                  ))}
                </div>
              </div>
            </section>
          </div>

          <Separator />

          {/* Parameters Deep Dive */}
          <section className="space-y-3">
            <button 
              onClick={() => setShowParams(!showParams)}
              className="flex items-center gap-2 text-lg font-semibold w-full text-left hover:text-primary transition-colors"
            >
              <ListFilter className="h-5 w-5 text-purple-500" />
              Selected Parameters
              {showParams ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
            </button>
            
            {showParams && (
              <div className="grid gap-3 sm:grid-cols-2 animate-in fade-in slide-in-from-top-2 duration-200">
                {parameters.map((p) => (
                  <div key={p.id} className="rounded-lg border p-3 text-sm hover:bg-muted/30 transition-colors">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-medium">{p.name}</span>
                      {p.isDynamic && (
                        <Badge variant="secondary" className="text-[10px] px-1.5 h-4">
                          Custom
                        </Badge>
                      )}
                    </div>
                    <p className="text-xs text-muted-foreground line-clamp-2">
                      {p.description}
                    </p>
                  </div>
                ))}
              </div>
            )}
            {!showParams && (
              <p className="text-sm text-muted-foreground">
                {parameters.length} parameters selected. Click to expand details.
              </p>
            )}
          </section>

          <Separator />

          {/* Graveyard / Post-Mortem Intelligence */}
          {plan.graveyard_enabled && plan.graveyard_companies && plan.graveyard_companies.length > 0 && (
            <>
              <Separator />
              <section className="space-y-3">
                <h3 className="text-lg font-semibold flex items-center gap-2">
                  <Skull className="h-5 w-5 text-slate-500" />
                  Post-Mortem Intelligence
                </h3>
                <p className="text-sm text-muted-foreground">
                  {plan.graveyard_companies.length} defunct companies will be analyzed for failure patterns and risk overlays.
                </p>
                <div className="grid gap-2">
                  {plan.graveyard_companies.map((c) => (
                    <div key={c.name} className="rounded-lg border p-3 text-sm bg-muted/20">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="font-medium">{c.name}</span>
                        {c.years_active && (
                          <span className="text-xs text-muted-foreground">({c.years_active})</span>
                        )}
                      </div>
                      {c.reason_summary && (
                        <p className="text-xs text-muted-foreground">{c.reason_summary}</p>
                      )}
                    </div>
                  ))}
                </div>
              </section>
            </>
          )}

          {/* Hypothesis (if present) */}
          {plan.hypothesis && (
            <section className="space-y-3">
              <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">Initial Hypothesis</h3>
              <p className="text-sm text-muted-foreground italic pl-4 border-l-2 border-primary/30">
                &quot;{plan.hypothesis}&quot;
              </p>
            </section>
          )}
        </div>
      </div>

      {/* Action Bar */}
      <div className="sticky bottom-6 z-10 mx-auto max-w-2xl">
        <div className="rounded-full border bg-background/95 backdrop-blur shadow-lg p-2 px-4 flex items-center justify-between gap-4">
          <div className="flex gap-2">
            <Button onClick={onSaveDraft} disabled={isSaving} variant="ghost" size="sm" className="rounded-full">
              <Save className="h-4 w-4 mr-2" />
              Save Draft
            </Button>
            <Button onClick={onExport} variant="ghost" size="sm" className="rounded-full">
              <Download className="h-4 w-4 mr-2" />
              Export
            </Button>
          </div>
          <Button onClick={onLaunch} disabled={isLaunching} size="sm" className="rounded-full px-6 shadow-md">
            <Play className="h-4 w-4 mr-2 fill-current" />
            {isLaunching ? "Launching..." : "Approve & Launch"}
          </Button>
        </div>
      </div>
    </div>
  );
}
