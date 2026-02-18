/**
 * TypeScript interfaces for the CompetelyClone frontend.
 */

// =============================================================================
// Enums
// =============================================================================

export type ConfidenceLevel = "high" | "medium" | "low" | "none";
export type RunStatus = "pending" | "running" | "completed" | "failed";

// =============================================================================
// Variable Types
// =============================================================================

export interface Variable {
  id: string;
  name: string;
  category: string;
  description?: string;
}

export interface VariableCategories {
  categories: Record<string, Variable[]>;
}

export interface Tier2Recommendation {
  variable_id: string;
  include: boolean;
  reason: string;
}

export interface DynamicVariableDefinition {
  id: string;
  name: string;
  category: string;
  research_prompt: string;
  example_queries: string[];
  answer_spec: string[];
  preferred_source_types: string[];
  key_terms: string[];
  max_concise_chars: number;
  rationale?: string;
}

export interface VariableGenerationResponse {
  industry_context: string;
  always_variables: Variable[];
  always_parameter_contexts?: Record<string, string>;
  tier2_recommendations: Tier2Recommendation[];
  generated_variables: DynamicVariableDefinition[];
}

// =============================================================================
// Source Types
// =============================================================================

export interface Source {
  title: string;
  url: string;
  snippet?: string;
  query?: string;
  domain?: string;
  source_score?: number;
  is_official?: boolean;
}

// =============================================================================
// Cell Types
// =============================================================================

export interface CellData {
  company: string;
  variable_id: string;
  variable_name: string;
  concise: string;
  comprehensive: string;
  sources: Source[];
  confidence: ConfidenceLevel;
  iterations: number;
  total_searches: number;
  timestamp?: string;
  error?: string;
  metadata?: Record<string, unknown>;
}

// =============================================================================
// Run Types
// =============================================================================

export interface RunMetadata {
  total_cells: number;
  successful_cells: number;
  failed_cells: number;
  elapsed_seconds: number;
  concurrency: number;
  fast_mode: boolean;
}

export type RunVersion = "v1" | "v2";

export interface RunListItem {
  id: string;
  companies: string[];
  variables: string[];
  status: RunStatus;
  created_at: string;
  completed_at?: string;
  total_cells: number;
  successful_cells?: number;
  version?: RunVersion;
}

export interface RunDetail {
  id: string;
  timestamp: string;
  companies: string[];
  variables: string[];
  grid: Record<string, Record<string, CellData>>;
  metadata: RunMetadata;
  status: RunStatus;
  version?: RunVersion;
}

/** Structured white-space opportunity (Option B) */
export interface WhiteSpaceOpportunity {
  opportunity: string;
  why_it_exists: string;
  who_is_closest: string;
  entry_difficulty: string;
}

/** Structured next-step item */
export interface NextStepItem {
  action: string;
  rationale: string;
  priority: string;
}

/** Executive brief with full sections */
export interface ExecutiveBriefData {
  brief: string;
  key_themes?: string[];
  trends?: string[];
  white_space_opportunities?: WhiteSpaceOpportunity[];
  white_space_matrix?: {
    segment_gaps?: string[];
    product_gaps?: string[];
    business_model_gaps?: string[];
    geographic_gaps?: string[];
  };
  next_steps?: {
    investigate_further?: NextStepItem[];
    quick_wins?: NextStepItem[];
    strategic_bets?: NextStepItem[];
    monitor_and_defend?: NextStepItem[];
  };
  venture_context?: string;
}

/** V2 relational run: executive brief + parameter analyses */
export interface RunDetailV2 {
  id: string;
  timestamp: string;
  companies: string[];
  parameters: string[];
  parameter_definitions: Record<string, { id: string; name: string; category: string }>;
  executive: ExecutiveBriefData;
  analyses: Record<
    string,
    {
      parameter_id: string;
      parameter_name: string;
      headline: string;
      executive_summary: string;
      rankings: { rank: number; company: string; label: string; rationale: string }[];
      positioning_table: Record<string, unknown>[];
      full_report_markdown: string;
      white_space: string[];
      trends: string[];
      confidence: string;
      sources: Source[];
    }
  >;
  metadata: Record<string, unknown>;
  status: RunStatus;
  version: "v2";
  graveyard_companies?: GraveyardCompany[];
  graveyard_analyses?: Record<string, Record<string, unknown>>;
  postmortem_brief?: PostMortemBriefData;
}

export interface RunCreateRequest {
  companies: string[];
  variables: string[];
  dynamic_variables?: DynamicVariableDefinition[];
  parameter_contexts?: Record<string, string>;
  concurrency?: number;
  fast_mode?: boolean;
  version?: RunVersion;
  venture_context?: string;
}

