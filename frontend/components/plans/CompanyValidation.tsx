"use client";

import type { CompanyProfile, ClarificationQuestion } from "@/lib/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Building2, MapPin, Globe } from "lucide-react";
import { ClarificationPanel } from "./ClarificationPanel";

export type CompanyChoice = "brand" | "group" | "subsidiaries";
export type CompanyChoiceState = {
  choice: CompanyChoice;
  selectedSubsidiaries?: string[];
};

interface CompanyValidationProps {
  companies: CompanyProfile[];
  clarifications: ClarificationQuestion[];
  companyChoices: Record<string, CompanyChoiceState>;
  onCompanyChoice: (
    companyId: string,
    choice: CompanyChoice,
    selectedSubsidiaries?: string[]
  ) => void;
  onOpenSubsidiaryModal: (companyId: string) => void;
  onAnswer?: (questionId: string, optionId: string | null, freeText: string | null) => void;
  disabled?: boolean;
}

export function CompanyValidation({
  companies,
  clarifications,
  companyChoices,
  onCompanyChoice,
  onOpenSubsidiaryModal,
  onAnswer,
  disabled,
}: CompanyValidationProps) {
  const hasAnySubsidiaries = companies.some((c) => c.subsidiaries?.length);
  const questions = hasAnySubsidiaries
    ? clarifications.filter(
        (q) =>
          !q.options.some((o) => o.id === "subsidiaries_only")
      )
    : clarifications;

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4">
        {companies.map((c) => (
          <Card key={c.id} className="overflow-hidden">
            <CardHeader className="pb-2">
              <CardTitle className="text-base flex items-center gap-2">
                <Building2 className="h-4 w-4 text-muted-foreground shrink-0" />
                {c.official_name}
              </CardTitle>
              <p className="text-xs text-muted-foreground">
                {c.industry}
                {c.headquarters && (
                  <span className="flex items-center gap-1 mt-1">
                    <MapPin className="h-3 w-3 inline" /> {c.headquarters}
                  </span>
                )}
              </p>
            </CardHeader>
            <CardContent className="pt-0 space-y-3">
              <p className="text-sm text-muted-foreground">{c.description}</p>
              {(c.ambiguity_notes || c.subsidiary_notes) && (
                <p className="text-xs text-amber-600 dark:text-amber-400">
                  Note: {c.subsidiary_notes || c.ambiguity_notes}
                </p>
              )}
              {c.website && (
                <a
                  href={c.website.startsWith("http") ? c.website : `https://${c.website}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs text-primary hover:underline flex items-center gap-1"
                >
                  <Globe className="h-3 w-3" /> Website
                </a>
              )}

              {c.subsidiaries && c.subsidiaries.length > 0 && (
                <div className="pt-2 border-t space-y-2">
                  <p className="text-xs font-medium text-muted-foreground">
                    This is a group/conglomerate. Choose scope:
                  </p>
                  <div className="flex flex-wrap gap-2">
                    <Button
                      type="button"
                      size="sm"
                      variant={
                        companyChoices[c.id]?.choice === "brand"
                          ? "default"
                          : "outline"
                      }
                      disabled={disabled}
                      onClick={() => onCompanyChoice(c.id, "brand")}
                    >
                      Select brand
                      {c.brand_name && (
                        <span className="ml-1 opacity-90">
                          ({c.brand_name})
                        </span>
                      )}
                    </Button>
                    <Button
                      type="button"
                      size="sm"
                      variant={
                        companyChoices[c.id]?.choice === "group"
                          ? "default"
                          : "outline"
                      }
                      disabled={disabled}
                      onClick={() => onCompanyChoice(c.id, "group")}
                    >
                      Select group ({c.official_name})
                    </Button>
                    <Button
                      type="button"
                      size="sm"
                      variant={
                        companyChoices[c.id]?.choice === "subsidiaries"
                          ? "default"
                          : "outline"
                      }
                      disabled={disabled}
                      onClick={() => onOpenSubsidiaryModal(c.id)}
                    >
                      Select subsidiaries…
                      {companyChoices[c.id]?.choice === "subsidiaries" &&
                        (companyChoices[c.id].selectedSubsidiaries?.length ?? 0) > 0 && (
                          <span className="ml-1 opacity-90">
                            ({companyChoices[c.id].selectedSubsidiaries!.length} selected)
                          </span>
                        )}
                    </Button>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        ))}
      </div>
      {questions.length > 0 && (
        <ClarificationPanel
          questions={questions}
          onAnswer={onAnswer}
          disabled={disabled}
        />
      )}
    </div>
  );
}
