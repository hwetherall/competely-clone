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
      // Invalidate runs list to refresh
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
