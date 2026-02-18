"use client";

import { useState } from "react";
import { SmartVariableSelector } from "@/components/runs/VariableSelector";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Plus, Loader2 } from "lucide-react";
import type {
  VariableGenerationResponse,
  DynamicVariableDefinition,
  ClarificationQuestion,
} from "@/lib/types";
import { ClarificationPanel } from "./ClarificationPanel";

interface PlanParameterSelectorProps {
  data: VariableGenerationResponse;
  selectedVariableIds: string[];
  dynamicVariableDefs: DynamicVariableDefinition[];
  clarifications: ClarificationQuestion[];
  onSelectionChange: (
    variableIds: string[],
    dynamicDefs: DynamicVariableDefinition[]
  ) => void;
  onCustomParameter?: (description: string) => void;
  onClarificationAnswer?: (
    questionId: string,
    optionId: string | null,
    freeText: string | null
  ) => void;
  isAddingCustom?: boolean;
  disabled?: boolean;
}

export function PlanParameterSelector({
  data,
  selectedVariableIds,
  dynamicVariableDefs,
  clarifications,
  onSelectionChange,
  onCustomParameter,
  onClarificationAnswer,
  isAddingCustom,
  disabled,
}: PlanParameterSelectorProps) {
  const [customInput, setCustomInput] = useState("");

  const handleAddCustom = () => {
    const desc = customInput.trim();
    if (desc && onCustomParameter) {
      onCustomParameter(desc);
      setCustomInput("");
    }
  };

  return (
    <div className="space-y-6">
      <SmartVariableSelector
        data={data}
        selectedVariableIds={selectedVariableIds}
        onSelectionChange={onSelectionChange}
      />
      {onCustomParameter && (
        <div className="flex gap-2">
          <Input
            value={customInput}
            onChange={(e) => setCustomInput(e.target.value)}
            placeholder='e.g. "AI strategy" or "pricing transparency"'
            className="flex-1"
            disabled={disabled}
            onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), handleAddCustom())}
          />
          <Button
            type="button"
            variant="outline"
            onClick={handleAddCustom}
            disabled={!customInput.trim() || isAddingCustom}
          >
            {isAddingCustom ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Plus className="h-4 w-4 mr-1" />
            )}
            Add custom
          </Button>
        </div>
      )}
      {clarifications.length > 0 && (
        <ClarificationPanel
          questions={clarifications}
          onAnswer={onClarificationAnswer}
          disabled={disabled}
        />
      )}
    </div>
  );
}
