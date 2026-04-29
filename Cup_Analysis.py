# Importando bibliotecas
import pandas as pd
import numpy as np
from pathlib import Path
from difflib import get_close_matches
import streamlit as st

# Configurando o Streamlit
st.set_page_config(
    page_title="Copa do Mundo Dashboard",
    layout="wide"
)

# PATH
try:
    BASE_DIR = Path(__file__).resolve().parent
except NameError:
    BASE_DIR = Path().resolve()

DATA_DIR = BASE_DIR / "data"

# Cache para carregamento de dados
@st.cache_data
def load_csv(file_name, **kwargs):
    return pd.read_csv(DATA_DIR / file_name, **kwargs)

# Carregando dados
df_matches = load_csv("WorldCupMatches.csv", encoding="utf8")
df_2018 = load_csv("Cup.Russia.Matches.csv", sep=";", encoding="utf8")
df_2022 = load_csv("Fifa_world_cup_matches_2022.csv", encoding="utf8")

# Padronização de colunas
def padronizar_colunas(df):
    df = df.copy()
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")
    return df

df_matches = padronizar_colunas(df_matches)
df_2018 = padronizar_colunas(df_2018)
df_2022 = padronizar_colunas(df_2022)

# Alinhamento de nomes de colunas
df_matches = df_matches.rename(columns={
    "home_team_name": "home_team",
    "away_team_name": "away_team"
}, errors="ignore")

df_2018 = df_2018.rename(columns={
    "home_team_name": "home_team",
    "away_team_name": "away_team"
}, errors="ignore")

df_2022 = df_2022.rename(columns={
    "team1": "home_team",
    "team2": "away_team",
    "number_of_goals_team1": "home_team_goals",
    "number_of_goals_team2": "away_team_goals"
}, errors="ignore")

df_2018["year"] = 2018
df_2022["year"] = 2022

# Concatenando dados
df_all = pd.concat([df_matches, df_2018, df_2022], ignore_index=True)

# Padronização de nomes de países
def padronizar_paises(df):
    df = df.copy()

    df["home_team"] = df["home_team"].astype(str).str.replace(r'^.*?>', '', regex=True)
    df["away_team"] = df["away_team"].astype(str).str.replace(r'^.*?>', '', regex=True)

    df["home_team"] = df["home_team"].str.title().str.strip()
    df["away_team"] = df["away_team"].str.title().str.strip()

    return df

# Resultados: H = vitória casa, A = vitória visitante, D = empate
def padronizar_resultados(df):
    df = df.copy()

    df["home_team_goals"] = pd.to_numeric(df["home_team_goals"], errors="coerce")
    df["away_team_goals"] = pd.to_numeric(df["away_team_goals"], errors="coerce")

    df = df.dropna(subset=["home_team_goals", "away_team_goals"])

    df["home_team_goals"] = df["home_team_goals"].astype(int)
    df["away_team_goals"] = df["away_team_goals"].astype(int)

    df["result"] = np.where(
        df["home_team_goals"] > df["away_team_goals"], "H",
        np.where(df["home_team_goals"] < df["away_team_goals"], "A", "D")
    )

    return df

df_all = padronizar_paises(df_all)
df_all = padronizar_resultados(df_all)

# Dados Auxliares (para normalização de países e títulos)
mapa_paises = {
    "brasil": "Brazil",
    "argentina": "Argentina",
    "alemanha": "Germany",
    "franca": "France",
    "inglaterra": "England",
    "espanha": "Spain",
    "italia": "Italy",
    "portugal": "Portugal",
    "eua": "United States",
    "usa": "United States"
}

titulos_copa = {
    "Brazil": 5,
    "Germany": 4,
    "Italy": 4,
    "Argentina": 3,
    "Uruguay": 2,
    "France": 2,
    "England": 1,
    "Spain": 1
}

# Normalização
def normalizar_input(pais):
    pais = pais.strip().lower()
    return mapa_paises.get(pais, pais).lower()

# SCORE
def calcular_score(df, pais):
    pais = pais.lower()
    df_pais = df[(df["home_team"].str.lower() == pais) | (df["away_team"].str.lower() == pais)]

    if df_pais.empty:
        return 0

    score = 0

    for _, row in df_pais.iterrows():
        ano = row["year"]
        peso = 1 / (2026 - ano)

        if row["home_team"].lower() == pais:
            gp, gc = row["home_team_goals"], row["away_team_goals"]
        else:
            gp, gc = row["away_team_goals"], row["home_team_goals"]

        saldo = gp - gc

        if saldo > 0:
            score += 3 * peso
        elif saldo == 0:
            score += 1 * peso
        else:
            score += saldo * 0.5 * peso

        score += saldo * 0.1 * peso

        if ano == 2022:
            score += 2

    return round(score, 4)

