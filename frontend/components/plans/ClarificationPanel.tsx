"use client";

import type { ClarificationQuestion } from "@/lib/types";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { MessageCircle } from "lucide-react";
import { useState } from "react";
import { cn } from "@/lib/utils";

export interface ClarificationAnswer {
  question_id: string;
  option_id?: string;
  free_text?: string;
}

interface ClarificationPanelProps {
  questions: ClarificationQuestion[];
  onAnswer?: (questionId: string, optionId: string | null, freeText: string | null) => void;
  onComplete?: (answers: ClarificationAnswer[]) => void;
  /** When user selects the "Specific brands or subsidiaries" option (id: subsidiaries_only), call this so parent can open the subsidiary selector modal */
  onSubsidiaryOptionSelected?: () => void;
  disabled?: boolean;
  className?: string;
}

export function ClarificationPanel({
  questions,
  onAnswer,
  onComplete,
  onSubsidiaryOptionSelected,
  disabled,
  className,
}: ClarificationPanelProps) {
  const [answers, setAnswers] = useState<Record<string, { optionId?: string; freeText?: string }>>({});
  const [showOtherFor, setShowOtherFor] = useState<string | null>(null);

  if (!questions.length) return null;

  const handleOption = (questionId: string, optionId: string, label: string) => {
    if (optionId === "other" || label.toLowerCase() === "other") {
      setShowOtherFor(questionId);
      setAnswers((prev) => ({ ...prev, [questionId]: { optionId: "other" } }));
      onAnswer?.(questionId, "other", null);
    } else {
      setShowOtherFor((q) => (q === questionId ? null : q));
      setAnswers((prev) => ({ ...prev, [questionId]: { optionId } }));
      onAnswer?.(questionId, optionId, null);
      if (optionId === "subsidiaries_only") {
        onSubsidiaryOptionSelected?.();
      }
    }
  };

  const handleFreeText = (questionId: string, value: string) => {
    setAnswers((prev) => ({
      ...prev,
      [questionId]: { ...prev[questionId], optionId: "other", freeText: value },
    }));
    onAnswer?.(questionId, "other", value || null);
  };

  const allAnswered = questions.every((q) => answers[q.id]?.optionId || (answers[q.id]?.optionId === "other" && answers[q.id]?.freeText?.trim()));

  const currentAnswers: ClarificationAnswer[] = questions.map((q) => ({
    question_id: q.id,
    option_id: answers[q.id]?.optionId,
    free_text: answers[q.id]?.freeText,
  }));

  return (
    <Card className={cn("border-dashed border-primary/30", className)}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <MessageCircle className="h-4 w-4 text-muted-foreground" />
          Quick clarifications
        </CardTitle>
        <CardDescription>
          Answer these to refine the plan. You can skip and continue.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {questions.map((q) => (
          <div key={q.id} className="space-y-2">
            <p className="text-sm font-medium">{q.question}</p>
            {q.context && (
              <p className="text-xs text-muted-foreground">{q.context}</p>
            )}
            <div className="flex flex-wrap gap-2">
              {q.options.map((opt) => (
                <Button
                  key={opt.id}
                  type="button"
                  variant={answers[q.id]?.optionId === opt.id ? "default" : "outline"}
                  size="sm"
                  disabled={disabled}
                  onClick={() => handleOption(q.id, opt.id, opt.label)}
                >
                  {opt.label}
                </Button>
              ))}
            </div>
            {showOtherFor === q.id && q.allow_free_text !== false && (
              <div className="pt-2">
                <Input
                  placeholder="Type your answer..."
                  className="max-w-md"
                  disabled={disabled}
                  onChange={(e) => handleFreeText(q.id, e.target.value)}
                />
              </div>
            )}
          </div>
        ))}
        {allAnswered && onComplete && (
          <div className="pt-2">
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => onComplete(currentAnswers)}
            >
              Apply answers
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
