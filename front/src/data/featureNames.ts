/**
 * Единый маппинг технических названий фичей → человекочитаемые названия.
 * Используется во всех местах фронтенда: SHAP-диаграмма, важность факторов и т.д.
 */
export const FEATURE_DISPLAY: Record<string, string> = {
  amount: "Причитающая сумма",
  log_amount: "Причитающая сумма",
  amount_to_normative: "Расчетное поголовье",
  amount_rank_in_subsidy_type: "Размер среди аналогичных субсидий",
  approval_rate_district: "Историческая одобряемость района",
  approval_rate_subsidy_type: "Историческая одобряемость субсидии",
  district: "Район",
  subsidy_type: "Вид субсидии",
  direction: "Направление",
  normative: "Норматив",
};

/** Преобразовать техническое имя фичи в человекочитаемое */
export function featureDisplayName(feature: string): string {
  return FEATURE_DISPLAY[feature] ?? feature;
}

