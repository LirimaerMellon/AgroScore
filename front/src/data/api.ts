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
  total_amount: number;
  mean_amount: number;
  confidence_high?: number;
  confidence_medium?: number;
  confidence_low?: number;
}
export const fetchSummary = (modelVersion?: string) => {
  const q = modelVersion ? `?model_version=${encodeURIComponent(modelVersion)}` : "";
  return request<AnalyticsSummary>(`/api/analytics/summary${q}`);
};

export interface DistributionBin { range: string; count: number; }
export const fetchDistribution = (bins = 10, modelVersion?: string) => {
  const q = new URLSearchParams();
  q.set("bins", String(bins));
  if (modelVersion) q.set("model_version", modelVersion);
  return request<{ bins: DistributionBin[] }>(`/api/analytics/distribution?${q.toString()}`);
};

export interface FeatureImportanceItem { feature: string; importance: number; }
export interface FeatureImportanceResponse { model_version: string; features: FeatureImportanceItem[]; }
export const fetchFeatureImportance = (modelVersion?: string) => {
  const q = modelVersion ? `?model_version=${encodeURIComponent(modelVersion)}` : "";
  return request<FeatureImportanceResponse>(`/api/analytics/features${q}`);
};

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
  confidence_level?: string;
  unknown_fields?: string[];
  review_required?: boolean;
  data_warnings?: any[];
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
  min_amount?: number;
  max_amount?: number;
  total_amount?: number;
  high_count?: number;
  medium_count?: number;
  low_count?: number;
}

export interface SimilarApp {
  id: number;
  score: number;
  category: string;
  region: string;
  direction: string;
  subsidy_type: string;
  amount: number;
  bin_iin?: string;
}


export interface AmountRangeStats {
  cnt: number;
  mean_score: number;
  min_score: number;
  max_score: number;
  mean_amount: number;
  range_from: number;
  range_to: number;
}

export interface ApplicationAnalysis {
  app_id: number;
  score: number;
  category: string;
  narrative: string;
  peers: {
    application_score: number;
    application_category: string;
    application_amount?: number;
    percentile: number;
    total_applications: number;
    amount_rank_region?: number;
    subsidy_stats: PeerStats | null;
    district_stats: PeerStats | null;
    global_stats: PeerStats | null;
    amount_range_stats: AmountRangeStats | null;
    similar_apps: SimilarApp[];
  };
}

export function fetchApplicationAnalysis(id: number) {
  return request<ApplicationAnalysis>(`/api/applications/${id}/analysis`);
}

// ─── SHAP Explanation ─────────────────────────────────
export interface ShapFactorItem {
  feature: string;
  shap_points: number;
  direction: string;
}

export interface ShapRestItem {
  count: number;
  shap_points: number;
  factors?: ShapFactorItem[];
}

export interface ShapResponse {
  score: number;
  base_value: number;
  category: string;
  model_version: string;
  fits_budget: boolean | null;
  summary: string;
  factors: ShapFactorItem[];
  rest: ShapRestItem;
}

