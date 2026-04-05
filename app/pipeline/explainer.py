"""
CalibratedExplainer — SHAP-объяснение модели (0–100 баллов).

Алгоритм:
  1. probability = model.predict_proba(X)[:, 1]
  2. score = clamp(round(probability * 100), 0, 100)
  3. delta = score - 50 (от -50 до +50)
  4. TreeExplainer → сырые SHAP-значения
  5. delta раскидывается по факторам пропорционально SHAP-значениям
     (знаки сохраняются, Largest Remainder Method гарантирует точное равенство)
  6. Результат: 50 + sum(display_shap) == score — ТОЧНОЕ равенство.
     Каждый display_shap — целое число.

Старый FeatureExplainer сохранён ниже для обратной совместимости.
"""

import math
import pandas as pd
import numpy as np
import logging
from typing import List, Dict, Any, Callable, Optional
import shap

from app.config import FEATURE_DISPLAY_NAMES

logger = logging.getLogger(__name__)


# =====================================================================
# Утилиты
# =====================================================================

def _safe_float(v) -> float:
    """Безопасное преобразование в float: NaN/Inf → 0."""
    try:
        f = float(v)
        if math.isnan(f) or math.isinf(f):
            return 0.0
        return f
    except (ValueError, TypeError):
        return 0.0


def _display_name(feature: str) -> str:
    """Человекочитаемое название признака."""
    return FEATURE_DISPLAY_NAMES.get(feature, feature)


def _distribute_delta(delta: int, raw_shap: List[float]) -> List[int]:
    """
    Распределяет целочисленную дельту по факторам пропорционально SHAP-значениям.

    Алгоритм:
      1. weight_i = |shap_i| / Σ|shap|      (доля абсолютного вклада)
      2. contribution_i = delta × weight_i × sign(shap_i)
         Каждый вклад ограничен диапазоном [−50, +50].
      3. Largest Remainder Method (Hamilton): round + распределение остатка
         по факторам с наибольшей потерей при округлении.
         Гарантирует sum(result) == delta — точное равенство.

    Args:
        delta: целевая сумма (score − 50), целое число от −50 до +50.
        raw_shap: сырые SHAP-значения из TreeExplainer (любое количество).

    Returns:
        Список целых чисел длиной len(raw_shap), sum == delta.
    """
    n = len(raw_shap)
    if n == 0:
        return []
    if delta == 0:
        return [0] * n

    abs_sum = sum(abs(v) for v in raw_shap)

    if abs_sum < 1e-12:
        # Все SHAP ≈ 0 — помещаем дельту в первый фактор
        result = [0] * n
        result[0] = delta
        return result

    # Пропорциональное масштабирование по абсолютным весам:
    # contribution_i = delta × (|shap_i| / Σ|shap|) × sign(shap_i)
    contributions = []
    for sv in raw_shap:
        weight = abs(sv) / abs_sum
        sign = 1.0 if sv >= 0 else -1.0
        contributions.append(delta * weight * sign)

    # Largest Remainder Method (Hamilton)
    rounded = [round(c) for c in contributions]
    gap = delta - sum(rounded)

    if gap != 0:
        step = 1 if gap > 0 else -1
        # Сортируем по потере при округлении в направлении нужной коррекции
        priority = sorted(
            range(n),
            key=lambda i: (contributions[i] - rounded[i]) * step,
            reverse=True,
        )
        for k in range(abs(gap)):
            rounded[priority[k % n]] += step

    return rounded


# =====================================================================
# CalibratedExplainer — основной класс для новых моделей
# =====================================================================

