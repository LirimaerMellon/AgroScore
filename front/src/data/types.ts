/**
 * Типы данных фронтенда AgriScore.
 * Выровнены с ответами API.
 */

/* SHAP-фактор (из API shap_explanation.top_factors / all_factors) */
export interface ShapFactor {
  feature: string;
  display_name?: string;
  value: number;
  importance?: number;
  shap_value?: number;
  direction?: string;
}

/* Заявка из API GET /api/applications */
export interface ApplicationRow {
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
  status?: string;
  shap_explanation?: {
    top_factors: ShapFactor[];
    risk_factors?: ShapFactor[];
    positive_factors?: ShapFactor[];
    all_factors: { feature: string; display_name?: string; value: number; shap_value: number }[];
    base_value?: number;
    method: string;
  };
}