export function fetchShapExplanation(id: number, detailed = false) {
  return request<ShapResponse>(`/api/applications/${id}/shap?detailed=${detailed}`);
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
export function trainFromFile(file: File) {
  const fd = new FormData();
  fd.append("file", file);
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

export function fetchErrors(params: {
  trace_id?: string;
  error_code?: string;
  error_col?: string;
  source_name?: string;
  sort_by?: string;
  sort_dir?: string;
  limit?: number;
  offset?: number;
} = {}) {
  const q = new URLSearchParams();
  if (params.trace_id) q.set("trace_id", params.trace_id);
  if (params.error_code) q.set("error_code", params.error_code);
  if (params.error_col) q.set("error_col", params.error_col);
  if (params.source_name) q.set("source_name", params.source_name);
  if (params.sort_by) q.set("sort_by", params.sort_by);
  if (params.sort_dir) q.set("sort_dir", params.sort_dir);
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
export const fetchByMonth = (year?: number, modelVersion?: string) => {
  const q = new URLSearchParams();
  if (year) q.set("year", String(year));
  if (modelVersion) q.set("model_version", modelVersion);
  const qs = q.toString();
  return request<{ months: MonthStat[] }>(`/api/analytics/by-month${qs ? `?${qs}` : ""}`);
};

// ─── Analytics: Avg Score by Region ───────────────────
export interface RegionScoreStat {
  region: string;
  count: number;
  avg_score: number;
  min_score: number;
  max_score: number;
  total_amount: number;
}
export const fetchAvgScoreByRegion = (year?: number, modelVersion?: string) => {
  const q = new URLSearchParams();
  if (year) q.set("year", String(year));
  if (modelVersion) q.set("model_version", modelVersion);
  const qs = q.toString();
  return request<{ regions: RegionScoreStat[] }>(`/api/analytics/avg-score-by-region${qs ? `?${qs}` : ""}`);
};

// ─── Analytics: Avg Score by Direction ────────────────
export interface DirectionScoreStat {
  direction: string;
  count: number;
  avg_score: number;
  min_score: number;
  max_score: number;
  total_amount: number;
}
export const fetchAvgScoreByDirection = (year?: number, modelVersion?: string) => {
  const q = new URLSearchParams();
  if (year) q.set("year", String(year));
  if (modelVersion) q.set("model_version", modelVersion);
  const qs = q.toString();
  return request<{ directions: DirectionScoreStat[] }>(`/api/analytics/avg-score-by-direction${qs ? `?${qs}` : ""}`);
};
// ─── Analytics: Available Years ───────────────────────
export const fetchAvailableYears = () =>
  request<{ years: number[] }>("/api/analytics/available-years");

// ─── Shortlist ────────────────────────────────────────
export interface ShortlistItem extends ApplicationItem {
  rank: number;
  cumulative_sum: number;
  fits_budget: boolean;
}

export interface ShortlistResponse {
  budget: number;
  total_candidates: number;
  total_in_db: number;
  selected_count: number;
  total_cost: number;
  remaining_budget: number;
  review_required_count: number;
  selected: ShortlistItem[];
  excluded_count: number;
}

export function fetchShortlist(
  budget?: number, category?: string, region?: string,
  min_score?: number, strategy?: string,
  direction?: string, subsidy_type?: string,
  district?: string, model_version?: string,
  signal?: AbortSignal,
) {
  const q = new URLSearchParams();
  if (budget !== undefined && budget !== null) q.set("budget", String(budget));
  if (category) q.set("category", category);
  if (region) q.set("region", region);
  if (direction) q.set("direction", direction);
  if (subsidy_type) q.set("subsidy_type", subsidy_type);
  if (district) q.set("district", district);
  if (model_version) q.set("model_version", model_version);
  if (min_score !== undefined && min_score !== null) q.set("min_score", String(min_score));
  if (strategy) q.set("strategy", strategy);
  return request<ShortlistResponse>(`/api/shortlist?${q.toString()}`, signal ? { signal } : undefined);
}

// ─── Thresholds ───────────────────────────────────────
export interface ThresholdItem {
  category: string;
  min_score: number;
  max_score: number;
}

export interface ThresholdsResponse {
  model_version: string;
  thresholds: ThresholdItem[];
}

export function fetchThresholds(modelVersion?: string) {
  const q = modelVersion ? `?model_version=${encodeURIComponent(modelVersion)}` : "";
  return request<ThresholdsResponse>(`/api/thresholds${q}`);
}

export function updateThresholds(thresholds: ThresholdItem[], updatedBy = "admin", modelVersion = "_default") {
  return request<{ status: string; thresholds: ThresholdItem[] }>("/api/thresholds", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ thresholds, model_version: modelVersion, updated_by: updatedBy }),
  });
}

export function resetThresholds(modelVersion = "_default") {
  return request<{ status: string; thresholds: ThresholdItem[] }>(
    `/api/thresholds/reset?model_version=${encodeURIComponent(modelVersion)}`,
    { method: "POST" },
  );
}

export function previewThresholds(thresholds: ThresholdItem[]) {
  return request<{ counts: Record<string, number> }>("/api/thresholds/preview", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ thresholds }),
  });
}

// ─── Round Budget ─────────────────────────────────────
export interface RoundBudgetResponse {
  budget: number;
  updated_by: string | null;
  updated_at: string | null;
}

export function fetchRoundBudget() {
  return request<RoundBudgetResponse>("/api/round-budget");
}

export function updateRoundBudget(budget: number, updatedBy = "admin") {
  return request<{ status: string; budget: number }>("/api/round-budget", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ budget, updated_by: updatedBy }),
  });
}

