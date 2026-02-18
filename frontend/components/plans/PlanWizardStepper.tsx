"use client";

import { cn } from "@/lib/utils";
import { Check } from "lucide-react";

const STEPS = [
  { id: 1, label: "Companies" },
  { id: 2, label: "Suggestions" },
  { id: 3, label: "Parameters" },
  { id: 4, label: "Research goal" },
  { id: 5, label: "Audience" },
  { id: 6, label: "Review" },
];

interface PlanWizardStepperProps {
  currentStep: number;
  onStepClick?: (step: number) => void;
  className?: string;
}

export function PlanWizardStepper({ currentStep, onStepClick, className }: PlanWizardStepperProps) {
  return (
    <nav aria-label="Progress" className={cn("flex items-center justify-center gap-0", className)}>
      {STEPS.map((step, index) => {
        const stepNumber = index + 1;
        const isComplete = currentStep > stepNumber;
        const isCurrent = currentStep === stepNumber;
        const isClickable = stepNumber < currentStep && onStepClick;

        return (
          <div key={step.id} className="flex items-center">
            <div 
              className={cn("flex flex-col items-center", isClickable && "cursor-pointer group")}
              onClick={() => isClickable && onStepClick(stepNumber)}
            >
              <div
                className={cn(
                  "flex size-10 min-w-10 min-h-10 shrink-0 items-center justify-center rounded-full border-2 text-sm font-semibold transition-colors",
                  isComplete && "border-primary bg-primary text-primary-foreground",
                  isCurrent && "border-primary bg-primary text-primary-foreground",
                  !isComplete && !isCurrent && "border-muted-foreground/30 text-muted-foreground",
                  isClickable && "group-hover:opacity-80"
                )}
              >
                {isComplete ? <Check className="h-5 w-5" /> : stepNumber}
              </div>
              <span
                className={cn(
                  "mt-1.5 text-xs font-medium whitespace-nowrap",
                  isCurrent ? "text-foreground" : "text-muted-foreground",
                  isClickable && "group-hover:text-foreground"
                )}
              >
                {step.label}
              </span>
            </div>
            {index < STEPS.length - 1 && (
              <div
                className={cn(
                  "mx-2 h-0.5 w-8 sm:w-12 flex-shrink-0",
                  stepNumber < currentStep ? "bg-primary" : "bg-muted"
                )}
              />
            )}
          </div>
        );
      })}
    </nav>
  );
}
