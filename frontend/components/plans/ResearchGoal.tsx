"use client";

import type { ResearchGoalResult, ClarificationQuestion } from "@/lib/types";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Plus, X } from "lucide-react";
import { ClarificationPanel } from "./ClarificationPanel";
import { useState } from "react";

interface ResearchGoalProps {
  goal: ResearchGoalResult;
  clarifications: ClarificationQuestion[];
  onGoalChange: (goal: Partial<ResearchGoalResult>) => void;
  onAnswer?: (questionId: string, optionId: string | null, freeText: string | null) => void;
  disabled?: boolean;
}

export function ResearchGoal({
  goal,
  clarifications,
  onGoalChange,
  onAnswer,
  disabled,
}: ResearchGoalProps) {
  const [newQuestion, setNewQuestion] = useState("");

  const addQuestion = () => {
    const q = newQuestion.trim();
    if (q && !goal.key_questions.includes(q)) {
      onGoalChange({ key_questions: [...goal.key_questions, q] });
      setNewQuestion("");
    }
  };

  const removeQuestion = (index: number) => {
    onGoalChange({
      key_questions: goal.key_questions.filter((_, i) => i !== index),
    });
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Research mission</CardTitle>
          <CardDescription>
            What we’re trying to learn and why. Edit as needed.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Textarea
            value={goal.mission_statement}
            onChange={(e) => onGoalChange({ mission_statement: e.target.value })}
            placeholder="e.g. Understand competitive positioning and white space in digital payments..."
            rows={4}
            className="resize-y"
            disabled={disabled}
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Key questions</CardTitle>
          <CardDescription>
            Questions the report must answer. Add, edit, or remove.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <ul className="space-y-2">
            {goal.key_questions.map((q, i) => (
              <li key={i} className="flex items-start gap-2">
                <span className="text-muted-foreground shrink-0">{i + 1}.</span>
                <span className="flex-1 text-sm">{q}</span>
                {!disabled && (
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon-xs"
                    onClick={() => removeQuestion(i)}
                  >
                    <X className="h-3 w-3" />
                  </Button>
                )}
              </li>
            ))}
          </ul>
          <div className="flex gap-2">
            <Input
              value={newQuestion}
              onChange={(e) => setNewQuestion(e.target.value)}
              placeholder="Add a key question..."
              className="flex-1"
              disabled={disabled}
              onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), addQuestion())}
            />
            <Button type="button" size="sm" onClick={addQuestion} disabled={disabled}>
              <Plus className="h-4 w-4" />
            </Button>
          </div>
        </CardContent>
      </Card>

      {goal.hypothesis != null && goal.hypothesis !== "" && (
        <Card>
          <CardHeader>
            <CardTitle>Initial hypothesis</CardTitle>
            <CardDescription>
              A testable hypothesis the deep dive will confirm or challenge.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Textarea
              value={goal.hypothesis}
              onChange={(e) => onGoalChange({ hypothesis: e.target.value })}
              rows={2}
              className="resize-y"
              disabled={disabled}
            />
          </CardContent>
        </Card>
      )}

      <div className="flex items-center gap-2">
        <span className="text-sm font-medium">Perspective:</span>
        <select
          value={goal.perspective}
          onChange={(e) => onGoalChange({ perspective: e.target.value })}
          className="rounded-md border bg-background px-3 py-2 text-sm"
          disabled={disabled}
        >
          <option value="neutral">Neutral landscape</option>
          <option value="venture">From a venture / new entrant</option>
        </select>
      </div>

      {clarifications.length > 0 && (
        <ClarificationPanel
          questions={clarifications}
          onAnswer={onAnswer}
          disabled={disabled}
        />
      )}
    </div>
  );
}
