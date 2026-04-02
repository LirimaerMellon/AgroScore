/**
 * API-клиент для взаимодействия с FastAPI бэкендом AgriScore.
 */

const BASE = "";  // проксируется через vite

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${url}`, init);
  if (!res.ok) {
    const body = await res.text();
    let message = res.statusText;
    try {
      const parsed = JSON.parse(body);
      message = parsed.detail || parsed.message || body;
    } catch {
      if (body) message = body;
    }
    throw new Error(message);
  }
  return res.json();
}

// ─── Health ───────────────────────────────────────────
export interface HealthResponse {
  status: string;
  timestamp: string;
  model_loaded: boolean;
  active_model: string | null;
}
export const fetchHealth = () => request<HealthResponse>("/health");

// ─── Analytics ────────────────────────────────────────
export interface AnalyticsSummary {
  total: number;
  mean_score: number | null;
  min_score: number | null;
  max_score: number | null;
  high: number;
  medium: number;
  low: number;
}
export const fetchSummary = () => request<AnalyticsSummary>("/api/analytics/summary");

export interface DistributionBin { range: string; count: number; }
export const fetchDistribution = (bins = 10) =>
  request<{ bins: DistributionBin[] }>(`/api/analytics/distribution?bins=${bins}`);

export interface FeatureImportanceItem { feature: string; importance: number; }
export interface FeatureImportanceResponse { model_version: string; features: FeatureImportanceItem[]; }
export const fetchFeatureImportance = () => request<FeatureImportanceResponse>("/api/analytics/features");

export interface FairnessGroup {
  group_value: string;
  cnt: number;
  mean_score: number;
  min_score: number;
  max_score: number;
}
export const fetchFairness = () => request<Record<string, any>>("/api/analytics/fairness");

// ─── Applications ─────────────────────────────────────
export interface ApplicationItem {
  id: number;
  model_version: string;
  created_at: string;
  bin_iin: string;
  region: string;
  akimat: string;
  direction: string;
  subsidy_type: string;
  normative: number;
  amount: number;
  district: string;
  score: number;
  category: string;
  probability: number;
  shap_explanation?: any;
  status?: string;
}

export interface ApplicationsResponse {
  total: number;
  items: ApplicationItem[];
}

export interface ApplicationsParams {
  limit?: number;
  offset?: number;
  region?: string;
  category?: string;
  model_version?: string;
  min_score?: number;
  max_score?: number;
  sort_by?: string;
  sort_dir?: string;
  review_required?: boolean;
  search?: string;
}

export function fetchApplications(params: ApplicationsParams = {}) {
  const q = new URLSearchParams();
  if (params.limit) q.set("limit", String(params.limit));
  if (params.offset !== undefined) q.set("offset", String(params.offset));
  if (params.region) q.set("region", params.region);
  if (params.category) q.set("category", params.category);
  if (params.model_version) q.set("model_version", params.model_version);
  if (params.min_score !== undefined && params.min_score !== null) q.set("min_score", String(params.min_score));
  if (params.max_score !== undefined && params.max_score !== null) q.set("max_score", String(params.max_score));
  if (params.sort_by) q.set("sort_by", params.sort_by);
  if (params.sort_dir) q.set("sort_dir", params.sort_dir);
  if (params.review_required) q.set("review_required", "true");
  if (params.search) q.set("search", params.search);
  return request<ApplicationsResponse>(`/api/applications?${q.toString()}`);
}

export function fetchApplication(id: number) {
  return request<{ application: ApplicationItem }>(`/api/applications/${id}`);
}

// ─── Application Analysis ─────────────────────────────
export interface PeerStats {
  cnt: number;
  mean_score: number;
  min_score: number;
  max_score: number;
  mean_amount: number;
}

export interface SimilarApp {
  id: number;
  score: number;
  category: string;
  region: string;
  direction: string;
  subsidy_type: string;
  amount: number;
}

export interface RiskItem {
  feature: string;
  display_name: string;
  impact: number;
  severity: "high" | "medium" | "low";
  description?: string;
}

export interface ApplicationAnalysis {
  app_id: number;
  score: number;
  category: string;
  score_interpretation: string;
  risks: RiskItem[];
  peers: {
    application_score: number;
    application_category: string;
    percentile: number;
    total_applications: number;
    region_stats: PeerStats | null;
    direction_stats: PeerStats | null;
    subsidy_stats: PeerStats | null;
    similar_apps: SimilarApp[];
  };
}

export function fetchApplicationAnalysis(id: number) {
  return request<ApplicationAnalysis>(`/api/applications/${id}/analysis`);
}

// ─── Models ───────────────────────────────────────────
export interface ModelInfo {
  id: number;
  version: string;
  created_at: string;
  file_path: string;
  metrics: Record<string, any>;
  train_size: number;
  n_features: number;
  positive_rate: number;
  is_active: number;
}
export interface ModelsResponse { total: number; models: ModelInfo[]; }
export const fetchModels = () => request<ModelsResponse>("/api/models");

export function activateModel(version: string) {
  return request<{ status: string; active_version: string }>(
    `/api/models/activate?version=${encodeURIComponent(version)}`,
    { method: "POST" },
  );
}

// ─── Training ─────────────────────────────────────────
export function trainFromFile(file: File, modelVersion?: string) {
  const fd = new FormData();
  fd.append("file", file);
  if (modelVersion) fd.append("model_version", modelVersion);
  return request<any>("/api/train", { method: "POST", body: fd });
}

// ─── Scoring ──────────────────────────────────────────
export function scoreFromFile(file: File, modelVersion?: string) {
  const fd = new FormData();
  fd.append("file", file);
  if (modelVersion) fd.append("model_version", modelVersion);
  return request<any>("/api/score", { method: "POST", body: fd });
}

// ─── Template ─────────────────────────────────────────
export function downloadTemplate() {
  window.open(`${BASE}/api/template`, "_blank");
}

// ─── Export ───────────────────────────────────────────
export function downloadExport(modelVersion?: string, category?: string) {
  const q = new URLSearchParams();
  if (modelVersion) q.set("model_version", modelVersion);
  if (category) q.set("category", category);
  window.open(`${BASE}/api/export?${q.toString()}`, "_blank");
}

// ─── Errors ───────────────────────────────────────────
export interface ErrorLogItem {
  id: number;
  trace_id: string;
  detected_at: string;
  source_type: string;
  source_name: string;
  error_codes: string[];
  error_cols: string[];
  locator: Record<string, any>;
  raw_payload: Record<string, any> | null;
  violations: any[];
}
export interface ErrorsResponse { total: number; items: ErrorLogItem[]; }

export function fetchErrors(params: { trace_id?: string; limit?: number; offset?: number } = {}) {
  const q = new URLSearchParams();
  if (params.trace_id) q.set("trace_id", params.trace_id);
  if (params.limit) q.set("limit", String(params.limit));
  if (params.offset !== undefined) q.set("offset", String(params.offset));
  return request<ErrorsResponse>(`/api/errors?${q.toString()}`);
}

export interface ErrorSummary {
  total_errors: number;
  by_error_code: Record<string, number>;
  by_column: Record<string, number>;
}
export function fetchErrorSummary(trace_id?: string) {
  const q = trace_id ? `?trace_id=${encodeURIComponent(trace_id)}` : "";
  return request<ErrorSummary>(`/api/errors/summary${q}`);
}

export interface TraceItem {
  trace_id: string;
  source_name: string;
  source_type: string;
  first_detected: string;
  error_count: number;
}
export function fetchTraces(limit = 50) {
  return request<{ traces: TraceItem[] }>(`/api/errors/traces?limit=${limit}`);
}

// ─── Analytics: By Month ──────────────────────────────
export interface MonthStat { month: string; count: number; avg_score: number; }
export const fetchByMonth = (year?: number) =>
  request<{ months: MonthStat[] }>(`/api/analytics/by-month${year ? `?year=${year}` : ""}`);

// ─── Analytics: Avg Score by Region ───────────────────
export interface RegionScoreStat {
  region: string;
  count: number;
  avg_score: number;
  min_score: number;
  max_score: number;
  total_amount: number;
}
export const fetchAvgScoreByRegion = (year?: number) =>
  request<{ regions: RegionScoreStat[] }>(`/api/analytics/avg-score-by-region${year ? `?year=${year}` : ""}`);

// ─── Analytics: Avg Score by Direction ────────────────
export interface DirectionScoreStat {
  direction: string;
  count: number;
  avg_score: number;
  min_score: number;
  max_score: number;
  total_amount: number;
}
export const fetchAvgScoreByDirection = (year?: number) =>
  request<{ directions: DirectionScoreStat[] }>(`/api/analytics/avg-score-by-direction${year ? `?year=${year}` : ""}`);

// ─── Analytics: Available Years ───────────────────────
export const fetchAvailableYears = () =>
  request<{ years: number[] }>("/api/analytics/available-years");

// ─── Shortlist ────────────────────────────────────────
export interface ShortlistResponse {
  budget: number;
  total_candidates: number;
  total_in_db: number;
  selected_count: number;
  total_cost: number;
  remaining_budget: number;
  review_required_count: number;
  selected: ApplicationItem[];
  excluded_count: number;
}

export function fetchShortlist(
  budget?: number, category?: string, region?: string,
  min_score?: number, strategy?: string,
  direction?: string, subsidy_type?: string,
) {
  const q = new URLSearchParams();
  if (budget !== undefined && budget !== null) q.set("budget", String(budget));
  if (category) q.set("category", category);
  if (region) q.set("region", region);
  if (direction) q.set("direction", direction);
  if (subsidy_type) q.set("subsidy_type", subsidy_type);
  if (min_score !== undefined && min_score !== null) q.set("min_score", String(min_score));
  if (strategy) q.set("strategy", strategy);
  return request<ShortlistResponse>(`/api/shortlist?${q.toString()}`);
}

