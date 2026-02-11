"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Header } from "@/components/layout/Header";
import { CompanyInput } from "@/components/runs/CompanyInput";
import { SmartVariableSelector } from "@/components/runs/VariableSelector";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { Switch } from "@/components/ui/switch";
import { useCreateRun, useGenerateVariables } from "@/lib/api";
import type { VariableGenerationResponse, DynamicVariableDefinition } from "@/lib/types";
import {
  Play,
  Clock,
  Zap,
  AlertCircle,
  Loader2,
  Sparkles,
} from "lucide-react";

function getDefaultSelection(data: VariableGenerationResponse): string[] {
  const alwaysIds = data.always_variables.map((v) => v.id);
  const tier2Included = data.tier2_recommendations
    .filter((r) => r.include)
    .map((r) => r.variable_id);
  const generatedIds = data.generated_variables.map((v) => v.id);
  return [...alwaysIds, ...tier2Included, ...generatedIds];
}

export default function NewRunPage() {
  const router = useRouter();
  const createRun = useCreateRun();
  const generateVariables = useGenerateVariables();

  const [companies, setCompanies] = useState<string[]>([]);
  const [generatedData, setGeneratedData] = useState<VariableGenerationResponse | null>(null);
  const [selectedVariableIds, setSelectedVariableIds] = useState<string[]>([]);
  const [dynamicVariableDefs, setDynamicVariableDefs] = useState<DynamicVariableDefinition[]>([]);
  const [fastMode, setFastMode] = useState(false);

  const totalCells = companies.length * selectedVariableIds.length;
  const estimatedMinutes = Math.ceil(totalCells * (fastMode ? 0.3 : 0.5));
  const estimatedMaxMinutes = Math.ceil(totalCells * (fastMode ? 0.5 : 0.75));

  const canGenerate = companies.length >= 2;
  const canSubmit = companies.length > 0 && selectedVariableIds.length > 0 && generatedData !== null;

  const handleGenerate = async () => {
    if (!canGenerate) return;
    try {
      const result = await generateVariables.mutateAsync(companies);
      setGeneratedData(result);
      setSelectedVariableIds(getDefaultSelection(result));
      setDynamicVariableDefs(result.generated_variables);
    } catch (error) {
      console.error("Failed to generate parameters:", error);
    }
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
    try {
      const result = await createRun.mutateAsync({
        companies,
        variables: selectedVariableIds,
        dynamic_variables: dynamicVariableDefs.length > 0 ? dynamicVariableDefs : undefined,
        fast_mode: fastMode,
        concurrency: 3,
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
          <CardContent>
            <CompanyInput
              companies={companies}
              onChange={setCompanies}
              placeholder="Enter company name..."
            />
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