# Estatísticas detalhadas por país
def stats_pais(df, pais):
    df_pais = df[(df["home_team"].str.lower() == pais) | (df["away_team"].str.lower() == pais)]

    total = len(df_pais)

    vitorias = len(df_pais[
        ((df_pais["home_team"].str.lower() == pais) & (df_pais["result"] == "H")) |
        ((df_pais["away_team"].str.lower() == pais) & (df_pais["result"] == "A"))
    ])

    derrotas = len(df_pais[
        ((df_pais["home_team"].str.lower() == pais) & (df_pais["result"] == "A")) |
        ((df_pais["away_team"].str.lower() == pais) & (df_pais["result"] == "H"))
    ])

    empates = len(df_pais[df_pais["result"] == "D"])

    gols_marcados = df_pais.apply(
        lambda r: r["home_team_goals"] if r["home_team"].lower() == pais else r["away_team_goals"],
        axis=1
    ).sum()

    gols_sofridos = df_pais.apply(
        lambda r: r["away_team_goals"] if r["home_team"].lower() == pais else r["home_team_goals"],
        axis=1
    ).sum()

    saldo = gols_marcados - gols_sofridos

    return total, vitorias, derrotas, empates, gols_marcados, gols_sofridos, saldo

# CSS (Tons de verde, preto e branco)
st.markdown("""
<style>

body {
    background-color: #f5fff5;
}

h1, h2, h3 {
    color: #1b5e20;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background-color: #e8f5e9;
}

/* TEXTO MENU PRETO */
section[data-testid="stSidebar"] * {
    color: black !important;
}

/* Botões */
.stButton>button {
    background-color: #2e7d32;
    color: white;
    border-radius: 8px;
}

/* Cards */
.card {
    background: white;
    padding: 15px;
    border-radius: 12px;
    border: 1px solid #c8e6c9;
}

</style>
""", unsafe_allow_html=True)

# UI
st.title("⚽ Copa do Mundo Dashboard")

menu = st.sidebar.radio("Menu", ["Análise", "Comparação", "Sobre"])


# Análise
if menu == "Análise":

    pais_input = st.text_input("Seleção", key="analise")

    if pais_input:

        pais = normalizar_input(pais_input)

        total, v, d, e, gm, gs, sg = stats_pais(df_all, pais)

        st.subheader(pais.title())

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Jogos", total)
        col2.metric("Vitórias", v)
        col3.metric("Empates", e)
        col4.metric("Derrotas", d)

        st.markdown("### Estatísticas avançadas")

        c1, c2, c3 = st.columns(3)
        c1.metric("Gols Marcados", gm)
        c2.metric("Gols Sofridos", gs)
        c3.metric("Saldo", sg)

        st.metric("Títulos", titulos_copa.get(pais.title(), 0))

if prob1 > prob2:
    st.success(f"Favorito: {p1.title()}")
elif prob2 > prob1:
    st.success(f"Favorito: {p2.title()}")
else:
    st.info("Equilíbrio entre seleções")

# Comparação
elif menu == "Comparação":

    p1 = st.text_input("Seleção 1", key="p1")
    p2 = st.text_input("Seleção 2", key="p2")

    if st.button("Comparar"):

        if p1 and p2:

            p1 = normalizar_input(p1)
            p2 = normalizar_input(p2)

            # SCORE
            s1 = calcular_score(df_all, p1)
            s2 = calcular_score(df_all, p2)

            total = float(s1 + s2)

            prob1 = (s1 / total) * 100 if total else 50
            prob2 = (s2 / total) * 100 if total else 50

            # STATS
            stats1 = stats_pais(df_all, p1)
            stats2 = stats_pais(df_all, p2)

            t1, v1, d1, e1, gm1, gs1, sg1 = stats1
            t2, v2, d2, e2, gm2, gs2, sg2 = stats2

            # RESULTADO
            st.subheader("Probabilidades")

            col1, col2 = st.columns(2)

            col1.metric(p1.title(), f"{prob1:.1f}%")
            col2.metric(p2.title(), f"{prob2:.1f}%")

            st.markdown("---")
            st.markdown("### Estatísticas completas")

            c1, c2 = st.columns(2)

            with c1:
                st.markdown(f"## {p1.title()}")
                st.metric("Jogos", t1)
                st.metric("Vitórias", v1)
                st.metric("Empates", e1)
                st.metric("Derrotas", d1)
                st.metric("Gols Marcados", gm1)
                st.metric("Gols Sofridos", gs1)
                st.metric("Saldo de Gols", sg1)

            with c2:
                st.markdown(f"## {p2.title()}")
                st.metric("Jogos", t2)
                st.metric("Vitórias", v2)
                st.metric("Empates", e2)
                st.metric("Derrotas", d2)
                st.metric("Gols Marcados", gm2)
                st.metric("Gols Sofridos", gs2)
                st.metric("Saldo de Gols", sg2)
# SOBRE
else:

    st.header("Sobre")

    st.write("""
    Projeto de análise de Copas do Mundo.
    
    ⚠️ Projeto não oficial, criado apenas para fins educacionais e de portfólio.

    Inclui:
    - Estatísticas históricas
    - Comparação entre seleções
    - Score baseado em performance e histórico
    """)
