# app.py
from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Vehicle Explorer", layout="wide")

# --------- Localiza o CSV (prioriza o limpo, se existir) ---------
project_root = Path.cwd()
if project_root.name == "notebooks":
    project_root = project_root.parent

clean_path = project_root / "vehicles_us_clean.csv"
raw_path   = project_root / "vehicles_us.csv"
csv_path   = clean_path if clean_path.exists() else raw_path

# --------- Carregamento com cache ---------
@st.cache_data(show_spinner=False)
def load_data(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    # normalização leve para filtros
    for col in ["model","condition","fuel","transmission","type","paint_color"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.lower()
    # garante colunas-chave
    for c in ["price","model_year","odometer"]:
        if c not in df.columns:
            df[c] = pd.NA
    return df

df = load_data(csv_path)
st.caption(f"Usando dados: `{csv_path.name}` — {len(df):,} linhas")

st.title("Análise de Veículos (US)")

# --------- Sidebar: Filtros ---------
st.sidebar.header("Filtros")

def safe_min(col, default):
    try:
        return int(pd.to_numeric(df[col], errors="coerce").min())
    except Exception:
        return default

def safe_max(col, default):
    try:
        return int(pd.to_numeric(df[col], errors="coerce").max())
    except Exception:
        return default

price_min, price_max = safe_min("price", 0), safe_max("price", 200_000)
odo_min,   odo_max   = safe_min("odometer", 0), safe_max("odometer", 500_000)
year_min,  year_max  = safe_min("model_year", 1980), safe_max("model_year", 2025)

year_range  = st.sidebar.slider("Model year",  min_value=year_min,  max_value=year_max,  value=(max(1990, year_min), year_max))
price_range = st.sidebar.slider("Preço (USD)", min_value=price_min, max_value=price_max, value=(max(500, price_min), min(150_000, price_max)))
odo_range   = st.sidebar.slider("Quilometragem", min_value=odo_min, max_value=odo_max, value=(odo_min, min(300_000, odo_max)))

def safe_unique(col):
    return sorted(x for x in df[col].dropna().unique()) if col in df.columns else []

cond_sel  = st.sidebar.multiselect("Condição",    safe_unique("condition"))
fuel_sel  = st.sidebar.multiselect("Combustível", safe_unique("fuel"))
trans_sel = st.sidebar.multiselect("Transmissão", safe_unique("transmission"))
type_sel  = st.sidebar.multiselect("Tipo",        safe_unique("type"))

# --------- Aplica filtros ---------
mask = pd.Series(True, index=df.index)

if "model_year" in df:
    mask &= pd.to_numeric(df["model_year"], errors="coerce").between(year_range[0], year_range[1], inclusive="both")
if "price" in df:
    mask &= pd.to_numeric(df["price"], errors="coerce").between(price_range[0], price_range[1], inclusive="both")
if "odometer" in df:
    mask &= pd.to_numeric(df["odometer"], errors="coerce").between(odo_range[0], odo_range[1], inclusive="both")

if cond_sel and "condition" in df:     mask &= df["condition"].isin(cond_sel)
if fuel_sel and "fuel" in df:          mask &= df["fuel"].isin(fuel_sel)
if trans_sel and "transmission" in df: mask &= df["transmission"].isin(trans_sel)
if type_sel and "type" in df:          mask &= df["type"].isin(type_sel)

df_f = df[mask].copy()

# Conjuntos para visualização com filtro leve de outliers
df_viz = df_f.copy()
if "price" in df_viz:
    df_viz = df_viz[pd.to_numeric(df_viz["price"], errors="coerce").between(500, 150_000)]
if "odometer" in df_viz:
    df_viz = df_viz[pd.to_numeric(df_viz["odometer"], errors="coerce") < 500_000]

# --------- Métricas rápidas ---------
colA, colB, colC = st.columns(3)
with colA:
    st.metric("Veículos filtrados", f"{len(df_f):,}")
with colB:
    if "price" in df_f:
        st.metric("Preço médio (USD)", f"{pd.to_numeric(df_f['price'], errors='coerce').mean():,.0f}")
with colC:
    if "odometer" in df_f:
        st.metric("Quilometragem média", f"{pd.to_numeric(df_f['odometer'], errors='coerce').mean():,.0f}")

# --------- Abas ---------
tab0, tab1, tab2, tab3, tab4 = st.tabs(["Visão geral", "Distribuição de preços", "Ano × Preço", "Quilometragem × Preço", "Preço por condição"])

with tab0:
    st.subheader("Amostra dos dados")
    st.dataframe(df_f.head(50))

with tab1:
    st.subheader("Distribuição de preços")
    if "price" in df_viz:
        fig = px.histogram(df_viz, x="price", nbins=60, title="Distribuição de preços (com filtro leve de outliers)")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Coluna 'price' não encontrada.")

with tab2:
    st.subheader("Preço vs. ano do carro")
    if {"model_year","price"}.issubset(df_viz.columns):
        fig = px.scatter(df_viz, x="model_year", y="price", opacity=0.5, title="Preço vs. Ano")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Colunas 'model_year' e/ou 'price' não encontradas.")

with tab3:
    st.subheader("Preço vs. quilometragem")
    if {"odometer","price"}.issubset(df_viz.columns):
        fig = px.scatter(df_viz, x="odometer", y="price", opacity=0.5, title="Preço vs. Odômetro")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Colunas 'odometer' e/ou 'price' não encontradas.")

with tab4:
    st.subheader("Preço por condição do veículo")
    if {"condition","price"}.issubset(df_viz.columns):
        fig = px.box(df_viz, x="condition", y="price", title="Preço por condição")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Colunas 'condition' e/ou 'price' não encontradas.")