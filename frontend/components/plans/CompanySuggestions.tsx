"use client";

import type { CompanySuggestion, ClarificationQuestion } from "@/lib/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Plus } from "lucide-react";
import { ClarificationPanel } from "./ClarificationPanel";
import { Badge } from "@/components/ui/badge";

export type SuggestionAcceptMode = "group" | "brand" | "subsidiaries";

interface CompanySuggestionsProps {
  suggestions: CompanySuggestion[];
  clarifications: ClarificationQuestion[];
  acceptedIds: string[];
  /** When a suggestion was added with subsidiaries, the selected names (for "Added (N subsidiaries)" label). */
  acceptedDetails?: Record<string, { mode: SuggestionAcceptMode; names: string[] }>;
  onAcceptSuggestion: (id: string, mode: SuggestionAcceptMode, names: string[]) => void;
  onSkip: (id: string) => void;
  onOpenSubsidiaryModal: (suggestionId: string) => void;
  onAnswer?: (questionId: string, optionId: string | null, freeText: string | null) => void;
  disabled?: boolean;
}

const categoryLabel: Record<string, string> = {
  direct_competitor: "Direct competitor",
  adjacent_disruptor: "Adjacent / disruptor",
  international: "International",
  dark_horse: "Dark horse",
};

export function CompanySuggestions({
  suggestions,
  clarifications,
  acceptedIds,
  acceptedDetails,
  onAcceptSuggestion,
  onSkip,
  onOpenSubsidiaryModal,
  onAnswer,
  disabled,
}: CompanySuggestionsProps) {
  return (
    <div className="space-y-6">
      <p className="text-sm text-muted-foreground">
        Add companies that would make the analysis more robust. Skip any you don’t need.
      </p>
      <div className="space-y-3">
        {suggestions.map((s) => {
          const accepted = acceptedIds.includes(s.id);
          const hasSubsidiaries = (s.subsidiaries?.length ?? 0) > 0;
          const detail = acceptedDetails?.[s.id];

          return (
            <Card key={s.id} className={accepted ? "border-primary/50 bg-primary/5" : ""}>
              <CardHeader className="py-3 px-4 flex flex-row items-start justify-between gap-2">
                <div>
                  <CardTitle className="text-sm font-medium">{s.name}</CardTitle>
                  <Badge variant="secondary" className="mt-1 text-xs">
                    {categoryLabel[s.category] ?? s.category}
                  </Badge>
                </div>
                <div className="flex gap-1 shrink-0 flex-wrap justify-end">
                  {!accepted ? (
                    <>
                      {hasSubsidiaries ? (
                        <>
                          <Button
                            type="button"
                            size="sm"
                            variant="outline"
                            onClick={() =>
                              onAcceptSuggestion(s.id, "brand", [
                                s.brand_name || s.name,
                              ])
                            }
                            disabled={disabled}
                          >
                            Add brand{s.brand_name ? ` (${s.brand_name})` : ""}
                          </Button>
                          <Button
                            type="button"
                            size="sm"
                            variant="outline"
                            onClick={() => onAcceptSuggestion(s.id, "group", [s.name])}
                            disabled={disabled}
                          >
                            Add group
                          </Button>
                          <Button
                            type="button"
                            size="sm"
                            variant="default"
                            onClick={() => onOpenSubsidiaryModal(s.id)}
                            disabled={disabled}
                          >
                            <Plus className="h-4 w-4 mr-1" /> Add subsidiaries…
                          </Button>
                        </>
                      ) : (
                        <>
                          <Button
                            type="button"
                            size="sm"
                            variant="default"
                            onClick={() => onAcceptSuggestion(s.id, "group", [s.name])}
                            disabled={disabled}
                          >
                            <Plus className="h-4 w-4 mr-1" /> Add
                          </Button>
                          <Button
                            type="button"
                            size="sm"
                            variant="ghost"
                            onClick={() => onSkip(s.id)}
                            disabled={disabled}
                          >
                            Skip
                          </Button>
                        </>
                      )}
                    </>
                  ) : (
                    <span className="text-xs text-primary font-medium">
                      Added
                      {detail?.mode === "subsidiaries" && detail.names.length > 0
                        ? ` (${detail.names.length} selected)`
                        : detail?.mode === "brand"
                          ? " (brand)"
                          : detail?.mode === "group"
                            ? " (group)"
                            : ""}
                    </span>
                  )}
                </div>
              </CardHeader>
              <CardContent className="py-2 px-4 text-sm text-muted-foreground">
                <p>{s.rationale}</p>
                <p className="text-xs mt-1">Gap: {s.gap_filled}</p>
              </CardContent>
            </Card>
          );
        })}
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
