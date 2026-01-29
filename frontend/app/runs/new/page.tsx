"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Header } from "@/components/layout/Header";
import { CompanyInput } from "@/components/runs/CompanyInput";
import { VariableSelector } from "@/components/runs/VariableSelector";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { Switch } from "@/components/ui/switch";
import { useCreateRun } from "@/lib/api";
import { 
  Play, 
  Clock, 
  Zap,
  AlertCircle,
  Loader2,
} from "lucide-react";

export default function NewRunPage() {
  const router = useRouter();
  const createRun = useCreateRun();
  
  const [companies, setCompanies] = useState<string[]>([]);
  const [selectedVariables, setSelectedVariables] = useState<string[]>([
    "unique_value_proposition",
    "positioning",
    "differentiation",
    "target_customer_personas",
    "key_features",
    "pricing_strategy",
    "business_models",
    "use_cases",
  ]);
  const [fastMode, setFastMode] = useState(false);

  const totalCells = companies.length * selectedVariables.length;
  const estimatedMinutes = Math.ceil(totalCells * (fastMode ? 0.3 : 0.5));
  const estimatedMaxMinutes = Math.ceil(totalCells * (fastMode ? 0.5 : 0.75));

  const canSubmit = companies.length > 0 && selectedVariables.length > 0;

  const handleSubmit = async () => {
    if (!canSubmit) return;

    try {
      const result = await createRun.mutateAsync({
        companies,
        variables: selectedVariables,
        fast_mode: fastMode,
        concurrency: 3,
      });

      // Navigate to the run progress/results page
      router.push(`/runs/${result.run_id}`);
    } catch (error) {
      console.error("Failed to start research:", error);
    }
  };

  return (
    <>
      <Header 
        title="New Competitive Analysis" 
        description="Configure companies and variables to research"
      />

      <div className="p-6 max-w-4xl mx-auto space-y-6">
        {/* Companies Section */}
        <Card>
          <CardHeader>
            <CardTitle>Companies</CardTitle>
            <CardDescription>
              Add the companies you want to analyze. Press Enter or click to add.
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

        {/* Variables Section */}
        <Card>
          <CardHeader>
            <CardTitle>Research Variables</CardTitle>
            <CardDescription>
              Select which aspects of each company you want to research.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <VariableSelector
              selectedVariables={selectedVariables}
              onChange={setSelectedVariables}
            />
          </CardContent>
        </Card>

        {/* Options Section */}
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
              {/* Estimate */}
              <div className="space-y-2">
                {companies.length === 0 ? (
                  <p className="text-muted-foreground flex items-center gap-2">
                    <AlertCircle className="h-4 w-4" />
                    Add at least one company to continue
                  </p>
                ) : selectedVariables.length === 0 ? (
                  <p className="text-muted-foreground flex items-center gap-2">
                    <AlertCircle className="h-4 w-4" />
                    Select at least one variable to continue
                  </p>
                ) : (
                  <>
                    <p className="text-lg font-medium">
                      {companies.length} companies × {selectedVariables.length} variables ={" "}
                      <span className="text-primary">{totalCells} cells</span>
                    </p>
                    <p className="text-sm text-muted-foreground flex items-center gap-2">
                      <Clock className="h-4 w-4" />
                      Estimated time: ~{estimatedMinutes}-{estimatedMaxMinutes} minutes
                      {fastMode && " (fast mode)"}
                    </p>
                  </>
                )}
              </div>

              {/* Submit Button */}
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
      </div>
    </>
  );
}