export interface RunCreateResponse {
  run_id: string;
  status: RunStatus;
  message: string;
}

// =============================================================================
// Progress Types
// =============================================================================

export interface CurrentTask {
  company: string;
  variable: string;
  step?: string;
}

export interface ActivityItem {
  company: string;
  variable: string;
  confidence: string;
  timestamp: string;
  status: string;
}

export interface ProgressData {
  completed: number;
  total: number;
  current?: CurrentTask;
}

export interface RunProgress {
  run_id: string;
  status: RunStatus;
  progress: ProgressData;
  elapsed_seconds: number;
  estimated_remaining_seconds?: number;
  recent_activity: ActivityItem[];
}

// =============================================================================
// Research Plan Types
// =============================================================================

export interface CompanyProfile {
  id: string;
  input_name: string;
  official_name: string;
  industry: string;
  description: string;
  headquarters?: string;
  website?: string;
  ambiguity_notes?: string;
  subsidiary_notes?: string | null;
  subsidiaries?: string[];
  brand_name?: string | null;
}

export interface CompanySuggestion {
  id: string;
  name: string;
  category: string;
  rationale: string;
  gap_filled: string;
  subsidiaries?: string[];
  brand_name?: string | null;
}

export interface ClarificationOption {
  id: string;
  label: string;
  description?: string;
}

export interface ClarificationQuestion {
  id: string;
  question: string;
  options: ClarificationOption[];
  allow_free_text?: boolean;
  context?: string;
  impacts?: string[];
}

// =============================================================================
// Intelligence Question Types
// =============================================================================

export interface IntelligenceOption {
  id: string;
  label: string;
  description?: string;
}

export interface IntelligenceQuestion {
  id: string;
  question: string;
  options: IntelligenceOption[];
  allow_multiple?: boolean;
  allow_free_text?: boolean;
  context?: string;
  follow_up_hint?: string;
}

export interface IntelligenceAnswer {
  question_id: string;
  question_text: string;
  selected_option_ids: string[];
  selected_labels: string[];
  free_text?: string;
}

// =============================================================================
// Research Goal Types
// =============================================================================

export interface ResearchGoalResult {
  mission_statement: string;
  key_questions: string[];
  hypothesis?: string | null;
  perspective: string;
}

export interface CompanyConfidence {
  company_id: string;
  company_name: string;
  level: string;
  reason: string;
}

export interface ConfidencePreview {
  overall_level: string;
  company_confidences: CompanyConfidence[];
  warnings: string[];
  suggestions: string[];
}

export type ParameterPath = "competely" | "avis";

export interface ResearchPlan {
  id: string;
  title: string;
  status: "draft" | "accepted" | "launched" | "completed";
  created_at: string;
  updated_at: string;
  companies: CompanyProfile[];
  suggested_companies: CompanySuggestion[];
  accepted_suggestions: string[];
  industry_context: string;
  parameter_path: ParameterPath;
  selected_variable_ids: string[];
  dynamic_variables: DynamicVariableDefinition[];
  parameter_contexts: Record<string, string>;
  mission_statement: string;
  key_questions: string[];
  hypothesis?: string | null;
  perspective: string;
  audience: string;
  depth: "quick" | "standard" | "deep";
  focus_companies: string[];
  known_context?: string | null;
  graveyard_enabled?: boolean;
  graveyard_companies?: GraveyardCompany[];
  confidence_preview?: ConfidencePreview | null;
  clarification_log?: unknown[];
  run_id?: string | null;
}

export interface PlanListItem {
  id: string;
  title: string;
  status: string;
  created_at: string;
  updated_at: string;
  companies: string[];
  run_id?: string | null;
}

// =============================================================================
// Graveyard / Post-Mortem Intelligence Types
// =============================================================================

export interface GraveyardCompany {
  name: string;
  years_active: string;
  peak_description: string;
  reason_summary: string;
  confidence: string;
}

export interface CautionaryNarrative {
  company: string;
  peak_position: string;
  failure_mode: string;
  narrative: string;
  key_lesson: string;
}

export interface RiskOverlay {
  white_space_opportunity: string;
  historical_precedent: string;
  risk_level: string;
  mitigation_guidance: string;
}

export interface PostMortemBriefData {
  failure_patterns: string[];
  structural_vulnerabilities: string[];
  cautionary_narratives: CautionaryNarrative[];
  risk_overlays: RiskOverlay[];
  survival_principles: string[];
}
