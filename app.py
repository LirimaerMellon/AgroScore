
from fastapi import FastAPI
import pandas as pd
import joblib
import shap

app = FastAPI()

model = joblib.load("model.pkl")
explainer = shap.Explainer(model.named_steps["model"])

@app.post("/score")
def score(data: dict):
    df = pd.DataFrame([data])
    proba = model.predict_proba(df)[0][1]

    Xp = model.named_steps["pre"].transform(df)
    shap_vals = explainer(Xp)

    explanation = []
    for name, val in zip(
        model.named_steps["pre"].get_feature_names_out(),
        shap_vals.values[0]
    ):
        if abs(val) > 0.05:
            explanation.append({"feature": name, "impact": float(val)})

    return {
        "score": float(proba),
        "decision": "RECOMMENDED" if proba > 0.7 else "REVIEW",
        "explanation": explanation
    }
