
@echo off
pip install -r requirements.txt
python train.py
start cmd /k uvicorn app:app --reload
start cmd /k streamlit run ui.py
