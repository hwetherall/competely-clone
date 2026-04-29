"use client";

import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type {
  VariableGenerationResponse,
  DynamicVariableDefinition,
} from "@/lib/types";

interface SmartVariableSelectorProps {
  data: VariableGenerationResponse;
  selectedVariableIds: string[];
  onSelectionChange: (
    variableIds: string[],
    dynamicDefs: DynamicVariableDefinition[]
  ) => void;
  className?: string;
}

export function SmartVariableSelector({
  data,
  selectedVariableIds,
  onSelectionChange,
  className,
}: SmartVariableSelectorProps) {
  const toggleTier2 = (variableId: string) => {
    const next = selectedVariableIds.includes(variableId)
      ? selectedVariableIds.filter((id) => id !== variableId)
      : [...selectedVariableIds, variableId];
    updateSelection(next);
  };

  const toggleGenerated = (variableId: string) => {
    const next = selectedVariableIds.includes(variableId)
      ? selectedVariableIds.filter((id) => id !== variableId)
      : [...selectedVariableIds, variableId];
    updateSelection(next);
  };

  function updateSelection(ids: string[]) {
    const dynamicDefs = data.generated_variables.filter((g) => ids.includes(g.id));
    onSelectionChange(ids, dynamicDefs);
  }

  const totalSelected = selectedVariableIds.length;
  const alwaysByCategory = data.always_variables.reduce<Record<string, typeof data.always_variables>>(
    (acc, variable) => {
      const category = variable.category || "Other";
      acc[category] = acc[category] ?? [];
      acc[category].push(variable);
      return acc;
    },
    {}
  );

  return (
    <div className={cn("space-y-6", className)}>
      {data.industry_context && (
        <p className="text-sm text-muted-foreground">
          Detected context: <span className="font-medium">{data.industry_context}</span>
          {data.always_variables.some(v => v.id.startsWith("avis_")) && (
            <span className="ml-2 inline-flex items-center rounded-full bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary">
              AVIS Framework
            </span>
          )}
          {data.always_variables.some(v => v.id.startsWith("inv_")) && (
            <span className="ml-2 inline-flex items-center rounded-full bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary">
              Innovera Lens
            </span>
          )}
        </p>
      )}

      <div className="text-sm font-medium">
        {totalSelected} parameters selected (always + contextual + industry-specific)
      </div>

      {/* Tier 1: Always included */}
      <Card>
        <CardHeader className="py-3 px-4">
          <CardTitle className="text-sm font-semibold text-muted-foreground">
            Always included
          </CardTitle>
        </CardHeader>
        <CardContent className="py-2 px-4">
          <div className="space-y-4">
            {Object.entries(alwaysByCategory).map(([category, variables]) => (
              <div key={category}>
                <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  {category}
                </p>
                <ul className="space-y-2">
                  {variables.map((v) => (
                    <li key={v.id} className="flex items-start gap-2">
                      <span className="inline-block w-4 h-4 mt-0.5 rounded border border-muted bg-muted/50 shrink-0" />
                      <div className="min-w-0">
                        <span className="text-sm text-muted-foreground">{v.name}</span>
                        {data.always_parameter_contexts?.[v.id] && (
                          <p className="text-xs text-muted-foreground mt-0.5">
                            {data.always_parameter_contexts[v.id]}
                          </p>
                        )}
                      </div>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Tier 2: Contextual (AI-recommended toggles) */}
      <Card>
        <CardHeader className="py-3 px-4">
          <CardTitle className="text-sm font-semibold">
            Contextual parameters
          </CardTitle>
          <p className="text-xs text-muted-foreground">
            Recommended based on your competitor set. You can override.
          </p>
        </CardHeader>
        <CardContent className="py-2 px-4 space-y-2">
          {data.tier2_recommendations.map((rec) => {
            const isIncluded = rec.include;
            const isSelected = selectedVariableIds.includes(rec.variable_id);
            return (
              <div
                key={rec.variable_id}
                className="flex items-start gap-2"
              >
                <Checkbox
                  id={`t2-${rec.variable_id}`}
                  checked={isSelected}
                  onCheckedChange={() => toggleTier2(rec.variable_id)}
                />
                <div className="flex-1 min-w-0">
                  <Label
                    htmlFor={`t2-${rec.variable_id}`}
                    className="text-sm font-normal cursor-pointer"
                  >
                    {rec.variable_id.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
                  </Label>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    {isIncluded ? "Included: " : "Excluded: "}
                    {rec.reason}
                  </p>
                </div>
              </div>
            );
          })}
        </CardContent>
      </Card>

      {/* Tier 3: Industry-specific (generated) */}
      <Card>
        <CardHeader className="py-3 px-4">
          <CardTitle className="text-sm font-semibold">
            Industry-specific parameters
          </CardTitle>
          <p className="text-xs text-muted-foreground">
            Generated for your competitor set. Toggle any you want to include.
          </p>
        </CardHeader>
        <CardContent className="py-2 px-4 space-y-2">
          {data.generated_variables.map((v) => (
            <div
              key={v.id}
              className="flex items-start gap-2"
            >
              <Checkbox
                id={v.id}
                checked={selectedVariableIds.includes(v.id)}
                onCheckedChange={() => toggleGenerated(v.id)}
              />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-1.5">
                  <Label
                    htmlFor={v.id}
                    className="text-sm font-normal cursor-pointer"
                  >
                    {v.name}
                  </Label>
                </div>
                {v.rationale && (
                  <p className="text-xs text-muted-foreground mt-0.5">
                    {v.rationale}
                  </p>
                )}
              </div>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}

// Legacy export for any code that still expects the old categories (e.g. tests)
const VARIABLE_CATEGORIES = {
  "Positioning & Value": [
    { id: "unique_value_proposition", name: "Unique Value Proposition" },
    { id: "positioning", name: "Positioning" },
    { id: "competitive_positioning_summary", name: "Competitive Summary" },
    { id: "differentiation", name: "Differentiation" },
    { id: "brand_promise", name: "Brand Promise" },
  ],
  "Customers": [
    { id: "target_customer_personas", name: "Target Personas" },
    { id: "customer_segmentation", name: "Customer Segmentation" },
    { id: "users", name: "Users" },
    { id: "buyers", name: "Buyers" },
    { id: "use_cases", name: "Use Cases" },
  ],
  "Product": [
    { id: "key_features", name: "Key Features" },
    { id: "advanced_features", name: "Advanced Features" },
    { id: "integrations", name: "Integrations" },
    { id: "technology_stack", name: "Technology Stack" },
    { id: "product_roadmap", name: "Product Roadmap" },
  ],
  "Business": [
    { id: "business_models", name: "Business Models" },
    { id: "pricing_strategy", name: "Pricing Strategy" },
    { id: "market_share", name: "Market Share" },
    { id: "market_size", name: "Market Size" },
    { id: "estimated_revenue", name: "Estimated Revenue" },
  ],
  "Commercial Deep Dive": [
    { id: "inv_packaging", name: "Packaging" },
    { id: "inv_pricing_mechanics", name: "Pricing Mechanics" },
    { id: "inv_contract_structure", name: "Contract Structure" },
  ],
};

export { VARIABLE_CATEGORIES };
