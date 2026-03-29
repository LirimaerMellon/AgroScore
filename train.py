
# === IMPORTS ===
import pandas as pd
import joblib

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.metrics import roc_auc_score

import lightgbm as lgb

# === LOAD DATA ===
df = pd.read_csv("data_clear.csv")
df.columns = df.columns.str.lower()

# === TARGET ===
df["status"] = df["status"].apply(
    lambda x: 1 if x in ["одобрена","исполнена"] else 0
)

# === FEATURES ===
cat = ["region","district","subsidy_type","direction"]
num = ["amount","normative"]

X = df[cat + num]
y = df["status"]

# === PREPROCESS ===
pre = ColumnTransformer([
    ("cat", OneHotEncoder(handle_unknown="ignore"), cat),
    ("num", "passthrough", num)
])

# === SPLIT ===
Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=42)

# === MODEL ===
model = lgb.LGBMClassifier(
    n_estimators=300,
    learning_rate=0.05,
    max_depth=6
)

pipe = Pipeline([
    ("pre", pre),
    ("model", model)
])

# === TRAIN ===
pipe.fit(Xtr, ytr)

# === EVAL ===
pred = pipe.predict_proba(Xte)[:,1]
print("ROC-AUC:", roc_auc_score(yte, pred))

# === SAVE ===
joblib.dump(pipe, "model.pkl")
print("Model saved")
