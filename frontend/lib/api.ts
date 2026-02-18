/**
 * API client with TanStack Query hooks for data fetching.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import type {
  RunListItem,
  RunDetail,
  RunDetailV2,
  RunProgress,
  RunCreateRequest,
  RunCreateResponse,
  VariableCategories,
  Variable,
  VariableGenerationResponse,
  CompanyProfile,
  CompanySuggestion,
  ClarificationQuestion,
  IntelligenceQuestion,
  IntelligenceAnswer,
  ResearchGoalResult,
  ConfidencePreview,
  ResearchPlan,
  PlanListItem,
  DynamicVariableDefinition,
} from "./types";

// API base URL - adjust based on environment
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// =============================================================================
// Fetch Helpers
// =============================================================================

async function fetchAPI<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  let response: Response;
  try {
    response = await fetch(url, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...options?.headers,
      },
    });
  } catch (err) {
    const message =
      err instanceof TypeError && err.message === "Failed to fetch"
        ? `Could not reach the API at ${url}. Make sure the backend is running (e.g. \`uvicorn api.main:app --reload --port 8000\` from the project root).`
        : err instanceof Error
          ? err.message
          : "Network error";
    throw new Error(message);
  }

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`API Error: ${response.status} - ${error}`);
  }

  return response.json();
}

// =============================================================================
// Variables API
// =============================================================================

export async function getVariables(): Promise<VariableCategories> {
  return fetchAPI<VariableCategories>("/api/variables");
}

export async function getVariablesList(): Promise<Variable[]> {
  return fetchAPI<Variable[]>("/api/variables/list");
}

export function useVariables() {
  return useQuery({
    queryKey: ["variables"],
    queryFn: getVariables,
    staleTime: Infinity, // Variables don't change
  });
}

export function useVariablesList() {
  return useQuery({
    queryKey: ["variables-list"],
    queryFn: getVariablesList,
    staleTime: Infinity,
  });
}

export async function generateVariables(request: { companies: string[]; company_profiles?: string[] }): Promise<VariableGenerationResponse> {
  return fetchAPI<VariableGenerationResponse>("/api/variables/generate", {
    method: "POST",
    body: JSON.stringify(request),
  });
}

export function useGenerateVariables() {
  return useMutation({
    mutationFn: generateVariables,
  });
}

// =============================================================================
// Runs API
// =============================================================================

export async function getRuns(): Promise<RunListItem[]> {
  return fetchAPI<RunListItem[]>("/api/runs");
}

export async function getRun(runId: string): Promise<RunDetail | RunDetailV2> {
  return fetchAPI<RunDetail | RunDetailV2>(`/api/runs/${runId}`);
}

export async function getRunProgress(runId: string): Promise<RunProgress> {
  return fetchAPI<RunProgress>(`/api/runs/${runId}/status`);
}

export async function createRun(request: RunCreateRequest): Promise<RunCreateResponse> {
  return fetchAPI<RunCreateResponse>("/api/runs", {
    method: "POST",
    body: JSON.stringify(request),
  });
}

export function useRuns() {
  return useQuery({
    queryKey: ["runs"],
    queryFn: getRuns,
    refetchInterval: 30000, // Refresh every 30 seconds
  });
}

export function useRun(runId: string) {
  return useQuery({
    queryKey: ["run", runId],
    queryFn: () => getRun(runId),
    enabled: !!runId,
  });
}

export function useRunProgress(runId: string, enabled: boolean = true) {
  return useQuery({
    queryKey: ["progress", runId],
    queryFn: () => getRunProgress(runId),
    enabled: enabled && !!runId,
    refetchInterval: enabled ? 3000 : false, // Poll every 3s while running
  });
}

export function useCreateRun() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: createRun,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["runs"] });
    },
  });
}

// =============================================================================
// Research Plans API
// =============================================================================

export interface ValidateCompaniesResponse {
  companies: CompanyProfile[];
  clarifications: ClarificationQuestion[];
}

export async function validateCompanies(companies: string[]): Promise<ValidateCompaniesResponse> {
  return fetchAPI<ValidateCompaniesResponse>("/api/plans/validate-companies", {
    method: "POST",
    body: JSON.stringify({ companies }),
  });
}

export function useValidateCompanies() {
  return useMutation({ mutationFn: validateCompanies });
}

export interface SuggestCompaniesResponse {
  suggestions: CompanySuggestion[];
  clarifications: ClarificationQuestion[];
}

export async function suggestCompanies(
  companies: CompanyProfile[],
  intelligenceAnswers?: IntelligenceAnswer[],
): Promise<SuggestCompaniesResponse> {
  return fetchAPI<SuggestCompaniesResponse>("/api/plans/suggest-companies", {
    method: "POST",
    body: JSON.stringify({
      companies,
      intelligence_answers: intelligenceAnswers ?? null,
    }),
  });
}

export function useSuggestCompanies() {
  return useMutation({
    mutationFn: ({ companies, intelligenceAnswers }: { companies: CompanyProfile[]; intelligenceAnswers?: IntelligenceAnswer[] }) =>
      suggestCompanies(companies, intelligenceAnswers),
  });
}

// =============================================================================
// Intelligence Questions API
// =============================================================================

export interface IntelligenceQuestionsResponse {
  questions: IntelligenceQuestion[];
}

export async function getIntelligenceQuestions(
  step: string,
  context: Record<string, unknown>,
): Promise<IntelligenceQuestionsResponse> {
  return fetchAPI<IntelligenceQuestionsResponse>("/api/plans/intelligence-questions", {
    method: "POST",
    body: JSON.stringify({ step, context }),
  });
}

export function useIntelligenceQuestions() {
  return useMutation({
    mutationFn: ({ step, context }: { step: string; context: Record<string, unknown> }) =>
      getIntelligenceQuestions(step, context),
  });
}

export async function getIntelligenceFollowup(payload: {
  step: string;
  question_id: string;
  selected_options: string[];
  context: Record<string, unknown>;
  previous_answers: IntelligenceAnswer[];
}): Promise<IntelligenceQuestionsResponse> {
  return fetchAPI<IntelligenceQuestionsResponse>("/api/plans/intelligence-followup", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function useIntelligenceFollowup() {
  return useMutation({
    mutationFn: getIntelligenceFollowup,
  });
}

export interface GenerateGoalResponse {
  goal: ResearchGoalResult;
  clarifications: ClarificationQuestion[];
}

export async function generateGoal(request: {
  companies: CompanyProfile[] | string[];
  industry_context: string;
  parameter_summary?: string;
}): Promise<GenerateGoalResponse> {
  return fetchAPI<GenerateGoalResponse>("/api/plans/generate-goal", {
    method: "POST",
    body: JSON.stringify(request),
  });
}

export function useGenerateGoal() {
  return useMutation({ mutationFn: generateGoal });
}

export async function generateCustomParameter(request: {
  description: string;
  companies?: string[];
  industry_context?: string;
}): Promise<DynamicVariableDefinition> {
  return fetchAPI<DynamicVariableDefinition>("/api/plans/generate-custom-parameter", {
    method: "POST",
    body: JSON.stringify(request),
  });
}

export function useGenerateCustomParameter() {
  return useMutation({ mutationFn: generateCustomParameter });
}

export async function stepClarifications(step: string, context: Record<string, unknown>): Promise<{ clarifications: ClarificationQuestion[] }> {
  return fetchAPI<{ clarifications: ClarificationQuestion[] }>("/api/plans/step-clarifications", {
    method: "POST",
    body: JSON.stringify({ step, context }),
  });
}

export function useStepClarifications() {
  return useMutation({ mutationFn: ({ step, context }: { step: string; context: Record<string, unknown> }) => stepClarifications(step, context) });
}

export async function confidencePreview(payload: {
  companies: { id: string; official_name?: string; name?: string }[];
  industry_context: string;
}): Promise<ConfidencePreview> {
  return fetchAPI<ConfidencePreview>("/api/plans/confidence-preview", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function useConfidencePreview() {
  return useMutation({ mutationFn: confidencePreview });
}

export interface PlanCreateRequest {
  title?: string;
  companies: CompanyProfile[];
  suggested_companies?: CompanySuggestion[];
  accepted_suggestions?: string[];
  effective_company_names?: string[] | null;
  industry_context?: string;
  selected_variable_ids?: string[];
  dynamic_variables?: DynamicVariableDefinition[];
  parameter_contexts?: Record<string, string>;
  mission_statement?: string;
  key_questions?: string[];
  hypothesis?: string | null;
  perspective?: string;
  audience?: string;
  depth?: string;
  focus_companies?: string[];
  known_context?: string | null;
}

export interface PlanCreateResponse {
  plan_id: string;
  status: string;
}

export async function createPlan(request: PlanCreateRequest): Promise<PlanCreateResponse> {
  return fetchAPI<PlanCreateResponse>("/api/plans", {
    method: "POST",
    body: JSON.stringify({
      title: request.title ?? "Research Plan",
      companies: request.companies,
      suggested_companies: request.suggested_companies ?? [],
      accepted_suggestions: request.accepted_suggestions ?? [],
      effective_company_names: request.effective_company_names ?? null,
      industry_context: request.industry_context ?? "",
      selected_variable_ids: request.selected_variable_ids ?? [],
      dynamic_variables: request.dynamic_variables ?? [],
      parameter_contexts: request.parameter_contexts ?? {},
      mission_statement: request.mission_statement ?? "",
      key_questions: request.key_questions ?? [],
      hypothesis: request.hypothesis ?? null,
      perspective: request.perspective ?? "neutral",
      audience: request.audience ?? "general",
      depth: request.depth ?? "standard",
      focus_companies: request.focus_companies ?? [],
      known_context: request.known_context ?? null,
    }),
  });
}

export function useCreatePlan() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: createPlan,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["plans"] });
    },
  });
}

export async function getPlans(): Promise<{ plans: PlanListItem[] }> {
  return fetchAPI<{ plans: PlanListItem[] }>("/api/plans");
}

export function usePlans() {
  return useQuery({
    queryKey: ["plans"],
    queryFn: getPlans,
  });
}

export async function getPlan(planId: string): Promise<ResearchPlan> {
  return fetchAPI<ResearchPlan>(`/api/plans/${planId}`);
}

export function usePlan(planId: string) {
  return useQuery({
    queryKey: ["plan", planId],
    queryFn: () => getPlan(planId),
    enabled: !!planId,
  });
}

export async function updatePlan(planId: string, plan: Partial<ResearchPlan>): Promise<{ id: string; status: string }> {
  return fetchAPI<{ id: string; status: string }>(`/api/plans/${planId}`, {
    method: "PUT",
    body: JSON.stringify(plan),
  });
}

export function useUpdatePlan() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ planId, plan }: { planId: string; plan: Partial<ResearchPlan> }) => updatePlan(planId, plan),
    onSuccess: (_, { planId }) => {
      queryClient.invalidateQueries({ queryKey: ["plan", planId] });
      queryClient.invalidateQueries({ queryKey: ["plans"] });
    },
  });
}

export async function launchPlan(planId: string): Promise<RunCreateResponse> {
  return fetchAPI<RunCreateResponse>(`/api/plans/${planId}/launch`, {
    method: "POST",
  });
}

export function useLaunchPlan() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: launchPlan,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["plans"] });
      queryClient.invalidateQueries({ queryKey: ["runs"] });
    },
  });
}

// =============================================================================
// Utility Functions
// =============================================================================

export function formatDuration(seconds: number): string {
  if (seconds < 60) {
    return `${Math.round(seconds)}s`;
  } else if (seconds < 3600) {
    const minutes = Math.floor(seconds / 60);
    const secs = Math.round(seconds % 60);
    return secs > 0 ? `${minutes}m ${secs}s` : `${minutes}m`;
  } else {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.round((seconds % 3600) / 60);
    return minutes > 0 ? `${hours}h ${minutes}m` : `${hours}h`;
  }
}

export function formatTimestamp(timestamp: string): string {
  try {
    const date = new Date(timestamp);
    return date.toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "numeric",
      minute: "2-digit",
      hour12: true,
    });
  } catch {
    return timestamp;
  }
}

export function getConfidenceColor(confidence: string): string {
  switch (confidence.toLowerCase()) {
    case "high":
      return "bg-green-100 text-green-800 border-green-200";
    case "medium":
      return "bg-yellow-100 text-yellow-800 border-yellow-200";
    case "low":
      return "bg-red-100 text-red-800 border-red-200";
    default:
      return "bg-gray-100 text-gray-800 border-gray-200";
  }
}

export function getConfidenceDot(confidence: string): string {
  switch (confidence.toLowerCase()) {
    case "high":
      return "bg-green-500";
    case "medium":
      return "bg-yellow-500";
    case "low":
      return "bg-red-500";
    default:
      return "bg-gray-400";
  }
}
