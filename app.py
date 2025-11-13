import streamlit as st
import pandas as pd
import plotly.express as px

# --- Configuração da página ---
st.set_page_config(page_title="Marketing Dashboard", page_icon="📊", layout="wide")

# --- Título ---
st.title("📊 Marketing Dashboard Interativo")

# --- Dados simulados ---
data = {
    "Canal": ["Google Ads", "Meta Ads", "LinkedIn", "Email", "Orgânico"] * 6,
    "Mês": ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun"] * 5,
    "Leads": [120, 140, 150, 130, 160, 170,
              90, 110, 100, 130, 120, 125,
              60, 80, 90, 95, 100, 120,
              40, 60, 70, 50, 65, 80,
              200, 210, 220, 230, 240, 260],
    "Custo": [800, 850, 870, 900, 950, 970,
              600, 640, 650, 670, 680, 700,
              400, 420, 440, 460, 480, 500,
              300, 320, 340, 360, 380, 400,
              0, 0, 0, 0, 0, 0]
}

df = pd.DataFrame(data)

# --- Filtros ---
st.sidebar.header("Filtros")
meses = st.sidebar.multiselect("Selecione o mês:", options=df["Mês"].unique(), default=df["Mês"].unique())
canais = st.sidebar.multiselect("Selecione o canal:", options=df["Canal"].unique(), default=df["Canal"].unique())

# --- Dados filtrados ---
df_filtrado = df[(df["Mês"].isin(meses)) & (df["Canal"].isin(canais))]

# --- KPIs ---
total_leads = int(df_filtrado["Leads"].sum())
total_custo = int(df_filtrado["Custo"].sum())
cpl = round(total_custo / total_leads, 2) if total_leads > 0 else 0

col1, col2, col3 = st.columns(3)
col1.metric("Total de Leads", f"{total_leads}")
col2.metric("Custo Total (R$)", f"{total_custo}")
col3.metric("Custo por Lead (CPL)", f"R$ {cpl}")

# --- Gráficos ---
fig_leads = px.bar(df_filtrado, x="Mês", y="Leads", color="Canal", barmode="group", title="Leads por Canal")
fig_custo = px.line(df_filtrado, x="Mês", y="Custo", color="Canal", title="Custo Mensal por Canal")

st.plotly_chart(fig_leads, use_container_width=True)
st.plotly_chart(fig_custo, use_container_width=True)

# --- Tabela ---
st.subheader("📋 Dados Detalhados")
st.dataframe(df_filtrado)

st.caption("Criado com ❤️ usando Streamlit + Plotly")
