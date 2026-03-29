
import streamlit as st
import pandas as pd
import joblib

st.set_page_config(layout="wide")
st.title("🚜 Subsidy Scoring (LightGBM)")

model = joblib.load("model.pkl")

file = st.file_uploader("Upload CSV", type=["csv"])

budget = st.sidebar.number_input("Budget", value=10000000)

if file:
    df = pd.read_csv(file)

    df["score"] = model.predict_proba(df)[:,1]
    df_sorted = df.sort_values("score", ascending=False)

    st.subheader("Ranking")
    st.dataframe(df_sorted)

    # shortlist
    total = 0
    selected = []

    for _, row in df_sorted.iterrows():
        if total + row["amount"] <= budget:
            selected.append(row)
            total += row["amount"]

    st.subheader("Shortlist")
    st.write("Allocated:", total)
    st.dataframe(pd.DataFrame(selected))
