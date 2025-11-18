import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Marketing Dashboard", layout="wide")

# --- LOAD DATA ---
@st.cache_data
def load_data():
    url = "https://raw.githubusercontent.com/rodi-ux/marketing-dashboard/main/data.csv"
    df = pd.read_csv(url)
    return df

df = load_data()

st.title("📊 Marketing Dashboard – Mosaicos no Canadá")
st.write("Dados carregados do arquivo `data.csv` do GitHub.")

st.dataframe(df)
