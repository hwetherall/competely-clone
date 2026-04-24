"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Header } from "@/components/layout/Header";
import { CompanyInput } from "@/components/runs/CompanyInput";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  useValidateCompanies,
  useSuggestCompanies,
  useGenerateVariables,
  useGenerateGoal,
  useGenerateCustomParameter,
  useStepClarifications,
  useConfidencePreview,
  useCreatePlan,
  useLaunchPlan,
  useIntelligenceQuestions,
  useIntelligenceFollowup,
  useDiscoverGraveyard,
} from "@/lib/api";
import type {
  CompanyProfile,
  CompanySuggestion,
  ClarificationQuestion,
  IntelligenceQuestion,
  IntelligenceAnswer,
  VariableGenerationResponse,
  DynamicVariableDefinition,
  ResearchGoalResult,
  ConfidencePreview,
  GraveyardCompany,
  ParameterPath,
} from "@/lib/types";
import { PlanWizardStepper } from "@/components/plans/PlanWizardStepper";
import { CompanyValidation, type CompanyChoiceState } from "@/components/plans/CompanyValidation";
import { CompanySuggestions } from "@/components/plans/CompanySuggestions";
import { PlanParameterSelector } from "@/components/plans/PlanParameterSelector";
import { ResearchGoal } from "@/components/plans/ResearchGoal";
import { AudienceConfig } from "@/components/plans/AudienceConfig";
import { PlanReview } from "@/components/plans/PlanReview";
import { SubsidiarySelectorModal } from "@/components/plans/SubsidiarySelectorModal";
import { IntelligenceQuestionsPanel } from "@/components/plans/IntelligenceQuestionsPanel";
import { GraveyardDiscovery } from "@/components/plans/GraveyardDiscovery";
import { Loader2, AlertCircle, ChevronRight, Sparkles, BarChart3, Landmark, Workflow } from "lucide-react";

function getDefaultSelection(data: VariableGenerationResponse): string[] {
  const alwaysIds = data.always_variables.map((v) => v.id);
  const tier2Included = data.tier2_recommendations
    .filter((r) => r.include)
    .map((r) => r.variable_id);
  const generatedIds = data.generated_variables.map((v) => v.id);
  return [...alwaysIds, ...tier2Included, ...generatedIds];
}

