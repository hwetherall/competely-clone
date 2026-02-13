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
