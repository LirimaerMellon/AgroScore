"""
ScoringModel — обучение, оценка и сериализация модели скоринга.

Ключевые возможности:
- StratifiedKFold кросс-валидация
- Нативная поддержка категориальных фичей LightGBM
- Fine-tuning через init_model (дообучение на новых данных)
- Сохранение FeatureEngineer вместе с моделью
- Fairness-анализ
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
from typing import Dict, List, Any, Optional

from app.config import MODEL_PARAMS

logger = logging.getLogger(__name__)


class ScoringModel:

    def __init__(self):
        self.model = LGBMClassifier(**MODEL_PARAMS)
        self.label_encoders: Dict[str, LabelEncoder] = {}
        self.feature_names: List[str] = []
        self.feature_types: Dict[str, str] = {}
        self._categorical_features: List[str] = []
        self._known_categories: Dict[str, set] = {}   # значения из обучающих данных
        self._category_modes: Dict[str, int] = {}      # мода (самая частая категория) → encoded

    # ==================================================================
    # FEATURE PREPARATION
    # ==================================================================

    # Временные признаки НЕ используются — скоринг только по атрибутам заявки
    EXCLUDE_COLS = {
        'application_id', 'request_number', 'row_number',
        'is_approved', 'status', 'submission_date',
        'index', 'date', 'bin_iin',
        # Дата-фичи исключены: скоринг не должен зависеть от даты
        'days_since_submission', 'month', 'quarter', 'day_of_week', 'day',
    }

    def prepare_features(self, df: pd.DataFrame, fit: bool = False) -> pd.DataFrame:
        df = df.copy()

        feature_cols = [c for c in df.columns if c not in self.EXCLUDE_COLS]

        categorical = df[feature_cols].select_dtypes(include=['object']).columns.tolist()
        numeric = df[feature_cols].select_dtypes(include=[np.number]).columns.tolist()

        for col in categorical:
            if fit:
                le = LabelEncoder()
                col_str = df[col].astype(str)
                df[col] = le.fit_transform(col_str)
                self.label_encoders[col] = le
                # Запоминаем известные значения
                self._known_categories[col] = set(le.classes_)
                # Запоминаем моду (самая частая категория → её encoded индекс)
                mode_value = col_str.mode().iloc[0] if len(col_str) > 0 else le.classes_[0]
                self._category_modes[col] = int(le.transform([mode_value])[0])
            else:
                if col in self.label_encoders:
                    le = self.label_encoders[col]
                    known = set(le.classes_)
                    # Неизвестные значения → мода обучающих данных
                    # (а НЕ 0 — который просто первая алфавитная категория)
                    mode_encoded = self._category_modes.get(col, 0)
                    df[col] = df[col].astype(str).map(
                        lambda x, _le=le, _known=known, _mode=mode_encoded: (
                            _le.transform([x])[0] if x in _known else _mode
                        )
                    )
                else:
                    df[col] = 0

            self.feature_types[col] = 'categorical'

        for col in numeric:
            self.feature_types[col] = 'numeric'

        feature_names = numeric + categorical

        if fit:
            self.feature_names = feature_names
            self._categorical_features = categorical

        # Обратная совместимость: если старая модель ожидает фичи (например
        # days_since_submission, month, ...), которых уже нет в данных — заполнить 0.
        # Для новых моделей (обученных без дат) этого не произойдёт.
        for col in self.feature_names:
            if col not in df.columns:
                logger.warning(f"Фича '{col}' отсутствует в данных — заполнена 0 (обратная совместимость)")
                df[col] = 0

        return df[self.feature_names]

    # ==================================================================
    # TRAINING
    # ==================================================================

    def train(
        self,
        df: pd.DataFrame,
        n_splits: int = 5,
        base_model: Optional[LGBMClassifier] = None,
    ) -> Dict[str, Any]:
        """
        Обучение модели.
        base_model — если передан, используется как init_model (fine-tuning).
        """
        logger.info("=" * 50)
        logger.info("ОБУЧЕНИЕ МОДЕЛИ")
        logger.info("=" * 50)

        df_train = df[df['is_approved'] != -1].copy()

        X = self.prepare_features(df_train, fit=True)
        y = df_train['is_approved'].astype(int)

        logger.info(f"Размер выборки: {len(X)}")
        logger.info(f"Признаков: {len(self.feature_names)}")
        logger.info(f"Баланс классов: approved={int(y.sum())} / rejected={int((1 - y).sum())} "
                     f"({y.mean():.1%} positive)")

        # --- Cross-validation ---
        cv_metrics = self._cross_validate(X, y, n_splits)

        # --- Final model on all data ---
        logger.info("Обучение финальной модели на всех данных...")
        fit_kwargs = {'categorical_feature': self._categorical_features}
        if base_model is not None:
            fit_kwargs['init_model'] = base_model
            logger.info("Fine-tuning: используется базовая модель как init_model")

        self.model.fit(X, y, **fit_kwargs)

        # --- Aggregate metrics ---
        agg = self._aggregate_cv_metrics(cv_metrics)

        logger.info("-" * 50)
        logger.info(f"AUC:       {agg['auc_mean']:.3f} ± {agg['auc_std']:.3f}")
        logger.info(f"F1:        {agg['f1_mean']:.3f} ± {agg['f1_std']:.3f}")
        logger.info(f"Precision: {agg['precision_mean']:.3f}")
        logger.info(f"Recall:    {agg['recall_mean']:.3f}")
        logger.info(f"Accuracy:  {agg['accuracy_mean']:.3f}")
        logger.info(f"Gini:      {agg['gini_mean']:.3f}")
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
        Enterprise-скоринг с учётом качества данных.

        Философия:
        - Модель даёт лучшую оценку на основе доступных данных
        - Неизвестные поля → мягкий дисконт + прозрачный индикатор качества
        - Заявки с низким качеством данных → review_required (рекомендация комиссии)
        - Новый фермер из нового региона НЕ карается автоматически
        """
        df = df.copy()
        X = self.prepare_features(df, fit=False)

        probabilities = self.model.predict_proba(X)[:, 1]

        # --- Уровень доверия к данным ---
        if 'unknown_ratio' in df.columns:
            unknown_ratio = df['unknown_ratio'].values
        else:
            unknown_ratio = np.zeros(len(df))

        # Мягкий линейный дисконт: ~10% за каждое неизвестное поле из 5.
        # Новый фермер с 1 неизвестным полем теряет всего 10% — это справедливо.
        # Полный мусор (5/5) теряет 50% — всё ещё получает оценку, но со скидкой.
        # Комиссия видит data_quality и review_required для принятия решения.
        #
        # ratio=0.0 → confidence=1.00  (данные полные)
        # ratio=0.2 → confidence=0.90  (1 поле — минимальная скидка)
        # ratio=0.4 → confidence=0.80  (2 поля — умеренная скидка)
        # ratio=0.6 → confidence=0.70  (3 поля — заметная скидка)
        # ratio=1.0 → confidence=0.50  (все поля неизвестны)
        confidence = np.clip(1.0 - unknown_ratio * 0.5, 0.5, 1.0)

        adjusted_proba = probabilities * confidence
        scores = np.round(adjusted_proba * 100, 2)

        # --- Индикаторы качества данных (НЕ влияют на score) ---
        # review_required: рекомендация ручной проверки при 2+ неизвестных полях
        review_required = unknown_ratio >= 0.4

        # data_quality: прозрачный уровень полноты данных
        data_quality = np.where(
            unknown_ratio == 0, 'complete',
            np.where(unknown_ratio <= 0.2, 'high',
                     np.where(unknown_ratio <= 0.4, 'medium', 'low'))
        )

        df['score'] = scores
        df['probability'] = adjusted_proba
        df['raw_probability'] = probabilities
        df['confidence'] = np.round(confidence, 4)
        df['review_required'] = review_required
        df['data_quality'] = data_quality
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
        if 'score' not in df.columns:
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

            if len(stats) > 1 and stats['mean'].min() > 0:
                di = round(stats['mean'].max() / stats['mean'].min(), 3)
                report[f'{col}_disparate_impact'] = di

        return report

    def get_feature_importance(self) -> pd.DataFrame:
        importance = self.model.feature_importances_.astype(float)
        total = importance.sum()
        if total > 0:
            importance = importance / total
        df = pd.DataFrame({
            'feature': self.feature_names,
            'importance': importance,
        })
        return df.sort_values('importance', ascending=False).reset_index(drop=True)

    # ==================================================================
    # PERSISTENCE — сохранение/загрузка с FeatureEngineer
    # ==================================================================

    def save(self, path: str, feature_engineer=None):
        """Сохраняет модель + label encoders + FeatureEngineer."""
        data = {
            'model': self.model,
            'label_encoders': self.label_encoders,
            'feature_names': self.feature_names,
            'feature_types': self.feature_types,
            'categorical_features': self._categorical_features,
            'known_categories': self._known_categories,
            'category_modes': self._category_modes,
            'feature_engineer': feature_engineer,
        }
        with open(path, 'wb') as f:
            pickle.dump(data, f)
        logger.info(f"Модель сохранена: {path}")

    def load(self, path: str):
        """
        Загружает модель. Возвращает FeatureEngineer (или None).
        """
        with open(path, 'rb') as f:
            data = pickle.load(f)

        self.model = data['model']
        self.label_encoders = data['label_encoders']
        self.feature_names = data['feature_names']
        self.feature_types = data['feature_types']
        self._categorical_features = data.get('categorical_features', [])
        self._known_categories = data.get('known_categories', {})
        self._category_modes = data.get('category_modes', {})

        fe = data.get('feature_engineer')
        logger.info(f"Модель загружена: {path}")
        return fe

    # ==================================================================
    # PRIVATE
    # ==================================================================

    def _cross_validate(
        self, X: pd.DataFrame, y: pd.Series, n_splits: int,
    ) -> List[Dict[str, float]]:
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
                'auc': auc, 'f1': f1, 'precision': precision, 'recall': recall,
                'accuracy': acc, 'log_loss': ll, 'avg_precision': ap,
                'gini': 2 * auc - 1,
                'tp': int(tp), 'fp': int(fp), 'tn': int(tn), 'fn': int(fn),
            }
            fold_metrics.append(m)

            logger.info(
                f"  Fold {fold_idx}: AUC={auc:.3f}  F1={f1:.3f}  "
                f"Prec={precision:.3f}  Rec={recall:.3f}  Acc={acc:.3f}"
            )

        return fold_metrics

    @staticmethod
    def _aggregate_cv_metrics(fold_metrics: List[Dict[str, float]]) -> Dict[str, float]:
        agg: Dict[str, float] = {}
        score_keys = ['auc', 'f1', 'precision', 'recall', 'accuracy',
                       'log_loss', 'avg_precision', 'gini']
        for key in score_keys:
            values = [m[key] for m in fold_metrics]
            agg[f'{key}_mean'] = round(float(np.mean(values)), 4)
            agg[f'{key}_std'] = round(float(np.std(values)), 4)

        for key in ('tp', 'fp', 'tn', 'fn'):
            agg[f'total_{key}'] = sum(m[key] for m in fold_metrics)

        return agg