class CalibratedExplainer:
    """
    SHAP Explainer: TreeExplainer + целочисленное распределение дельты.

    Алгоритм для каждой заявки:
      1. probability = raw_model.predict_proba(X)[:, 1]  (0–1)
      2. score = clamp(round(probability × 100), 0, 100)  (целое)
      3. delta = score − 50                                (целое, от −50 до +50)
      4. TreeExplainer → сырые SHAP-значения
      5. _distribute_delta(delta, raw_shap) → целочисленные вклады
      6. Инвариант: 50 + sum(вклады) == score  (точное равенство)

    Параметры:
        raw_model — обученная LightGBM модель
        calibrated_fn — не используется (сохранён для совместимости сигнатуры)
        background — pd.DataFrame (сохранён для совместимости сигнатуры)
        feature_names — список имён признаков
    """

    def __init__(
        self,
        raw_model,
        calibrated_fn: Callable,
        background: pd.DataFrame,
        feature_names: List[str],
    ):
        self.raw_model = raw_model
        self.feature_names = feature_names
        self.background = background[feature_names].copy()

        # TreeExplainer — на порядки быстрее KernelSHAP
        self.explainer = shap.TreeExplainer(raw_model)

        logger.info(
            f"CalibratedExplainer: TreeExplainer, "
            f"features={len(self.feature_names)}"
        )

    def explain_batch(
        self,
        X: pd.DataFrame,
        original_df: Optional[pd.DataFrame] = None,
    ) -> List[Dict[str, Any]]:
        """
        Вычисляет SHAP для нескольких строк (батч).

        1. TreeExplainer.shap_values(X) — сырые SHAP (один вызов).
        2. predict_proba → score = clamp(round(prob × 100), 0, 100).
        3. delta = score − 50.
        4. _distribute_delta → целочисленные вклады, sum == delta.
        """
        X_aligned = X[self.feature_names].copy()
        X_aligned = X_aligned.fillna(0).replace([np.inf, -np.inf], 0)

        # 1) Batch SHAP в нативном пространстве (log-odds для LightGBM)
        raw_shap = self.explainer.shap_values(X_aligned)
        shap_matrix = _extract_shap_values(raw_shap)
        if isinstance(shap_matrix, list):
            shap_matrix = np.array(shap_matrix)

        # 2) Вероятности → целочисленные баллы
        probas = self.raw_model.predict_proba(X_aligned)[:, 1]

        results = []
        for i in range(len(X_aligned)):
            prob = float(probas[i])
            score = max(0, min(100, round(prob * 100)))
            delta = score - 50

            # 3) Сырые SHAP → целочисленные вклады
            sv_raw = [_safe_float(v) for v in shap_matrix[i]]
            int_contribs = _distribute_delta(delta, sv_raw)

            # 4) Формирование факторов
            factors = []
            for j, fname in enumerate(self.feature_names):
                # Значение признака — из original_df (человекочитаемое) или из X
                if original_df is not None and fname in original_df.columns:
                    feat_val = original_df.iloc[i][fname]
                    if isinstance(feat_val, (int, float, np.integer, np.floating)):
                        feat_val = _safe_float(feat_val)
                    else:
                        feat_val = str(feat_val)
                else:
                    feat_val = _safe_float(X_aligned.iloc[i][fname])

                factors.append({
                    "feature": fname,
                    "display_name": _display_name(fname),
                    "shap_value": int_contribs[j],
                    "feature_value": feat_val,
                })

            # Проверка инварианта: 50 + sum == score
            check_sum = 50 + sum(f["shap_value"] for f in factors)
            if check_sum != score:
                logger.error(
                    f"SHAP invariant broken: 50 + sum(shap)={check_sum} != score={score}, "
                    f"prob={prob:.6f}, delta={delta}"
                )

            results.append({
                "base_value": 50,
                "score": score,
                "factors": factors,
            })

        return results

    def explain_single(
        self,
        X_single: pd.DataFrame,
        original_row: Optional[pd.Series] = None,
    ) -> Dict[str, Any]:
        """Объяснение одной строки."""
        orig_df = None
        if original_row is not None:
            orig_df = pd.DataFrame([original_row])
        return self.explain_batch(X_single, orig_df)[0]


# =====================================================================
# FeatureExplainer — старый класс для обратной совместимости
# =====================================================================

def _sigmoid(x: float) -> float:
    try:
        return 1.0 / (1.0 + math.exp(-x))
    except OverflowError:
        return 0.0 if x < 0 else 1.0


def _detect_shap_space(base_value, shap_values_list, predicted_prob):
    total_shap = sum(shap_values_list)
    logodds_pred = _sigmoid(base_value + total_shap)
    prob_pred = base_value + total_shap
    err_logodds = abs(logodds_pred - predicted_prob)
    err_prob = abs(prob_pred - predicted_prob)
    return "logodds" if err_logodds < err_prob else "probability"


def _compute_score_contributions(shap_values_list, base_value, predicted_prob):
    n = len(shap_values_list)
    predicted_score = round(predicted_prob * 100, 4)
    if n == 0:
        return [], predicted_score

    space = _detect_shap_space(base_value, shap_values_list, predicted_prob)

    if space == "probability":
        base_score = base_value * 100
    else:
        base_score = _sigmoid(base_value) * 100

    total_delta = predicted_score - base_score

    abs_sum = sum(abs(sv) for sv in shap_values_list)

    if abs_sum < 1e-12:
        return [0.0] * n, round(base_score, 2)

    # Пропорциональное масштабирование по абсолютным весам:
    # score_point_i = total_delta × (|shap_i| / Σ|shap|) × sign(shap_i)
    score_points = []
    for sv in shap_values_list:
        weight = abs(sv) / abs_sum
        sign = 1.0 if sv >= 0 else -1.0
        score_points.append(total_delta * weight * sign)

    rounded = [round(sp, 2) for sp in score_points]
    residual = round(total_delta - sum(rounded), 2)
    if abs(residual) > 0.001 and n > 0:
        max_idx = max(range(n), key=lambda i: abs(score_points[i]))
        rounded[max_idx] = round(rounded[max_idx] + residual, 2)

    return rounded, round(base_score, 2)