export default function NewPlanPage() {
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [companyNames, setCompanyNames] = useState<string[]>([]);
  const [companies, setCompanies] = useState<CompanyProfile[]>([]);
  const [step1Clarifications, setStep1Clarifications] = useState<ClarificationQuestion[]>([]);
  const [step1CompanyChoices, setStep1CompanyChoices] = useState<Record<string, CompanyChoiceState>>({});
  const [subsidiaryModalOpen, setSubsidiaryModalOpen] = useState(false);
  const [subsidiaryModalCompanyId, setSubsidiaryModalCompanyId] = useState<string | null>(null);
  const [suggestions, setSuggestions] = useState<CompanySuggestion[]>([]);
  const [suggestionClarifications, setSuggestionClarifications] = useState<ClarificationQuestion[]>([]);
  const [acceptedSuggestionIds, setAcceptedSuggestionIds] = useState<string[]>([]);
  /** For each accepted suggestion: how it was added (group/brand/subsidiaries) and which names to include. */
  const [acceptedSuggestionDetails, setAcceptedSuggestionDetails] = useState<
    Record<string, { mode: "group" | "brand" | "subsidiaries"; names: string[] }>
  >({});
  const [suggestionSubsidiaryModalId, setSuggestionSubsidiaryModalId] = useState<string | null>(null);

  // Intelligence questions state -- per-step
  type IntelStepState = {
    phase: "questions" | "content";
    questions: IntelligenceQuestion[];
    answers: IntelligenceAnswer[];
    followUpGroups: { parentQuestionId: string; parentOptionIds: string[]; questions: IntelligenceQuestion[] }[];
  };
  const emptyIntel: IntelStepState = { phase: "questions", questions: [], answers: [], followUpGroups: [] };
  const [intelByStep, setIntelByStep] = useState<Record<string, IntelStepState>>({
    suggestions: { ...emptyIntel },
    parameters: { ...emptyIntel },
    goal: { ...emptyIntel },
    audience: { ...emptyIntel },
  });

  const getIntel = (stepKey: string): IntelStepState => intelByStep[stepKey] ?? { ...emptyIntel };
  const updateIntel = (stepKey: string, patch: Partial<IntelStepState>) =>
    setIntelByStep((prev) => ({ ...prev, [stepKey]: { ...(prev[stepKey] ?? emptyIntel), ...patch } }));

  const [parameterPath, setParameterPath] = useState<ParameterPath>("competely");
  const [variableData, setVariableData] = useState<VariableGenerationResponse | null>(null);
  const [selectedVariableIds, setSelectedVariableIds] = useState<string[]>([]);
  const [dynamicVariableDefs, setDynamicVariableDefs] = useState<DynamicVariableDefinition[]>([]);
  const [paramClarifications, setParamClarifications] = useState<ClarificationQuestion[]>([]);
  const [goal, setGoal] = useState<ResearchGoalResult>({
    mission_statement: "",
    key_questions: [],
    hypothesis: null,
    perspective: "neutral",
  });
  const [goalClarifications, setGoalClarifications] = useState<ClarificationQuestion[]>([]);
  const [audience, setAudience] = useState("general");
  const [depth, setDepth] = useState<"quick" | "standard" | "deep">("standard");
  const [focusCompanies, setFocusCompanies] = useState<string[]>([]);
  const [knownContext, setKnownContext] = useState("");
  const [confidencePreview, setConfidencePreview] = useState<ConfidencePreview | null>(null);
  const [planId, setPlanId] = useState<string | null>(null);
  const [graveyardEnabled, setGraveyardEnabled] = useState(false);
  const [graveyardCompanies, setGraveyardCompanies] = useState<GraveyardCompany[]>([]);
  const [graveyardError, setGraveyardError] = useState<string | null>(null);

  const validateCompanies = useValidateCompanies();
  const suggestCompanies = useSuggestCompanies();
  const generateVariables = useGenerateVariables();
  const generateGoal = useGenerateGoal();
  const generateCustomParam = useGenerateCustomParameter();
  const stepClarifications = useStepClarifications();
  const confidencePreviewMutation = useConfidencePreview();
  const createPlan = useCreatePlan();
  const launchPlan = useLaunchPlan();
  const intelligenceQuestionsMutation = useIntelligenceQuestions();
  const intelligenceFollowupMutation = useIntelligenceFollowup();
  const discoverGraveyardMutation = useDiscoverGraveyard();

  const finalCompanyNames = (() => {
    const baseNames = companies.flatMap((c) => {
      if (!c.subsidiaries?.length) return [c.official_name];
      const choice = step1CompanyChoices[c.id];
      if (!choice) return [c.official_name];
      if (choice.choice === "brand") return [c.brand_name || c.official_name];
      if (choice.choice === "group") return [c.official_name];
      if (choice.choice === "subsidiaries" && choice.selectedSubsidiaries?.length)
        return choice.selectedSubsidiaries;
      return [c.official_name];
    });
    const suggestionNames = suggestions
      .filter((s) => acceptedSuggestionIds.includes(s.id))
      .flatMap((s) => acceptedSuggestionDetails[s.id]?.names ?? [s.name]);
    return [...baseNames, ...suggestionNames];
  })();

  const handleValidateCompanies = async () => {
    if (companyNames.length < 1) return;
    try {
      const res = await validateCompanies.mutateAsync(companyNames);
      setCompanies(res.companies);
      setStep1Clarifications(res.clarifications);
      setStep1CompanyChoices({});
      setStep(1);
    } catch (e) {
      console.error(e);
    }
  };

  const handleStep1Answer = () => {
    // Other clarification answers can be stored here if needed
  };

  const handleCompanyChoice = (
    companyId: string,
    choice: "brand" | "group" | "subsidiaries",
    selectedSubsidiaries?: string[]
  ) => {
    setStep1CompanyChoices((prev) => ({
      ...prev,
      [companyId]: {
        choice,
        ...(choice === "subsidiaries" && selectedSubsidiaries
          ? { selectedSubsidiaries }
          : {}),
      },
    }));
  };

  const handleOpenSubsidiaryModal = (companyId: string) => {
    setSubsidiaryModalCompanyId(companyId);
    setSubsidiaryModalOpen(true);
  };

  const handleSubsidiaryConfirm = (selected: string[]) => {
    if (subsidiaryModalCompanyId) {
      handleCompanyChoice(subsidiaryModalCompanyId, "subsidiaries", selected);
    }
    setSubsidiaryModalOpen(false);
    setSubsidiaryModalCompanyId(null);
  };

  // ---------- Generic intelligence questions helpers (work for any step) ----------

  const buildIntelContext = (stepKey: string): Record<string, unknown> => {
    const base = {
      companies: companies.map((c) => ({
        official_name: c.official_name,
        industry: c.industry,
        description: c.description,
      })),
    };
    if (stepKey === "parameters" || stepKey === "goal" || stepKey === "audience") {
      return {
        ...base,
        industry_context: variableData?.industry_context ?? "",
        selected_parameters: selectedVariableIds.length,
      };
    }
    return base;
  };

  const skipHandlers: Record<string, () => void> = {
    suggestions: () => handleSuggestionsIntelSkip(),
    parameters: () => handleParamsIntelSkip(),
    goal: () => handleGoalIntelSkip(),
    audience: () => handleAudienceIntelSkip(),
  };

  const handleFetchIntel = async (stepKey: string) => {
    if (companies.length < 2) return;
    try {
      const res = await intelligenceQuestionsMutation.mutateAsync({
        step: stepKey,
        context: buildIntelContext(stepKey),
      });
      if (res.questions.length === 0) {
        skipHandlers[stepKey]?.();
        return;
      }
      updateIntel(stepKey, { questions: res.questions, followUpGroups: [], answers: [], phase: "questions" });
    } catch (e) {
      console.error(e);
      skipHandlers[stepKey]?.();
    }
  };

  const handleIntelFollowUp = (stepKey: string) => async (
    questionId: string,
    selectedOptionIds: string[],
    currentAnswers: IntelligenceAnswer[],
  ) => {
    try {
      const res = await intelligenceFollowupMutation.mutateAsync({
        step: stepKey,
        question_id: questionId,
        selected_options: selectedOptionIds,
        context: buildIntelContext(stepKey),
        previous_answers: currentAnswers,
      });
      if (res.questions.length > 0) {
        updateIntel(stepKey, {
          followUpGroups: [
            ...(getIntel(stepKey).followUpGroups.filter((g) => g.parentQuestionId !== questionId)),
            { parentQuestionId: questionId, parentOptionIds: selectedOptionIds, questions: res.questions },
          ],
        });
      }
    } catch (e) {
      console.error(e);
    }
  };

  // Step 2 (Suggestions) -- intel complete triggers suggest_companies
  const handleSuggestionsIntelComplete = async (answers: IntelligenceAnswer[]) => {
    updateIntel("suggestions", { answers, phase: "content" });
    if (companies.length < 1) return;
    try {
      const res = await suggestCompanies.mutateAsync({
        companies,
        intelligenceAnswers: answers.length > 0 ? answers : undefined,
      });
      setSuggestions(res.suggestions);
      setSuggestionClarifications(res.clarifications);
    } catch (e) {
      console.error(e);
    }
  };

  const handleSuggestionsIntelSkip = async () => {
    updateIntel("suggestions", { answers: [], phase: "content" });
    if (companies.length < 1) return;
    try {
      const res = await suggestCompanies.mutateAsync({ companies });
      setSuggestions(res.suggestions);
      setSuggestionClarifications(res.clarifications);
    } catch (e) {
      console.error(e);
    }
  };

  // Step 3 (Parameters) -- intel complete triggers handleGenerateParameters
  const handleParamsIntelComplete = async (answers: IntelligenceAnswer[]) => {
    updateIntel("parameters", { answers, phase: "content" });
    handleGenerateParameters();
  };

  const handleParamsIntelSkip = async () => {
    updateIntel("parameters", { answers: [], phase: "content" });
    handleGenerateParameters();
  };

  // Step 4 (Goal) -- intel complete triggers handleGenerateGoal
  const handleGoalIntelComplete = async (answers: IntelligenceAnswer[]) => {
    updateIntel("goal", { answers, phase: "content" });
    handleGenerateGoal();
  };

  const handleGoalIntelSkip = async () => {
    updateIntel("goal", { answers: [], phase: "content" });
    handleGenerateGoal();
  };

  // Step 5 (Audience) -- intel complete just shows the audience config
  const handleAudienceIntelComplete = async (answers: IntelligenceAnswer[]) => {
    updateIntel("audience", { answers, phase: "content" });
  };

  const handleAudienceIntelSkip = async () => {
    updateIntel("audience", { answers: [], phase: "content" });
  };

  const handleSuggestCompanies = async () => {
    if (companies.length < 1) return;
    const answers = getIntel("suggestions").answers;
    try {
      const res = await suggestCompanies.mutateAsync({
        companies,
        intelligenceAnswers: answers.length > 0 ? answers : undefined,
      });
      setSuggestions(res.suggestions);
      setSuggestionClarifications(res.clarifications);
    } catch (e) {
      console.error(e);
    }
  };

  const handleAcceptSuggestion = (
    id: string,
    mode: "group" | "brand" | "subsidiaries",
    names: string[]
  ) => {
    setAcceptedSuggestionIds((prev) => (prev.includes(id) ? prev : [...prev, id]));
    setAcceptedSuggestionDetails((prev) => ({ ...prev, [id]: { mode, names } }));
  };

  const handleSuggestionSubsidiaryConfirm = (selected: string[]) => {
    if (suggestionSubsidiaryModalId) {
      handleAcceptSuggestion(suggestionSubsidiaryModalId, "subsidiaries", selected);
    }
    setSuggestionSubsidiaryModalId(null);
  };

  const handleGenerateParameters = async () => {
    const list = finalCompanyNames.length >= 2 ? finalCompanyNames : companies.map((c) => c.official_name);
    if (list.length < 2) return;
    try {
      setParamClarifications([]);
      const res = await generateVariables.mutateAsync({
        companies: list,
        company_profiles: ["public_mature"],
        parameter_path: parameterPath,
      });
      setVariableData(res);
      setSelectedVariableIds(getDefaultSelection(res));
      setDynamicVariableDefs(res.generated_variables);
      setStep(3);
      void stepClarifications.mutateAsync({
        step: "parameters",
        context: { companies: list, industry_context: res.industry_context },
      })
        .then((clarRes) => {
          setParamClarifications(clarRes.clarifications ?? []);
        })
        .catch((clarificationError) => {
          console.error(clarificationError);
        });
    } catch (e) {
      console.error(e);
    }
  };

  const handleGenerateGoal = async () => {
    try {
      const res = await generateGoal.mutateAsync({
        companies: companies.concat(
          suggestions.filter((s) => acceptedSuggestionIds.includes(s.id)).map((s) => ({ id: s.id, input_name: s.name, official_name: s.name, industry: "", description: "" }))
        ),
        industry_context: variableData?.industry_context ?? "",
        parameter_summary: `${selectedVariableIds.length} parameters`,
      });
      setGoal(res.goal);
      setGoalClarifications(res.clarifications ?? []);
      setStep(4);
    } catch (e) {
      console.error(e);
    }
  };

  const handleAddCustomParameter = async (description: string) => {
    try {
      const def = await generateCustomParam.mutateAsync({
        description,
        companies: finalCompanyNames,
        industry_context: variableData?.industry_context ?? "",
      });
      setSelectedVariableIds((prev) => [...prev, def.id]);
      setDynamicVariableDefs((prev) => [...prev, def]);
    } catch (e) {
      console.error(e);
    }
  };

  const buildPlanPayload = () => ({
    title: `Research Plan: ${variableData?.industry_context ?? "Competitive Analysis"}`,
    companies,
    suggested_companies: suggestions,
    accepted_suggestions: acceptedSuggestionIds,
    effective_company_names: finalCompanyNames,
    industry_context: variableData?.industry_context ?? "",
    parameter_path: parameterPath,
    selected_variable_ids: selectedVariableIds,
    dynamic_variables: dynamicVariableDefs,
    parameter_contexts: variableData?.always_parameter_contexts ?? {},
    mission_statement: goal.mission_statement,
    key_questions: goal.key_questions,
    hypothesis: goal.hypothesis,
    perspective: goal.perspective,
    audience,
    depth,
    focus_companies: focusCompanies,
    known_context: knownContext || null,
    graveyard_enabled: graveyardEnabled,
    graveyard_companies: graveyardEnabled ? graveyardCompanies : [],
  });

  const handleSaveDraft = async () => {
    const payload = buildPlanPayload();
    try {
      const res = await createPlan.mutateAsync(payload);
      setPlanId(res.plan_id);
      router.push(`/plans/${res.plan_id}`);
    } catch (e) {
      console.error(e);
    }
  };

  const handleLaunch = async () => {
    let id = planId;
    if (!id) {
      const payload = buildPlanPayload();
      const createRes = await createPlan.mutateAsync(payload);
      id = createRes.plan_id;
      setPlanId(id);
    }
    if (!id) return;
    try {
      const res = await launchPlan.mutateAsync(id);
      router.push(`/runs/${res.run_id}`);
    } catch (e) {
      console.error(e);
    }
  };

  const handleExport = () => {
    const plan = {
      title: `Research Plan: ${variableData?.industry_context ?? "Competitive Analysis"}`,
      companies,
      suggested_companies: suggestions,
      accepted_suggestions: acceptedSuggestionIds,
      industry_context: variableData?.industry_context ?? "",
      selected_variable_ids: selectedVariableIds,
      dynamic_variables: dynamicVariableDefs,
      mission_statement: goal.mission_statement,
      key_questions: goal.key_questions,
      hypothesis: goal.hypothesis,
      perspective: goal.perspective,
      audience,
      depth,
      focus_companies: focusCompanies,
      known_context: knownContext || null,
    };
    const blob = new Blob([JSON.stringify(plan, null, 2)], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "research-plan.json";
    a.click();
    URL.revokeObjectURL(a.href);
  };

  const fetchConfidencePreview = async () => {
    const list = companies.map((c) => ({ id: c.id, official_name: c.official_name }));
    try {
      const res = await confidencePreviewMutation.mutateAsync({
        companies: list,
        industry_context: variableData?.industry_context ?? "",
      });
      setConfidencePreview(res);
    } catch {
      setConfidencePreview(null);
    }
  };

  const handleDiscoverGraveyard = async () => {
    setGraveyardError(null);
    try {
      const res = await discoverGraveyardMutation.mutateAsync({
        companies: finalCompanyNames,
        industry_context: variableData?.industry_context ?? "",
      });
      setGraveyardCompanies(res.companies);
    } catch (e) {
      setGraveyardError(e instanceof Error ? e.message : "Discovery failed");
    }
  };

  const handleSelectionChange = useCallback(
    (ids: string[], defs: DynamicVariableDefinition[]) => {
      setSelectedVariableIds(ids);
      setDynamicVariableDefs(defs);
    },
    []
  );

  return (
    <>
      <Header
        title="New Research Plan"
        description="Create a 5-minute plan, then launch the deep-dive research"
      />
      <div className="p-6 max-w-4xl mx-auto space-y-6">
        <PlanWizardStepper currentStep={step} onStepClick={(s) => {
          setStep(s);
          const stepKeyMap: Record<number, string> = { 2: "suggestions", 3: "parameters", 4: "goal", 5: "audience" };
          const stepKey = stepKeyMap[s];
          if (stepKey) {
            const st = getIntel(stepKey);
            const hasContent = s === 2 ? suggestions.length > 0
              : s === 3 ? variableData !== null
              : s === 4 ? !!goal.mission_statement
              : false;
            if (st.questions.length === 0 && !hasContent && !intelligenceQuestionsMutation.isPending) {
              handleFetchIntel(stepKey);
            }
          }
        }} />

        {step === 1 && (
          <Card>
            <CardHeader>
              <CardTitle>Step 1: Companies</CardTitle>
              <CardDescription>
                Add company names, then validate to get profiles and disambiguation.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <CompanyInput
                companies={companyNames}
                onChange={setCompanyNames}
                placeholder="Enter company name..."
              />
              {companies.length > 0 ? (
                <>
                  <CompanyValidation
                    companies={companies}
                    clarifications={step1Clarifications}
                    companyChoices={step1CompanyChoices}
                    onCompanyChoice={handleCompanyChoice}
                    onOpenSubsidiaryModal={handleOpenSubsidiaryModal}
                    onAnswer={handleStep1Answer}
                  />
                  <SubsidiarySelectorModal
                    open={subsidiaryModalOpen}
                    onClose={() => {
                      setSubsidiaryModalOpen(false);
                      setSubsidiaryModalCompanyId(null);
                    }}
                    companies={companies}
                    companyId={subsidiaryModalCompanyId}
                    initialSelected={
                      subsidiaryModalCompanyId
                        ? step1CompanyChoices[subsidiaryModalCompanyId]
                            ?.selectedSubsidiaries
                        : undefined
                    }
                    onConfirm={handleSubsidiaryConfirm}
                  />
                  <div className="flex gap-2">
                    <Button
                      onClick={() => {
                        setStep(2);
                        handleFetchIntel("suggestions");
                      }}
                      disabled={finalCompanyNames.length < 2}
                    >
                      Next: Suggestions
                      <ChevronRight className="h-4 w-4 ml-1" />
                    </Button>
                    <Button
                      variant="outline"
                      onClick={handleSuggestCompanies}
                      disabled={suggestCompanies.isPending || companies.length < 2}
                    >
                      {suggestCompanies.isPending ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <Sparkles className="h-4 w-4 mr-1" />
                      )}
                      Refresh suggestions
                    </Button>
                  </div>
                </>
              ) : (
                <Button
                  onClick={handleValidateCompanies}
                  disabled={companyNames.length < 1 || validateCompanies.isPending}
                >
                  {validateCompanies.isPending ? (
                    <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  ) : (
                    <Sparkles className="h-4 w-4 mr-2" />
                  )}
                  Validate companies
                </Button>
              )}
              {validateCompanies.isError && (
                <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-3 text-sm text-destructive">
                  <p className="flex items-center gap-2 font-medium">
                    <AlertCircle className="h-4 w-4 shrink-0" />
                    Validation failed
                  </p>
                  <p className="mt-1 text-muted-foreground text-destructive/90">
                    {validateCompanies.error instanceof Error
                      ? validateCompanies.error.message
                      : "Could not reach the API. If using a deployed backend, ensure it includes the Research Plans routes and CORS allows your frontend origin."}
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {step === 2 && (() => {
          const si = getIntel("suggestions");
          return (
            <Card>
              <CardHeader>
                <CardTitle>Step 2: Additional companies</CardTitle>
                <CardDescription>
                  {si.phase === "questions" && suggestions.length === 0
                    ? "Answer a few questions to get more targeted competitor suggestions."
                    : "Add suggested companies or skip. Then continue to parameters."}
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Phase 1: Intelligence questions (before suggestions) */}
                {si.phase === "questions" && suggestions.length === 0 && (
                  <>
                    <IntelligenceQuestionsPanel
                      questions={si.questions}
                      onComplete={handleSuggestionsIntelComplete}
                      onSkip={handleSuggestionsIntelSkip}
                      onRequestFollowUp={handleIntelFollowUp("suggestions")}
                      followUpGroups={si.followUpGroups}
                      isLoadingFollowUp={intelligenceFollowupMutation.isPending}
                      isLoadingQuestions={intelligenceQuestionsMutation.isPending}
                      disabled={suggestCompanies.isPending}
                      stepLabel="Before we suggest competitors..."
                    />
                    {suggestCompanies.isPending && (
                      <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        <Loader2 className="h-4 w-4 animate-spin" />
                        Generating tailored suggestions based on your preferences...
                      </div>
                    )}
                  </>
                )}

                {/* Phase 2: Suggestions list (after intelligence questions or skip) */}
                {si.phase === "content" && suggestions.length === 0 && suggestCompanies.isPending && (
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Generating competitor suggestions...
                  </div>
                )}

                {suggestions.length > 0 && (
                  <>
                    {si.answers.length > 0 && (
                      <div className="rounded-lg border border-primary/20 bg-primary/5 p-3 text-xs text-muted-foreground">
                        <p className="font-medium text-foreground mb-1">Suggestions tailored by your preferences:</p>
                        {si.answers.map((a) => (
                          <p key={a.question_id}>
                            {a.question_text}: <span className="text-foreground">{a.selected_labels.join(", ")}</span>
                            {a.free_text ? ` (${a.free_text})` : ""}
                          </p>
                        ))}
                      </div>
                    )}
                    <CompanySuggestions
                      suggestions={suggestions}
                      clarifications={suggestionClarifications}
                      acceptedIds={acceptedSuggestionIds}
                      acceptedDetails={acceptedSuggestionDetails}
                      onAcceptSuggestion={handleAcceptSuggestion}
                      onSkip={() => {}}
                      onOpenSubsidiaryModal={setSuggestionSubsidiaryModalId}
                    />
                    <SubsidiarySelectorModal
                      open={suggestionSubsidiaryModalId != null}
                      onClose={() => setSuggestionSubsidiaryModalId(null)}
                      companies={suggestions.map((s) => ({
                        id: s.id,
                        input_name: s.name,
                        official_name: s.name,
                        industry: "",
                        description: "",
                        subsidiaries: s.subsidiaries ?? [],
                        brand_name: s.brand_name ?? undefined,
                      }))}
                      companyId={suggestionSubsidiaryModalId}
                      initialSelected={
                        suggestionSubsidiaryModalId &&
                        acceptedSuggestionDetails[suggestionSubsidiaryModalId]?.mode === "subsidiaries"
                          ? acceptedSuggestionDetails[suggestionSubsidiaryModalId].names
                          : undefined
                      }
                      onConfirm={handleSuggestionSubsidiaryConfirm}
                    />
                    <div className="flex gap-2">
                      <Button
                        onClick={() => {
                          setStep(3);
                          if (getIntel("parameters").questions.length === 0 && !variableData) handleFetchIntel("parameters");
                        }}
                        disabled={finalCompanyNames.length < 2}
                      >
                        Next: Parameters
                        <ChevronRight className="h-4 w-4 ml-1" />
                      </Button>
                      <Button
                        variant="outline"
                        onClick={() => {
                          setSuggestions([]);
                          updateIntel("suggestions", { ...emptyIntel });
                          handleFetchIntel("suggestions");
                        }}
                        disabled={suggestCompanies.isPending}
                      >
                        <Sparkles className="h-4 w-4 mr-1" />
                        Re-do with different preferences
                      </Button>
                    </div>
                  </>
                )}

                {suggestCompanies.isError && (
                  <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-3 text-sm text-destructive">
                    <p className="flex items-center gap-2 font-medium">
                      <AlertCircle className="h-4 w-4 shrink-0" />
                      Suggestion generation failed
                    </p>
                    <p className="mt-1 text-muted-foreground text-destructive/90">
                      {suggestCompanies.error instanceof Error
                        ? suggestCompanies.error.message
                        : "Could not generate suggestions. Check API connection."}
                    </p>
                  </div>
                )}
              </CardContent>
            </Card>
          );
        })()}

        {step === 3 && (() => {
          const pi = getIntel("parameters");
          const pathNotChosen = !variableData && pi.phase === "questions";
          return (
            <Card>
              <CardHeader>
                <CardTitle>Step 3: Parameters</CardTitle>
                <CardDescription>
                  {pathNotChosen
                    ? "Choose your analysis framework, then we'll generate parameters."
                    : "Generate and select research parameters. Add custom ones if needed."}
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Path selector */}
                {!variableData && (
                  <div className="grid gap-3 lg:grid-cols-3">
                    <button
                      type="button"
                      onClick={() => setParameterPath("competely")}
                      className={`relative rounded-xl border-2 p-5 text-left transition-all ${
                        parameterPath === "competely"
                          ? "border-primary bg-primary/5 shadow-sm"
                          : "border-muted hover:border-muted-foreground/30"
                      }`}
                    >
                      <div className="flex items-center gap-2 mb-2">
                        <BarChart3 className="h-5 w-5 text-primary" />
                        <h4 className="font-semibold text-sm">Competely Path</h4>
                      </div>
                      <p className="text-xs text-muted-foreground leading-relaxed">
                        Product-comparison lens. Best for understanding how products stack up on features, pricing, customers, and market share.
                      </p>
                      {parameterPath === "competely" && (
                        <span className="absolute top-3 right-3 h-2 w-2 rounded-full bg-primary" />
                      )}
                    </button>
                    <button
                      type="button"
                      onClick={() => setParameterPath("avis")}
                      className={`relative rounded-xl border-2 p-5 text-left transition-all ${
                        parameterPath === "avis"
                          ? "border-primary bg-primary/5 shadow-sm"
                          : "border-muted hover:border-muted-foreground/30"
                      }`}
                    >
                      <div className="flex items-center gap-2 mb-2">
                        <Landmark className="h-5 w-5 text-primary" />
                        <h4 className="font-semibold text-sm">AVIS Path</h4>
                      </div>
                      <p className="text-xs text-muted-foreground leading-relaxed">
                        Investment-thesis lens (Innovera AVIS framework). Evaluates moats, funding, GTM, team, IP defensibility, and exit readiness.
                      </p>
                      {parameterPath === "avis" && (
                        <span className="absolute top-3 right-3 h-2 w-2 rounded-full bg-primary" />
                      )}
                    </button>
                    <button
                      type="button"
                      onClick={() => setParameterPath("innovera")}
                      className={`relative rounded-xl border-2 p-5 text-left transition-all ${
                        parameterPath === "innovera"
                          ? "border-primary bg-primary/5 shadow-sm"
                          : "border-muted hover:border-muted-foreground/30"
                      }`}
                    >
                      <div className="flex items-center gap-2 mb-2">
                        <Workflow className="h-5 w-5 text-primary" />
                        <h4 className="font-semibold text-sm">Innovera Lens</h4>
                      </div>
                      <p className="text-xs text-muted-foreground leading-relaxed">
                        Business-model lens for AI-native decision platforms and consulting firms adopting blended AI plus human delivery.
                      </p>
                      {parameterPath === "innovera" && (
                        <span className="absolute top-3 right-3 h-2 w-2 rounded-full bg-primary" />
                      )}
                    </button>
                  </div>
                )}

                {/* Phase 1: Intelligence questions (before parameter generation) */}
                {pi.phase === "questions" && !variableData && (
                  <>
                    <IntelligenceQuestionsPanel
                      questions={pi.questions}
                      onComplete={handleParamsIntelComplete}
                      onSkip={handleParamsIntelSkip}
                      onRequestFollowUp={handleIntelFollowUp("parameters")}
                      followUpGroups={pi.followUpGroups}
                      isLoadingFollowUp={intelligenceFollowupMutation.isPending}
                      isLoadingQuestions={intelligenceQuestionsMutation.isPending}
                      disabled={generateVariables.isPending}
                      stepLabel="Before we generate parameters..."
                    />
                    {generateVariables.isPending && (
                      <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        <Loader2 className="h-4 w-4 animate-spin" />
                        Generating parameters based on your preferences...
                      </div>
                    )}
                  </>
                )}

                {/* Phase 2: Parameters (after intel or skip) */}
                {pi.phase === "content" && !variableData && generateVariables.isPending && (
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Generating research parameters...
                  </div>
                )}

                {variableData && (
                  <>
                    {pi.answers.length > 0 && (
                      <div className="rounded-lg border border-primary/20 bg-primary/5 p-3 text-xs text-muted-foreground">
                        <p className="font-medium text-foreground mb-1">Parameters guided by your preferences:</p>
                        {pi.answers.map((a) => (
                          <p key={a.question_id}>
                            {a.question_text}: <span className="text-foreground">{a.selected_labels.join(", ")}</span>
                            {a.free_text ? ` (${a.free_text})` : ""}
                          </p>
                        ))}
                      </div>
                    )}
                    <PlanParameterSelector
                      data={variableData}
                      selectedVariableIds={selectedVariableIds}
                      dynamicVariableDefs={dynamicVariableDefs}
                      clarifications={paramClarifications}
                      onSelectionChange={handleSelectionChange}
                      onCustomParameter={handleAddCustomParameter}
                      isAddingCustom={generateCustomParam.isPending}
                    />
                    <Button
                      onClick={() => {
                        setStep(4);
                        if (getIntel("goal").questions.length === 0 && !goal.mission_statement) handleFetchIntel("goal");
                      }}
                    >
                      Next: Research goal
                      <ChevronRight className="h-4 w-4 ml-1" />
                    </Button>
                  </>
                )}
              </CardContent>
            </Card>
          );
        })()}

        {step === 4 && (() => {
          const gi = getIntel("goal");
          return (
            <Card>
              <CardHeader>
                <CardTitle>Step 4: Research goal</CardTitle>
                <CardDescription>
                  {gi.phase === "questions" && !goal.mission_statement
                    ? "Answer a few questions to shape the research mission and key questions."
                    : "Mission, key questions, and perspective. Generate or edit."}
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Phase 1: Intelligence questions (before goal generation) */}
                {gi.phase === "questions" && !goal.mission_statement && (
                  <>
                    <IntelligenceQuestionsPanel
                      questions={gi.questions}
                      onComplete={handleGoalIntelComplete}
                      onSkip={handleGoalIntelSkip}
                      onRequestFollowUp={handleIntelFollowUp("goal")}
                      followUpGroups={gi.followUpGroups}
                      isLoadingFollowUp={intelligenceFollowupMutation.isPending}
                      isLoadingQuestions={intelligenceQuestionsMutation.isPending}
                      disabled={generateGoal.isPending}
                      stepLabel="Before we define the research goal..."
                    />
                    {generateGoal.isPending && (
                      <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        <Loader2 className="h-4 w-4 animate-spin" />
                        Generating research goal based on your preferences...
                      </div>
                    )}
                  </>
                )}

                {/* Phase 2: Goal content */}
                {gi.phase === "content" && !goal.mission_statement && generateGoal.isPending && (
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Generating research goal...
                  </div>
                )}

                {goal.mission_statement && (
                  <>
                    {gi.answers.length > 0 && (
                      <div className="rounded-lg border border-primary/20 bg-primary/5 p-3 text-xs text-muted-foreground">
                        <p className="font-medium text-foreground mb-1">Goal shaped by your preferences:</p>
                        {gi.answers.map((a) => (
                          <p key={a.question_id}>
                            {a.question_text}: <span className="text-foreground">{a.selected_labels.join(", ")}</span>
                            {a.free_text ? ` (${a.free_text})` : ""}
                          </p>
                        ))}
                      </div>
                    )}
                    <ResearchGoal
                      goal={goal}
                      clarifications={goalClarifications}
                      onGoalChange={(g) => setGoal((prev) => ({ ...prev, ...g }))}
                    />
                    <Button
                      onClick={() => {
                        setStep(5);
                        if (getIntel("audience").questions.length === 0) handleFetchIntel("audience");
                      }}
                    >
                      Next: Audience
                      <ChevronRight className="h-4 w-4 ml-1" />
                    </Button>
                  </>
                )}
              </CardContent>
            </Card>
          );
        })()}

        {step === 5 && (() => {
          const ai = getIntel("audience");
          return (
            <Card>
              <CardHeader>
                <CardTitle>Step 5: Audience and depth</CardTitle>
                <CardDescription>
                  {ai.phase === "questions"
                    ? "Answer a few questions to help us tailor the report format."
                    : "Who the report is for and how deep to go."}
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Phase 1: Intelligence questions */}
                {ai.phase === "questions" && (
                  <IntelligenceQuestionsPanel
                    questions={ai.questions}
                    onComplete={handleAudienceIntelComplete}
                    onSkip={handleAudienceIntelSkip}
                    onRequestFollowUp={handleIntelFollowUp("audience")}
                    followUpGroups={ai.followUpGroups}
                    isLoadingFollowUp={intelligenceFollowupMutation.isPending}
                    isLoadingQuestions={intelligenceQuestionsMutation.isPending}
                    stepLabel="Before we configure the audience..."
                  />
                )}

                {/* Phase 2: Audience config */}
                {ai.phase === "content" && (
                  <>
                    {ai.answers.length > 0 && (
                      <div className="rounded-lg border border-primary/20 bg-primary/5 p-3 text-xs text-muted-foreground">
                        <p className="font-medium text-foreground mb-1">Audience guided by your preferences:</p>
                        {ai.answers.map((a) => (
                          <p key={a.question_id}>
                            {a.question_text}: <span className="text-foreground">{a.selected_labels.join(", ")}</span>
                            {a.free_text ? ` (${a.free_text})` : ""}
                          </p>
                        ))}
                      </div>
                    )}
                    <AudienceConfig
                      audience={audience}
                      depth={depth}
                      focusCompanies={focusCompanies}
                      knownContext={knownContext}
                      onAudienceChange={setAudience}
                      onDepthChange={setDepth}
                      onFocusToggle={(name) =>
                        setFocusCompanies((prev) =>
                          prev.includes(name) ? prev.filter((c) => c !== name) : [...prev, name]
                        )
                      }
                      onKnownContextChange={setKnownContext}
                      companyNames={finalCompanyNames}
                    />
                    <div className="mt-6 pt-6 border-t">
                      <GraveyardDiscovery
                        enabled={graveyardEnabled}
                        onToggle={(v) => {
                          setGraveyardEnabled(v);
                          if (v && graveyardCompanies.length === 0) {
                            handleDiscoverGraveyard();
                          }
                        }}
                        companies={graveyardCompanies}
                        onCompaniesChange={setGraveyardCompanies}
                        onDiscover={handleDiscoverGraveyard}
                        isDiscovering={discoverGraveyardMutation.isPending}
                        error={graveyardError}
                      />
                    </div>
                    <Button className="mt-4" onClick={() => setStep(6)}>
                      Next: Review
                      <ChevronRight className="h-4 w-4 ml-1" />
                    </Button>
                  </>
                )}
              </CardContent>
            </Card>
          );
        })()}

        {step === 6 && (
          <Card>
            <CardHeader>
              <CardTitle>Step 6: Review and launch</CardTitle>
              <CardDescription>
                Check the plan, then save as draft or launch the research.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {!confidencePreview && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={fetchConfidencePreview}
                  disabled={confidencePreviewMutation.isPending}
                >
                  {confidencePreviewMutation.isPending ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    "Load feasibility preview"
                  )}
                </Button>
              )}
              <PlanReview
                plan={{
                  companies,
                  suggested_companies: suggestions,
                  accepted_suggestions: acceptedSuggestionIds,
                  industry_context: variableData?.industry_context,
                  parameter_path: parameterPath,
                  selected_variable_ids: selectedVariableIds,
                  dynamic_variables: dynamicVariableDefs,
                  parameter_contexts: variableData?.always_parameter_contexts,
                  mission_statement: goal.mission_statement,
                  key_questions: goal.key_questions,
                  hypothesis: goal.hypothesis,
                  perspective: goal.perspective,
                  audience,
                  depth,
                  focus_companies: focusCompanies,
                  known_context: knownContext,
                  graveyard_enabled: graveyardEnabled,
                  graveyard_companies: graveyardCompanies,
                }}
                confidencePreview={confidencePreview}
                onEditStep={setStep}
                onSaveDraft={handleSaveDraft}
                onLaunch={handleLaunch}
                onExport={handleExport}
                isSaving={createPlan.isPending}
                isLaunching={launchPlan.isPending}
              />
              {launchPlan.isError && (
                <p className="text-sm text-destructive flex items-center gap-2">
                  <AlertCircle className="h-4 w-4" />
                  Launch failed. Check API.
                </p>
              )}
            </CardContent>
          </Card>
        )}
      </div>
    </>
  );
}
