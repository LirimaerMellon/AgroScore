import pandas as pd
import numpy as np
import logging
from typing import List, Dict
import shap

logger = logging.getLogger(__name__)


class FeatureExplainer:

    def __init__(self, model, feature_names: List[str], X_train: pd.DataFrame):
        self.model = model
        self.feature_names = feature_names

        self.X_train = X_train[self.feature_names].sample(
            min(1000, len(X_train)), random_state=42
        )

        self.explainer = shap.TreeExplainer(self.model)

    def explain_single(self, X_single: pd.DataFrame) -> Dict:
        X_single = X_single[self.feature_names]

        shap_values = self.explainer.shap_values(X_single)

        if isinstance(shap_values, list):
            shap_values = shap_values[1]

        shap_row = shap_values[0]
        values = X_single.iloc[0].values

        explanation = pd.DataFrame({
            'feature': self.feature_names,
            'value': values,
            'shap_value': shap_row
        })

        explanation['abs_shap'] = explanation['shap_value'].abs()
        explanation = explanation.sort_values(by='abs_shap', ascending=False)

        top_factors = []
        for _, row in explanation.head(5).iterrows():
            direction = "positive" if row['shap_value'] > 0 else "negative"

            top_factors.append({
                "feature": row['feature'],
                "value": float(row['value']),
                "importance": float(row['abs_shap']),
                "direction": direction
            })

        return {
            "top_factors": top_factors,
            "all_factors": explanation.drop(columns=['abs_shap']).to_dict('records'),
            "method": "SHAP"
        }

    def get_global_importance(self) -> pd.DataFrame:
        shap_values = self.explainer.shap_values(self.X_train)

        if isinstance(shap_values, list):
            shap_values = shap_values[1]

        importance = np.abs(shap_values).mean(axis=0)

        df = pd.DataFrame({
            'feature': self.feature_names,
            'importance': importance
        })

        return df.sort_values(by='importance', ascending=False)