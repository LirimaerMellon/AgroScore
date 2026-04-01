"""
ScoringModel — обучение, оценка и сериализация модели скоринга.

Ключевые улучшения:
- StratifiedKFold кросс-валидация для надёжных метрик
- Нативная поддержка категориальных фичей LightGBM
- Расширенные метрики (AUC, F1, Precision, Recall, Accuracy, LogLoss, Gini)
- Fairness-анализ — распределение скоров по регионам / типам субсидий
"""

import pandas as pd
import numpy as np
from sklearn.preprocessing import LabelEncoder
from lightgbm import LGBMClassifier
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import (
    roc_auc_score,
    precision_recall_fscore_support,
    accuracy_score,
    log_loss,
    average_precision_score,
    confusion_matrix,
)
import pickle
import logging
from typing import Dict, List, Any

from app.config import MODEL_PARAMS

logger = logging.getLogger(__name__)


class ScoringModel:

    def __init__(self):
        self.model = LGBMClassifier(**MODEL_PARAMS)
        self.label_encoders: Dict[str, LabelEncoder] = {}
        self.feature_names: List[str] = []
        self.feature_types: Dict[str, str] = {}
        self._categorical_features: List[str] = []

    # ==================================================================
    # FEATURE PREPARATION
    # ==================================================================

    def prepare_features(self, df: pd.DataFrame, fit: bool = False) -> pd.DataFrame:
        """
        Подготовка признаков: label-encoding категорий,
        определение типов для LightGBM.
        """
        df = df.copy()

        exclude_cols = {
            'application_id', 'request_number', 'row_number',
            'is_approved', 'status', 'submission_date',
            'index', 'date',
        }

        feature_cols = [c for c in df.columns if c not in exclude_cols]

        categorical = df[feature_cols].select_dtypes(include=['object']).columns.tolist()
        numeric = df[feature_cols].select_dtypes(include=[np.number]).columns.tolist()

        for col in categorical:
            if fit:
                le = LabelEncoder()
                df[col] = le.fit_transform(df[col].astype(str))
                self.label_encoders[col] = le
            else:
                if col in self.label_encoders:
                    le = self.label_encoders[col]
                    df[col] = df[col].astype(str).map(
                        lambda x, _le=le: (
                            _le.transform([x])[0] if x in _le.classes_ else -1
                        )
                    )
                else:
                    df[col] = -1

            self.feature_types[col] = 'categorical'

        for col in numeric:
            self.feature_types[col] = 'numeric'

        feature_names = numeric + categorical

        if fit:
            self.feature_names = feature_names
            self._categorical_features = categorical

        return df[self.feature_names]

    # ==================================================================
    # TRAINING
    # ==================================================================

    def train(self, df: pd.DataFrame, n_splits: int = 5) -> Dict[str, Any]:
        """
        Обучение модели:
        1. Кросс-валидация (StratifiedKFold) → метрики
        2. Финальное обучение на ВСЕХ данных → production-модель
        """
        logger.info("=" * 50)
        logger.info("ОБУЧЕНИЕ МОДЕЛИ")
        logger.info("=" * 50)

        df_train = df[df['is_approved'] != -1].copy()

        X = self.prepare_features(df_train, fit=True)
        y = df_train['is_approved'].astype(int)

        logger.info(f"Размер выборки: {len(X)}")
        logger.info(f"Признаков: {len(self.feature_names)}")
        logger.info(f"  числовых:       {sum(1 for v in self.feature_types.values() if v == 'numeric')}")
        logger.info(f"  категориальных: {sum(1 for v in self.feature_types.values() if v == 'categorical')}")
        logger.info(f"Баланс классов: approved={int(y.sum())} / rejected={int((1 - y).sum())} "
                     f"({y.mean():.1%} positive)")

        # --- Cross-validation ---
        cv_metrics = self._cross_validate(X, y, n_splits)

        # --- Final model on all data ---
        logger.info("Обучение финальной модели на всех данных...")
        self.model.fit(
            X, y,
            categorical_feature=self._categorical_features,
        )

        # --- Aggregate metrics ---
        agg = self._aggregate_cv_metrics(cv_metrics)

        logger.info("-" * 50)
        logger.info(f"✓ AUC:       {agg['auc_mean']:.3f} ± {agg['auc_std']:.3f}")
        logger.info(f"✓ F1:        {agg['f1_mean']:.3f} ± {agg['f1_std']:.3f}")
        logger.info(f"✓ Precision: {agg['precision_mean']:.3f}")
        logger.info(f"✓ Recall:    {agg['recall_mean']:.3f}")
        logger.info(f"✓ Accuracy:  {agg['accuracy_mean']:.3f}")
        logger.info(f"✓ Gini:      {agg['gini_mean']:.3f}")
        logger.info("-" * 50)

        return {
            **agg,
            'train_size': len(X),
            'n_features': len(self.feature_names),
            'positive_rate': round(float(y.mean()), 4),
        }

    # ==================================================================
    # SCORING
    # ==================================================================

    def score(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Скоринг: probability → score (0–100) → category (LOW/MEDIUM/HIGH).
        """
        df = df.copy()
        X = self.prepare_features(df, fit=False)

        probabilities = self.model.predict_proba(X)[:, 1]
        scores = np.round(probabilities * 100, 2)

        df['score'] = scores
        df['probability'] = probabilities

        df['category'] = pd.cut(
            scores,
            bins=[0, 40, 70, 100],
            labels=['LOW', 'MEDIUM', 'HIGH'],
            include_lowest=True,
        )

        return df

    # ==================================================================
    # FAIRNESS
    # ==================================================================

    def compute_fairness_report(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Анализ справедливости: распределение скоров по группам.

        Возвращает средний скор, std и count для каждой группы
        по region, subsidy_type, direction.
        """
        if 'score' not in df.columns:
            logger.warning("Колонка 'score' отсутствует, fairness-отчёт невозможен")
            return {}

        report: Dict[str, Any] = {}

        for col in ['region', 'subsidy_type', 'direction']:
            if col not in df.columns:
                continue

            stats = (
                df.groupby(col)['score']
                .agg(['mean', 'std', 'min', 'max', 'count'])
                .round(2)
                .sort_values('mean', ascending=False)
            )
            report[col] = stats.to_dict('index')

            # Disparate impact: max_mean / min_mean
            if len(stats) > 1 and stats['mean'].min() > 0:
                di = round(stats['mean'].max() / stats['mean'].min(), 3)
                report[f'{col}_disparate_impact'] = di

        logger.info("Fairness-отчёт сформирован")
        return report

    def get_feature_importance(self) -> pd.DataFrame:
        """Важность признаков из обученной модели."""
        importance = self.model.feature_importances_
        df = pd.DataFrame({
            'feature': self.feature_names,
            'importance': importance,
        })
        return df.sort_values('importance', ascending=False).reset_index(drop=True)

    # ==================================================================
    # PERSISTENCE
    # ==================================================================

    def save(self, path: str):
        data = {
            'model': self.model,
            'label_encoders': self.label_encoders,
            'feature_names': self.feature_names,
            'feature_types': self.feature_types,
            'categorical_features': self._categorical_features,
        }
        with open(path, 'wb') as f:
            pickle.dump(data, f)

        logger.info(f"Модель сохранена: {path}")

    def load(self, path: str):
        with open(path, 'rb') as f:
            data = pickle.load(f)

        self.model = data['model']
        self.label_encoders = data['label_encoders']
        self.feature_names = data['feature_names']
        self.feature_types = data['feature_types']
        self._categorical_features = data.get('categorical_features', [])

        logger.info(f"Модель загружена: {path}")

    # ==================================================================
    # PRIVATE
    # ==================================================================

    def _cross_validate(
        self, X: pd.DataFrame, y: pd.Series, n_splits: int,
    ) -> List[Dict[str, float]]:
        """StratifiedKFold кросс-валидация."""

        kfold = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)
        fold_metrics: List[Dict[str, float]] = []

        logger.info(f"Кросс-валидация ({n_splits} фолдов)...")

        for fold_idx, (train_idx, val_idx) in enumerate(kfold.split(X, y), 1):
            X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
            y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]

            fold_model = LGBMClassifier(**MODEL_PARAMS)
            fold_model.fit(
                X_train, y_train,
                categorical_feature=self._categorical_features,
            )

            y_proba = fold_model.predict_proba(X_val)[:, 1]
            y_pred = fold_model.predict(X_val)

            auc = roc_auc_score(y_val, y_proba)
            precision, recall, f1, _ = precision_recall_fscore_support(
                y_val, y_pred, average='binary', zero_division=0,
            )
            acc = accuracy_score(y_val, y_pred)
            ll = log_loss(y_val, y_proba)
            ap = average_precision_score(y_val, y_proba)
            tn, fp, fn, tp = confusion_matrix(y_val, y_pred).ravel()

            m = {
                'auc': auc,
                'f1': f1,
                'precision': precision,
                'recall': recall,
                'accuracy': acc,
                'log_loss': ll,
                'avg_precision': ap,
                'gini': 2 * auc - 1,
                'tp': int(tp), 'fp': int(fp),
                'tn': int(tn), 'fn': int(fn),
            }
            fold_metrics.append(m)

            logger.info(
                f"  Fold {fold_idx}: AUC={auc:.3f}  F1={f1:.3f}  "
                f"Prec={precision:.3f}  Rec={recall:.3f}  Acc={acc:.3f}"
            )

        return fold_metrics

    @staticmethod
    def _aggregate_cv_metrics(fold_metrics: List[Dict[str, float]]) -> Dict[str, float]:
        """Агрегация метрик по фолдам (mean ± std)."""
        agg: Dict[str, float] = {}

        score_keys = ['auc', 'f1', 'precision', 'recall', 'accuracy',
                       'log_loss', 'avg_precision', 'gini']

        for key in score_keys:
            values = [m[key] for m in fold_metrics]
            agg[f'{key}_mean'] = round(float(np.mean(values)), 4)
            agg[f'{key}_std'] = round(float(np.std(values)), 4)

        # Суммарная confusion matrix
        for key in ('tp', 'fp', 'tn', 'fn'):
            agg[f'total_{key}'] = sum(m[key] for m in fold_metrics)

        return agg