import math
import pandas as pd
import numpy as np
import logging
from typing import List, Dict
import shap

from app.config import FEATURE_DISPLAY_NAMES

logger = logging.getLogger(__name__)


def _safe_float(v) -> float:
    """Безопасное преобразование в float: NaN/Inf → 0."""
    try:
        f = float(v)
        if math.isnan(f) or math.isinf(f):
            return 0.0
        return f
    except (ValueError, TypeError):
        return 0.0


def _extract_shap_values(shap_values):
    """Extract SHAP values from different formats (list, Explanation, ndarray)."""
    # shap >= 0.44 may return Explanation object
    if isinstance(shap_values, shap.Explanation):
        vals = shap_values.values
        if vals.ndim == 3:
            return vals[:, :, 1]
        return vals

    # Older versions: list of two arrays [class_0, class_1]
    if isinstance(shap_values, list):
        return shap_values[1]

    # ndarray with 3 axes (samples x features x classes)
    if isinstance(shap_values, np.ndarray) and shap_values.ndim == 3:
        return shap_values[:, :, 1]

    return shap_values


def _display_name(feature: str) -> str:
    """Человекочитаемое название признака."""
    return FEATURE_DISPLAY_NAMES.get(feature, feature)


class FeatureExplainer:

    def __init__(self, model, feature_names: List[str], X_train: pd.DataFrame):
        self.model = model
        self.feature_names = feature_names

        self.X_train = X_train[self.feature_names].sample(
            min(1000, len(X_train)), random_state=42
        )
        # Заполняем NaN в фоновых данных — TreeExplainer может не работать с NaN
        self.X_train = self.X_train.fillna(0)

        try:
            self.explainer = shap.TreeExplainer(self.model)
        except Exception as e:
            logger.warning(f"TreeExplainer init failed: {e}, trying fallback")
            self.explainer = shap.TreeExplainer(self.model, self.X_train)


    def explain_single(self, X_single: pd.DataFrame) -> Dict:
        X_single = X_single[self.feature_names].copy()

        # Заменяем NaN и Inf в данных перед SHAP-объяснением
        X_single = X_single.fillna(0)
        X_single = X_single.replace([np.inf, -np.inf], 0)

        # Приводим к float для предотвращения ошибок типов
        for col in X_single.columns:
            try:
                X_single[col] = pd.to_numeric(X_single[col], errors='coerce').fillna(0)
            except Exception:
                X_single[col] = 0

        raw = self.explainer.shap_values(X_single)
        shap_values = _extract_shap_values(raw)

        shap_row = shap_values[0]
        values = X_single.iloc[0].values

        # Получаем базовое значение (expected value)
        base_value = 0.0
        if hasattr(self.explainer, 'expected_value'):
            ev = self.explainer.expected_value
            if isinstance(ev, (list, np.ndarray)):
                base_value = _safe_float(ev[1] if len(ev) > 1 else ev[0])
            else:
                base_value = _safe_float(ev)

        explanation = pd.DataFrame({
            'feature': self.feature_names,
            'display_name': [_display_name(f) for f in self.feature_names],
            'value': [_safe_float(v) for v in values],
            'shap_value': [_safe_float(v) for v in shap_row],
        })

        explanation['abs_shap'] = explanation['shap_value'].abs()
        explanation = explanation.sort_values(by='abs_shap', ascending=False)

        top_factors = []
        for _, row in explanation.head(8).iterrows():
            direction = "positive" if row['shap_value'] > 0 else "negative"

            top_factors.append({
                "feature": str(row['feature']),
                "display_name": str(row['display_name']),
                "value": float(round(row['value'], 4)),
                "shap_value": float(round(row['shap_value'], 6)),
                "importance": float(round(row['abs_shap'], 6)),
                "direction": direction,
            })

        # Отдельно: факторы риска (снижающие вероятность) и позитивные
        risk_factors = [f for f in top_factors if f['direction'] == 'negative']
        positive_factors = [f for f in top_factors if f['direction'] == 'positive']

        all_factors = []
        for _, row in explanation.iterrows():
            all_factors.append({
                "feature": str(row['feature']),
                "display_name": str(row['display_name']),
                "value": float(round(row['value'], 4)),
                "shap_value": float(round(row['shap_value'], 6)),
            })

        return {
            "top_factors": top_factors,
            "risk_factors": risk_factors,
            "positive_factors": positive_factors,
            "all_factors": all_factors,
            "base_value": round(base_value, 6),
            "method": "SHAP",
        }

    def get_global_importance(self) -> pd.DataFrame:
        raw = self.explainer.shap_values(self.X_train)
        shap_values = _extract_shap_values(raw)

        importance = np.abs(shap_values).mean(axis=0)

        df = pd.DataFrame({
            'feature': self.feature_names,
            'display_name': [_display_name(f) for f in self.feature_names],
            'importance': importance
        })

        return df.sort_values(by='importance', ascending=False)