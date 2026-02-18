"use client";

import type { IntelligenceQuestion, IntelligenceAnswer } from "@/lib/types";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Loader2, Lightbulb, ChevronRight, Check, SkipForward } from "lucide-react";
import { useState, useCallback, useEffect } from "react";
import { cn } from "@/lib/utils";

interface FollowUpGroup {
  parentQuestionId: string;
  parentOptionIds: string[];
  questions: IntelligenceQuestion[];
}

interface IntelligenceQuestionsPanelProps {
  questions: IntelligenceQuestion[];
  onComplete: (answers: IntelligenceAnswer[]) => void;
  onSkip: () => void;
  onRequestFollowUp?: (
    questionId: string,
    selectedOptionIds: string[],
    currentAnswers: IntelligenceAnswer[],
  ) => void;
  followUpGroups?: FollowUpGroup[];
  isLoadingFollowUp?: boolean;
  isLoadingQuestions?: boolean;
  disabled?: boolean;
  stepLabel?: string;
}

export function IntelligenceQuestionsPanel({
  questions,
  onComplete,
  onSkip,
  onRequestFollowUp,
  followUpGroups = [],
  isLoadingFollowUp = false,
  isLoadingQuestions = false,
  disabled = false,
  stepLabel = "Help us focus the suggestions",
}: IntelligenceQuestionsPanelProps) {
  const [selections, setSelections] = useState<
    Record<string, { optionIds: string[]; freeText?: string }>
  >({});
  const [showOtherFor, setShowOtherFor] = useState<Set<string>>(new Set());
  const [requestedFollowUps, setRequestedFollowUps] = useState<Set<string>>(new Set());

  const allQuestions = [
    ...questions,
    ...followUpGroups.flatMap((g) => g.questions),
  ];

  const handleToggleOption = useCallback(
    (questionId: string, optionId: string, optionLabel: string, isMultiple: boolean) => {
      setSelections((prev) => {
        const current = prev[questionId]?.optionIds ?? [];

        if (optionId === "other") {
          setShowOtherFor((s) => {
            const next = new Set(s);
            if (next.has(questionId)) {
              next.delete(questionId);
            } else {
              next.add(questionId);
            }
            return next;
          });
          if (current.includes("other")) {
            return {
              ...prev,
              [questionId]: {
                ...prev[questionId],
                optionIds: current.filter((id) => id !== "other"),
              },
            };
          }
          return {
            ...prev,
            [questionId]: {
              ...prev[questionId],
              optionIds: isMultiple ? [...current, "other"] : ["other"],
            },
          };
        }

        setShowOtherFor((s) => {
          const next = new Set(s);
          if (!isMultiple) next.delete(questionId);
          return next;
        });

        let newIds: string[];
        if (isMultiple) {
          newIds = current.includes(optionId)
            ? current.filter((id) => id !== optionId)
            : [...current, optionId];
        } else {
          newIds = current.includes(optionId) ? [] : [optionId];
        }

        return {
          ...prev,
          [questionId]: {
            ...prev[questionId],
            optionIds: newIds,
          },
        };
      });
    },
    [],
  );

  const handleFreeText = useCallback((questionId: string, value: string) => {
    setSelections((prev) => ({
      ...prev,
      [questionId]: {
        ...prev[questionId],
        optionIds: prev[questionId]?.optionIds ?? ["other"],
        freeText: value,
      },
    }));
  }, []);

  // When a question is answered, check if we should request follow-ups
  useEffect(() => {
    if (!onRequestFollowUp) return;

    for (const q of questions) {
      const sel = selections[q.id];
      if (!sel?.optionIds?.length) continue;
      if (sel.optionIds.length === 1 && sel.optionIds[0] === "other") continue;

      const key = `${q.id}:${sel.optionIds.sort().join(",")}`;
      if (requestedFollowUps.has(key)) continue;

      setRequestedFollowUps((prev) => new Set(prev).add(key));
      onRequestFollowUp(q.id, sel.optionIds, buildAnswers());
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selections, questions, onRequestFollowUp]);

  const buildAnswers = useCallback((): IntelligenceAnswer[] => {
    return allQuestions
      .filter((q) => selections[q.id]?.optionIds?.length)
      .map((q) => {
        const sel = selections[q.id];
        const selectedLabels = sel.optionIds
          .map((oid) => q.options.find((o) => o.id === oid)?.label ?? oid)
          .filter(Boolean);
        return {
          question_id: q.id,
          question_text: q.question,
          selected_option_ids: sel.optionIds,
          selected_labels: selectedLabels,
          free_text: sel.freeText,
        };
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [allQuestions, selections]);

  const hasAnyAnswer = Object.values(selections).some(
    (s) => s.optionIds.length > 0,
  );

  const renderQuestion = (q: IntelligenceQuestion, isFollowUp = false) => {
    const sel = selections[q.id]?.optionIds ?? [];
    const isMultiple = q.allow_multiple !== false;

    return (
      <div
        key={q.id}
        className={cn(
          "space-y-3 transition-all duration-300 ease-in-out",
          isFollowUp && "ml-6 pl-4 border-l-2 border-primary/20",
        )}
      >
        <div className="space-y-1">
          <p className="text-sm font-medium">{q.question}</p>
          {q.context && (
            <p className="text-xs text-muted-foreground">{q.context}</p>
          )}
          {isMultiple && (
            <p className="text-xs text-muted-foreground/60">Select one or more</p>
          )}
        </div>
        <div className="flex flex-wrap gap-2">
          {q.options.map((opt) => {
            const isSelected = sel.includes(opt.id);
            return (
              <Button
                key={opt.id}
                type="button"
                variant={isSelected ? "default" : "outline"}
                size="sm"
                disabled={disabled}
                onClick={() =>
                  handleToggleOption(q.id, opt.id, opt.label, isMultiple)
                }
                className={cn(
                  "transition-all",
                  isSelected && "ring-1 ring-primary/50",
                )}
              >
                {isSelected && (
                  <Check className="h-3 w-3 mr-1 shrink-0" />
                )}
                {opt.label}
              </Button>
            );
          })}
        </div>
        {q.options.some((o) => o.description) && sel.length > 0 && (
          <div className="space-y-1">
            {q.options
              .filter((o) => sel.includes(o.id) && o.description)
              .map((o) => (
                <p key={o.id} className="text-xs text-muted-foreground italic">
                  {o.label}: {o.description}
                </p>
              ))}
          </div>
        )}
        {showOtherFor.has(q.id) && q.allow_free_text !== false && (
          <div className="pt-1">
            <Input
              placeholder="Type your answer..."
              className="max-w-md"
              disabled={disabled}
              value={selections[q.id]?.freeText ?? ""}
              onChange={(e) => handleFreeText(q.id, e.target.value)}
            />
          </div>
        )}
        {q.follow_up_hint && sel.length > 0 && (
          <p className="text-xs text-primary/70 flex items-center gap-1">
            <ChevronRight className="h-3 w-3" />
            {q.follow_up_hint}
          </p>
        )}
      </div>
    );
  };

  if (isLoadingQuestions) {
    return (
      <Card className="border-dashed border-primary/30">
        <CardContent className="py-8 flex flex-col items-center gap-3">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          <p className="text-sm text-muted-foreground">
            Generating intelligence questions...
          </p>
        </CardContent>
      </Card>
    );
  }

  if (!questions.length) return null;

  return (
    <Card className="border-dashed border-primary/30">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Lightbulb className="h-4 w-4 text-amber-500" />
          {stepLabel}
        </CardTitle>
        <CardDescription>
          Answer these questions to get more targeted results. You can also skip
          and go straight to generation.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {questions.map((q) => (
          <div key={q.id} className="space-y-4">
            {renderQuestion(q)}
            {followUpGroups
              .filter((g) => g.parentQuestionId === q.id)
              .flatMap((g) =>
                g.questions.map((fq) => renderQuestion(fq, true)),
              )}
          </div>
        ))}

        {isLoadingFollowUp && (
          <div className="flex items-center gap-2 ml-6 pl-4 border-l-2 border-primary/20">
            <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
            <p className="text-xs text-muted-foreground">
              Loading follow-up questions...
            </p>
          </div>
        )}

        <div className="flex items-center gap-3 pt-2">
          <Button
            type="button"
            onClick={() => onComplete(buildAnswers())}
            disabled={disabled || (!hasAnyAnswer && false)}
          >
            {hasAnyAnswer ? (
              <>
                Continue with preferences
                <ChevronRight className="h-4 w-4 ml-1" />
              </>
            ) : (
              <>
                Continue without preferences
                <ChevronRight className="h-4 w-4 ml-1" />
              </>
            )}
          </Button>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={onSkip}
            disabled={disabled}
          >
            <SkipForward className="h-4 w-4 mr-1" />
            Skip questions
          </Button>
          {hasAnyAnswer && (
            <Badge variant="secondary" className="text-xs">
              {Object.values(selections).filter((s) => s.optionIds.length > 0).length} answered
            </Badge>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