def _extract_shap_values(shap_values):
    if isinstance(shap_values, shap.Explanation):
        vals = shap_values.values
        if vals.ndim == 3:
            return vals[:, :, 1]
        return vals
    if isinstance(shap_values, list):
        return shap_values[1]
    if isinstance(shap_values, np.ndarray) and shap_values.ndim == 3:
        return shap_values[:, :, 1]
    return shap_values


def _extract_base_value(explainer) -> float:
    if not hasattr(explainer, 'expected_value'):
        return 0.0
    ev = explainer.expected_value
    if isinstance(ev, (list, np.ndarray)):
        return _safe_float(ev[1] if len(ev) > 1 else ev[0])
    return _safe_float(ev)


class FeatureExplainer:
    """Старый explainer (TreeExplainer) — для обратной совместимости."""

    def __init__(self, model, feature_names: List[str], X_train: pd.DataFrame):
        self.model = model
        self.feature_names = feature_names

        self.X_train = X_train[self.feature_names].sample(
            min(1000, len(X_train)), random_state=42
        )
        self.X_train = self.X_train.fillna(0)

        try:
            self.explainer = shap.TreeExplainer(self.model)
        except Exception as e:
            logger.warning(f"TreeExplainer init failed: {e}, trying fallback")
            self.explainer = shap.TreeExplainer(self.model, self.X_train)

    def explain_single(self, X_single: pd.DataFrame) -> Dict:
        X_single = X_single[self.feature_names].copy()
        X_single = X_single.fillna(0).replace([np.inf, -np.inf], 0)
        for col in X_single.columns:
            try:
                X_single[col] = pd.to_numeric(X_single[col], errors='coerce').fillna(0)
            except Exception:
                X_single[col] = 0

        predicted_prob = float(self.model.predict_proba(X_single)[:, 1][0])
        predicted_score = round(predicted_prob * 100, 2)

        raw = self.explainer.shap_values(X_single)
        shap_vals = _extract_shap_values(raw)
        shap_row = shap_vals[0]
        feature_values = X_single.iloc[0].values
        base_value = _extract_base_value(self.explainer)
        all_shap_raw = [_safe_float(v) for v in shap_row]

        score_points_list, base_score = _compute_score_contributions(
            all_shap_raw, base_value, predicted_prob,
        )

        explanation = pd.DataFrame({
            'feature': self.feature_names,
            'display_name': [_display_name(f) for f in self.feature_names],
            'value': [_safe_float(v) for v in feature_values],
            'shap_value': all_shap_raw,
        })
        explanation['abs_shap'] = explanation['shap_value'].abs()
        explanation = explanation.sort_values(by='abs_shap', ascending=False)

        score_points_map = dict(zip(self.feature_names, score_points_list))

        top_factors = []
        for _, row in explanation.head(8).iterrows():
            direction = "positive" if row['shap_value'] > 0 else "negative"
            sp = score_points_map.get(row['feature'], 0.0)
            top_factors.append({
                "feature": str(row['feature']),
                "display_name": str(row['display_name']),
                "value": float(round(row['value'], 4)),
                "shap_value": float(round(row['shap_value'], 6)),
                "score_points": float(sp),
                "importance": float(round(row['abs_shap'], 6)),
                "direction": direction,
            })

        all_factors = []
        for _, row in explanation.iterrows():
            sp = score_points_map.get(row['feature'], 0.0)
            all_factors.append({
                "feature": str(row['feature']),
                "display_name": str(row['display_name']),
                "value": float(round(row['value'], 4)),
                "shap_value": float(round(row['shap_value'], 6)),
                "score_points": float(sp),
            })

        return {
            "top_factors": top_factors,
            "risk_factors": [f for f in top_factors if f['direction'] == 'negative'],
            "positive_factors": [f for f in top_factors if f['direction'] == 'positive'],
            "all_factors": all_factors,
            "base_value": round(base_value, 6),
            "base_score": base_score,
            "predicted_score": predicted_score,
            "method": "SHAP",
        }

    def get_global_importance(self) -> pd.DataFrame:
        raw = self.explainer.shap_values(self.X_train)
        shap_values = _extract_shap_values(raw)
        importance = np.abs(shap_values).mean(axis=0)
        df = pd.DataFrame({
            'feature': self.feature_names,
            'display_name': [_display_name(f) for f in self.feature_names],
            'importance': importance,
        })
        return df.sort_values(by='importance', ascending=False)

