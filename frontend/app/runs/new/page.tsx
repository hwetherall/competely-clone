"use client";

import { Suspense, useState, useCallback, useMemo } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Header } from "@/components/layout/Header";
import { CompanyInput } from "@/components/runs/CompanyInput";
import { SmartVariableSelector } from "@/components/runs/VariableSelector";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { Switch } from "@/components/ui/switch";
import { useCreateRun, useGenerateVariables } from "@/lib/api";
import type { VariableGenerationResponse, DynamicVariableDefinition, ParameterPath } from "@/lib/types";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import {
  Play,
  Clock,
  Zap,
  AlertCircle,
  Loader2,
  Sparkles,
  Lightbulb,
  Building2,
  Rocket,
  Factory,
  TrendingUp,
  BarChart3,
  Landmark,
  Workflow,
} from "lucide-react";
import { Checkbox } from "@/components/ui/checkbox";

function getDefaultSelection(data: VariableGenerationResponse): string[] {
  const alwaysIds = data.always_variables.map((v) => v.id);
  const tier2Included = data.tier2_recommendations
    .filter((r) => r.include)
    .map((r) => r.variable_id);
  const generatedIds = data.generated_variables.map((v) => v.id);
  return [...alwaysIds, ...tier2Included, ...generatedIds];
}

type QueryParams = {
  get: (name: string) => string | null;
  getAll: (name: string) => string[];
};

function getInitialCompanies(params: QueryParams): string[] {
  const queryCompanies = [
    ...params.getAll("company"),
    ...(params.get("companies") ?? "")
      .split(/\n|,/)
      .map((company) => company.trim())
      .filter(Boolean),
  ];
  return [...new Set(queryCompanies)];
}

function getInitialParameterPath(params: QueryParams): ParameterPath {
  const queryPath = params.get("parameter_path");
  if (queryPath === "competely" || queryPath === "avis" || queryPath === "innovera") {
    return queryPath;
  }
  return "competely";
}

export default function NewRunPage() {
  return (
    <Suspense fallback={null}>
      <NewRunPageContent />
    </Suspense>
  );
}

function NewRunPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const createRun = useCreateRun();
  const generateVariables = useGenerateVariables();

  const initialCompanies = useMemo(() => getInitialCompanies(searchParams), [searchParams]);
  const initialParameterPath = useMemo(() => getInitialParameterPath(searchParams), [searchParams]);

  const [companies, setCompanies] = useState<string[]>(initialCompanies);
  const [generatedData, setGeneratedData] = useState<VariableGenerationResponse | null>(null);
  const [selectedVariableIds, setSelectedVariableIds] = useState<string[]>([]);
  const [dynamicVariableDefs, setDynamicVariableDefs] = useState<DynamicVariableDefinition[]>([]);
  const [fastMode, setFastMode] = useState(false);
  const [useV2, setUseV2] = useState(false);
  const [ventureContext, setVentureContext] = useState("");
  const [companyProfiles, setCompanyProfiles] = useState<string[]>(["public_mature"]);
  const [parameterPath, setParameterPath] = useState<ParameterPath>(initialParameterPath);

  const totalCells = companies.length * selectedVariableIds.length;
  const estimatedMinutes = Math.ceil(totalCells * (fastMode ? 0.3 : 0.5));
  const estimatedMaxMinutes = Math.ceil(totalCells * (fastMode ? 0.5 : 0.75));

  const canGenerate = companies.length >= 2;
  const canSubmit = companies.length > 0 && selectedVariableIds.length > 0 && generatedData !== null;

  const handleGenerate = async () => {
    if (!canGenerate) return;
    try {
      const result = await generateVariables.mutateAsync({
        companies,
        company_profiles: companyProfiles,
        parameter_path: parameterPath,
      });
      setGeneratedData(result);
      setSelectedVariableIds(getDefaultSelection(result));
      setDynamicVariableDefs(result.generated_variables);
    } catch (error) {
      console.error("Failed to generate parameters:", error);
    }
  };

  const toggleProfile = (profile: string) => {
    setCompanyProfiles((prev) =>
      prev.includes(profile)
        ? prev.filter((p) => p !== profile)
        : [...prev, profile]
    );
  };

  const handleSelectionChange = useCallback(
    (variableIds: string[], dynamicDefs: DynamicVariableDefinition[]) => {
      setSelectedVariableIds(variableIds);
      setDynamicVariableDefs(dynamicDefs);
    },
    []
  );

  const handleSubmit = async () => {
    if (!canSubmit) return;
    let parameter_contexts: Record<string, string> | undefined;
    if (useV2 && generatedData) {
      parameter_contexts = {};
      const alwaysIds = new Set(generatedData.always_variables.map((v) => v.id));
      const tier2ById = new Map(
        generatedData.tier2_recommendations.map((r) => [r.variable_id, r.reason])
      );
      const generatedById = new Map(
        generatedData.generated_variables.map((v) => [v.id, v.rationale ?? ""])
      );
      for (const id of selectedVariableIds) {
        if (alwaysIds.has(id)) {
          parameter_contexts[id] = generatedData.always_parameter_contexts?.[id] ?? "";
        } else if (tier2ById.has(id)) {
          parameter_contexts[id] = tier2ById.get(id) ?? "";
        } else if (generatedById.has(id)) {
          parameter_contexts[id] = generatedById.get(id) ?? "";
        }
      }
    }
    try {
      const result = await createRun.mutateAsync({
        companies,
        variables: selectedVariableIds,
        dynamic_variables: dynamicVariableDefs.length > 0 ? dynamicVariableDefs : undefined,
        parameter_contexts: parameter_contexts,
        fast_mode: fastMode,
        concurrency: 3,
        version: useV2 ? "v2" : "v1",
        venture_context: ventureContext.trim() || undefined,
        parameter_path: parameterPath,
      });
      router.push(`/runs/${result.run_id}`);
    } catch (error) {
      console.error("Failed to start research:", error);
    }
  };

  return (
    <>
      <Header
        title="New Competitive Analysis"
        description="Add competitors, generate smart parameters, then run research"
      />

      <div className="p-6 max-w-4xl mx-auto space-y-6">
        {/* Step 1: Companies */}
        <Card>
          <CardHeader>
            <CardTitle>Companies</CardTitle>
            <CardDescription>
              Add at least 2 companies to analyze. Press Enter or click to add.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <CompanyInput
              companies={companies}
              onChange={setCompanies}
              placeholder="Enter company name..."
            />

            <div className="space-y-3">
              <Label>Company Profile (Select all that apply)</Label>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Public / Mature */}
                <div
                  className={cn(
                    "flex flex-col items-center justify-between rounded-md border-2 bg-popover p-4 hover:bg-accent hover:text-accent-foreground cursor-pointer transition-all",
                    companyProfiles.includes("public_mature")
                      ? "border-primary bg-primary/5"
                      : "border-muted"
                  )}
                  onClick={() => toggleProfile("public_mature")}
                >
                  <div className="flex items-center justify-between w-full mb-2">
                    <Building2 className="h-6 w-6 text-muted-foreground" />
                    <Checkbox
                      checked={companyProfiles.includes("public_mature")}
                      onCheckedChange={() => toggleProfile("public_mature")}
                    />
                  </div>
                  <div className="text-center w-full">
                    <div className="font-semibold">Public / Mature</div>
                    <div className="text-xs text-muted-foreground mt-1">
                      Established enterprises (e.g. IBM, Toyota)
                    </div>
                  </div>
                </div>

                {/* Public / Emerging */}
                <div
                  className={cn(
                    "flex flex-col items-center justify-between rounded-md border-2 bg-popover p-4 hover:bg-accent hover:text-accent-foreground cursor-pointer transition-all",
                    companyProfiles.includes("public_emerging")
                      ? "border-primary bg-primary/5"
                      : "border-muted"
                  )}
                  onClick={() => toggleProfile("public_emerging")}
                >
                  <div className="flex items-center justify-between w-full mb-2">
                    <TrendingUp className="h-6 w-6 text-blue-500" />
                    <Checkbox
                      checked={companyProfiles.includes("public_emerging")}
                      onCheckedChange={() => toggleProfile("public_emerging")}
                    />
                  </div>
                  <div className="text-center w-full">
                    <div className="font-semibold">Public / Emerging</div>
                    <div className="text-xs text-muted-foreground mt-1">
                      Recent IPOs, high-growth tech (e.g. Figma, Klarna)
                    </div>
                  </div>
                </div>

                {/* Private / Venture */}
                <div
                  className={cn(
                    "flex flex-col items-center justify-between rounded-md border-2 bg-popover p-4 hover:bg-accent hover:text-accent-foreground cursor-pointer transition-all",
                    companyProfiles.includes("private_venture")
                      ? "border-primary bg-primary/5"
                      : "border-muted"
                  )}
                  onClick={() => toggleProfile("private_venture")}
                >
                  <div className="flex items-center justify-between w-full mb-2">
                    <Rocket className="h-6 w-6 text-amber-500" />
                    <Checkbox
                      checked={companyProfiles.includes("private_venture")}
                      onCheckedChange={() => toggleProfile("private_venture")}
                    />
                  </div>
                  <div className="text-center w-full">
                    <div className="font-semibold">Private / Venture</div>
                    <div className="text-xs text-muted-foreground mt-1">
                      Early-stage, pre-revenue to Series C (e.g Burnbot, Innovera)
                    </div>
                  </div>
                </div>

                {/* Private / Established */}
                <div
                  className={cn(
                    "flex flex-col items-center justify-between rounded-md border-2 bg-popover p-4 hover:bg-accent hover:text-accent-foreground cursor-pointer transition-all",
                    companyProfiles.includes("private_established")
                      ? "border-primary bg-primary/5"
                      : "border-muted"
                  )}
                  onClick={() => toggleProfile("private_established")}
                >
                  <div className="flex items-center justify-between w-full mb-2">
                    <Factory className="h-6 w-6 text-slate-600" />
                    <Checkbox
                      checked={companyProfiles.includes("private_established")}
                      onCheckedChange={() => toggleProfile("private_established")}
                    />
                  </div>
                  <div className="text-center w-full">
                    <div className="font-semibold">Private / Established</div>
                    <div className="text-xs text-muted-foreground mt-1">
                      SMEs, industrial, family-owned (e.g. Bosch, The Economist)
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Step 2: Generate parameters (or show review if already generated) */}
        {!generatedData ? (
          <Card>
            <CardHeader>
              <CardTitle>Research Parameters</CardTitle>
              <CardDescription>
                Generate parameters tailored to your competitor set. The AI will suggest
                contextual and industry-specific parameters (e.g. for airlines: fleet size,
                routes; for fintech: API coverage, settlement speed).
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="mb-6 grid gap-3 md:grid-cols-3">
                <button
                  type="button"
                  onClick={() => setParameterPath("competely")}
                  className={cn(
                    "rounded-md border-2 p-4 text-left transition-colors hover:bg-accent",
                    parameterPath === "competely"
                      ? "border-primary bg-primary/5"
                      : "border-muted"
                  )}
                >
                  <div className="mb-2 flex items-center gap-2">
                    <BarChart3 className="h-5 w-5 text-primary" />
                    <span className="text-sm font-semibold">Competely</span>
                  </div>
                  <p className="text-xs leading-relaxed text-muted-foreground">
                    Product-comparison lens for features, pricing, customers, and market position.
                  </p>
                </button>
                <button
                  type="button"
                  onClick={() => setParameterPath("avis")}
                  className={cn(
                    "rounded-md border-2 p-4 text-left transition-colors hover:bg-accent",
                    parameterPath === "avis"
                      ? "border-primary bg-primary/5"
                      : "border-muted"
                  )}
                >
                  <div className="mb-2 flex items-center gap-2">
                    <Landmark className="h-5 w-5 text-primary" />
                    <span className="text-sm font-semibold">AVIS</span>
                  </div>
                  <p className="text-xs leading-relaxed text-muted-foreground">
                    Investment-thesis lens for moats, funding, GTM, team, IP, and exit readiness.
                  </p>
                </button>
                <button
                  type="button"
                  onClick={() => setParameterPath("innovera")}
                  className={cn(
                    "rounded-md border-2 p-4 text-left transition-colors hover:bg-accent",
                    parameterPath === "innovera"
                      ? "border-primary bg-primary/5"
                      : "border-muted"
                  )}
                >
                  <div className="mb-2 flex items-center gap-2">
                    <Workflow className="h-5 w-5 text-primary" />
                    <span className="text-sm font-semibold">Innovera lens</span>
                  </div>
                  <p className="text-xs leading-relaxed text-muted-foreground">
                    Business-model deep dive for AI-native and blended AI plus human competitors.
                  </p>
                </button>
              </div>
              <Button
                size="lg"
                disabled={!canGenerate || generateVariables.isPending}
                onClick={handleGenerate}
                className="w-full sm:w-auto"
              >
                {generateVariables.isPending ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Analyzing your competitor set...
                  </>
                ) : (
                  <>
                    <Sparkles className="h-4 w-4 mr-2" />
                    Generate Smart Parameters
                  </>
                )}
              </Button>
              {!canGenerate && companies.length > 0 && (
                <p className="mt-3 text-sm text-muted-foreground">
                  Add at least one more company to enable parameter generation.
                </p>
              )}
              {generateVariables.isError && (
                <div className="mt-4 p-4 rounded-lg bg-destructive/10 text-destructive">
                  <p className="flex items-center gap-2">
                    <AlertCircle className="h-4 w-4" />
                    Failed to generate parameters. Check that the API is running and
                    OPENROUTER_API_KEY is set.
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        ) : (
          <>
            {/* Step 3: Review parameters */}
            <Card>
              <CardHeader>
                <CardTitle>Review Parameters</CardTitle>
                <CardDescription>
                  Adjust which parameters to include. Then click Start Research below.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <SmartVariableSelector
                  data={generatedData}
                  selectedVariableIds={selectedVariableIds}
                  onSelectionChange={handleSelectionChange}
                />
              </CardContent>
            </Card>

            {/* Options */}
            <Card>
              <CardHeader>
                <CardTitle>Options</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label htmlFor="v2-mode">Relational (V2)</Label>
                    <p className="text-sm text-muted-foreground">
                      Compare all companies per parameter; executive brief and deep-dive reports
                    </p>
                  </div>
                  <Switch
                    id="v2-mode"
                    checked={useV2}
                    onCheckedChange={setUseV2}
                  />
                </div>
                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label htmlFor="fast-mode" className="flex items-center gap-2">
                      <Zap className="h-4 w-4 text-yellow-500" />
                      Fast Mode
                    </Label>
                    <p className="text-sm text-muted-foreground">
                      Single iteration per cell, faster but less comprehensive
                    </p>
                  </div>
                  <Switch
                    id="fast-mode"
                    checked={fastMode}
                    onCheckedChange={setFastMode}
                  />
                </div>
              </CardContent>
            </Card>

            {/* Venture Context (V2 only) */}
            {useV2 && (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Lightbulb className="h-5 w-5 text-amber-500" />
                    Venture Context
                    <span className="text-xs font-normal text-muted-foreground ml-1">(optional)</span>
                  </CardTitle>
                  <CardDescription>
                    Describe your proposed venture or strategic position. The executive brief will
                    personalize white-space analysis and next steps to your specific situation.
                    Leave blank for a neutral landscape analysis.
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <Textarea
                    placeholder='e.g. "Low-cost airline focused on connecting the Caribbean with Europe. Spin-off of LATAM airlines with a budget of $200M. Targeting underserved leisure and diaspora routes."'
                    value={ventureContext}
                    onChange={(e) => setVentureContext(e.target.value)}
                    rows={4}
                    className="resize-y"
                  />
                  {ventureContext.trim() && (
                    <p className="mt-2 text-xs text-muted-foreground">
                      White space and next steps will be tailored to this venture.
                    </p>
                  )}
                </CardContent>
              </Card>
            )}

            <Separator />

            {/* Summary & Submit */}
            <Card>
              <CardContent className="py-6">
                <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
                  <div className="space-y-2">
                    <p className="text-lg font-medium">
                      {companies.length} companies × {selectedVariableIds.length} parameters ={" "}
                      <span className="text-primary">{totalCells} cells</span>
                    </p>
                    <p className="text-sm text-muted-foreground flex items-center gap-2">
                      <Clock className="h-4 w-4" />
                      Estimated time: ~{estimatedMinutes}-{estimatedMaxMinutes} minutes
                      {fastMode && " (fast mode)"}
                    </p>
                  </div>
                  <Button
                    size="lg"
                    disabled={!canSubmit || createRun.isPending}
                    onClick={handleSubmit}
                    className="min-w-[200px]"
                  >
                    {createRun.isPending ? (
                      <>
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        Starting...
                      </>
                    ) : (
                      <>
                        <Play className="h-4 w-4 mr-2" />
                        Start Research
                      </>
                    )}
                  </Button>
                </div>
                {createRun.isError && (
                  <div className="mt-4 p-4 rounded-lg bg-destructive/10 text-destructive">
                    <p className="flex items-center gap-2">
                      <AlertCircle className="h-4 w-4" />
                      Failed to start research. Make sure the API server is running.
                    </p>
                  </div>
                )}
              </CardContent>
            </Card>
          </>
        )}
      </div>
    </>
  );
}
