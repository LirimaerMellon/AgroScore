
# Subsidy Scoring System (LightGBM Version)

## Overview
Production-ready ML system using LightGBM for subsidy scoring.

## Stack
- scikit-learn (data processing)
- LightGBM (model)
- SHAP (explainability)
- FastAPI (API)
- Streamlit (UI)

## Setup (Windows / Server)

### 1. Install dependencies
pip install -r requirements.txt

### 2. Train model
python train.py

### 3. Run API
uvicorn app:app --reload

### 4. Run UI
streamlit run ui.py

## Input data
CSV file: data_clear.csv

## Output
- score
- explanation
- ranking
