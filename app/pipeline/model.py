import pandas as pd
import numpy as np
from sklearn.preprocessing import LabelEncoder
from lightgbm import LGBMClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, precision_recall_fscore_support
import pickle
import logging
from app.config import MODEL_PARAMS

logger = logging.getLogger(__name__)


class ScoringModel:
    def __init__(self):
        self.model = LGBMClassifier(**MODEL_PARAMS)
        self.label_encoders = {}
        self.feature_names = []
        self.feature_types = {}

    def prepare_features(self, df: pd.DataFrame, fit: bool = False) -> pd.DataFrame:
        df = df.copy()

        exclude_cols = {
            'application_id', 'is_approved', 'status',
            'index', 'date'
        }

        feature_cols = [col for col in df.columns if col not in exclude_cols]

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
                    df[col] = df[col].astype(str)

                    # handle unseen labels
                    df[col] = df[col].map(
                        lambda x: le.transform([x])[0] if x in le.classes_ else -1
                    )
                else:
                    df[col] = -1

            self.feature_types[col] = 'categorical'

        for col in numeric:
            self.feature_types[col] = 'numeric'

        feature_names = numeric + categorical

        if fit:
            self.feature_names = feature_names

        df = df[self.feature_names]

        return df

    def train(self, df: pd.DataFrame, test_size: float = 0.2) -> dict:
        logger.info("Тренируем LightGBM...")

        df_train = df[df['is_approved'] != -1].copy()

        X = self.prepare_features(df_train, fit=True)
        y = df_train['is_approved']

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=42, stratify=y
        )

        self.model.fit(X_train, y_train)

        y_pred_proba = self.model.predict_proba(X_test)[:, 1]
        auc = roc_auc_score(y_test, y_pred_proba)

        y_pred = self.model.predict(X_test)
        precision, recall, f1, _ = precision_recall_fscore_support(
            y_test, y_pred, average='binary'
        )

        logger.info(f"✓ AUC: {auc:.3f}")
        logger.info(f"✓ F1: {f1:.3f}")

        return {
            'auc': auc,
            'precision': precision,
            'recall': recall,
            'f1': f1
        }

    def score(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()

        X = self.prepare_features(df, fit=False)

        probabilities = self.model.predict_proba(X)[:, 1]
        scores = probabilities * 100

        df['score'] = scores
        df['probability'] = probabilities

        df['category'] = pd.cut(
            scores,
            bins=[0, 40, 70, 100],
            labels=['LOW', 'MEDIUM', 'HIGH']
        )

        return df

    def save(self, path: str):
        data = {
            'model': self.model,
            'label_encoders': self.label_encoders,
            'feature_names': self.feature_names,
            'feature_types': self.feature_types
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

        logger.info(f"Модель загружена: {path}")