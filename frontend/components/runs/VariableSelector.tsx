"use client";

import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

// Variable definitions matching the backend
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
};

interface VariableSelectorProps {
  selectedVariables: string[];
  onChange: (variables: string[]) => void;
  className?: string;
}

export function VariableSelector({
  selectedVariables,
  onChange,
  className,
}: VariableSelectorProps) {
  const allVariables = Object.values(VARIABLE_CATEGORIES).flat();
  const allVariableIds = allVariables.map((v) => v.id);
  const allSelected = allVariableIds.every((id) => selectedVariables.includes(id));
  const someSelected = selectedVariables.length > 0 && !allSelected;

  const toggleVariable = (variableId: string) => {
    if (selectedVariables.includes(variableId)) {
      onChange(selectedVariables.filter((v) => v !== variableId));
    } else {
      onChange([...selectedVariables, variableId]);
    }
  };

  const toggleAll = () => {
    if (allSelected) {
      onChange([]);
    } else {
      onChange(allVariableIds);
    }
  };

  const toggleCategory = (categoryName: string) => {
    const categoryVars = VARIABLE_CATEGORIES[categoryName as keyof typeof VARIABLE_CATEGORIES];
    const categoryIds = categoryVars.map((v) => v.id);
    const allCategorySelected = categoryIds.every((id) =>
      selectedVariables.includes(id)
    );

    if (allCategorySelected) {
      onChange(selectedVariables.filter((v) => !categoryIds.includes(v)));
    } else {
      const newSelection = [...selectedVariables];
      categoryIds.forEach((id) => {
        if (!newSelection.includes(id)) {
          newSelection.push(id);
        }
      });
      onChange(newSelection);
    }
  };

  return (
    <div className={cn("space-y-4", className)}>
      {/* Select All Button */}
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium">
          {selectedVariables.length} of {allVariableIds.length} selected
        </span>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={toggleAll}
        >
          {allSelected ? "Deselect All" : "Select All"}
        </Button>
      </div>

      {/* Category Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {Object.entries(VARIABLE_CATEGORIES).map(([categoryName, variables]) => {
          const categoryIds = variables.map((v) => v.id);
          const categorySelectedCount = categoryIds.filter((id) =>
            selectedVariables.includes(id)
          ).length;
          const allCategorySelected = categorySelectedCount === categoryIds.length;

          return (
            <Card key={categoryName}>
              <CardHeader className="py-3 px-4">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-sm font-semibold">
                    {categoryName}
                  </CardTitle>
                  <button
                    type="button"
                    onClick={() => toggleCategory(categoryName)}
                    className="text-xs text-primary hover:underline"
                  >
                    {allCategorySelected ? "Deselect" : "Select all"}
                  </button>
                </div>
              </CardHeader>
              <CardContent className="py-2 px-4 space-y-2">
                {variables.map((variable) => (
                  <div
                    key={variable.id}
                    className="flex items-center space-x-2"
                  >
                    <Checkbox
                      id={variable.id}
                      checked={selectedVariables.includes(variable.id)}
                      onCheckedChange={() => toggleVariable(variable.id)}
                    />
                    <Label
                      htmlFor={variable.id}
                      className="text-sm font-normal cursor-pointer"
                    >
                      {variable.name}
                    </Label>
                  </div>
                ))}
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}

// Export variable categories for use elsewhere
export { VARIABLE_CATEGORIES };
