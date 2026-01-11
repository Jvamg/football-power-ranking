import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Premier League GK Power Ranking",
    page_icon="🧤",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilo CSS Customizado (Dark Mode Clean)
st.markdown("""
<style>
    [data-testid="stMetricValue"] {
        font-size: 24px;
    }
    .stDataFrame {
        border: 1px solid #333;
    }
</style>
""", unsafe_allow_html=True)

# --- 1. CARGA E PREPARAÇÃO DE DADOS ---


@st.cache_data
def load_data():
    # Tenta carregar do caminho padrão do seu projeto
    path = "notebooks/data/processed/final_ranking_table.csv"

    if not os.path.exists(path):
        st.error(
            f"Arquivo não encontrado em: {path}. Rode o notebook 02_ranking_logic.ipynb primeiro.")
        return pd.DataFrame()  # Retorna vazio para não quebrar

    df = pd.read_csv(path)

    # Tratamento de Nulos (Garante que calculos não quebrem)
    cols_to_fill = ['PSxG_Net_p90', 'Prevention_Ratio',
                    'OPA', 'Crosses_Stopped_pct', 'Launch_Completion_pct']
    for col in cols_to_fill:
        if col in df.columns:
            df[col] = df[col].fillna(0)

    return df


def calculate_scores(df):
    """
    Normaliza os dados brutos (0-100) para permitir o cálculo dinâmico dos pesos.
    Baseado na lógica do seu notebook 02.
    """
    # Função auxiliar de normalização (Percentil)
    def normalize(series):
        return series.rank(pct=True) * 100

    # Criação dos Scores Parciais (Se não existirem no CSV)
    # 1. Score de Defesa (Shot Stopping)
    # Combina Volume (PSxG +/- p90) e Eficiência (Prevention Ratio)
    if 'PSxG_Net_p90' in df.columns and 'Prevention_Ratio' in df.columns:
        df['Score_Defesa'] = normalize(
            df['PSxG_Net_p90'] + df['Prevention_Ratio'])
    else:
        df['Score_Defesa'] = 50  # Fallback

    # 2. Score de Distribuição (Jogo com os pés)
    # Usa OPA (Saídas do gol) e Lançamentos se tiver
    dist_cols = [c for c in [
        'OPA', 'Launch_Completion_pct'] if c in df.columns]
    if dist_cols:
        df['Score_Distribuicao'] = normalize(df[dist_cols].sum(axis=1))
    else:
        df['Score_Distribuicao'] = 50

    # 3. Score Aéreo (Cruzamentos)
    if 'Crosses_Stopped_pct' in df.columns:
        df['Score_Aereo'] = normalize(df['Crosses_Stopped_pct'])
    elif 'Crosses_Stopped' in df.columns:  # Fallback se for numero absoluto
        df['Score_Aereo'] = normalize(df['Crosses_Stopped'])
    else:
        df['Score_Aereo'] = 50

    return df


# Carrega e processa
raw_df = load_data()
if not raw_df.empty:
    df = calculate_scores(raw_df.copy())
else:
    st.stop()

# --- 2. SIDEBAR (CONTROLES) ---
st.sidebar.header("⚙️ Painel de Controle")

st.sidebar.subheader("Pesos do Algoritmo")
w_shot = st.sidebar.slider("🧤 Defesa (Shot Stopping)", 0, 100,
                           70, help="Peso para gols evitados e defesas difíceis.")
w_dist = st.sidebar.slider("👟 Distribuição (Pés)", 0,
                           100, 15, help="Peso para lançamentos e saídas do gol.")
w_cross = st.sidebar.slider(
    "✈️ Controle Aéreo", 0, 100, 15, help="Peso para interceptação de cruzamentos.")

# Normaliza os pesos para somar 1.0
total_w = w_shot + w_dist + w_cross
if total_w == 0:
    total_w = 1  # Evita divisão por zero
pct_shot = w_shot / total_w
pct_dist = w_dist / total_w
pct_cross = w_cross / total_w

st.sidebar.markdown("---")
st.sidebar.subheader("Filtros")
times = sorted(df['Team'].unique())
selected_teams = st.sidebar.multiselect("Filtrar Times", times, default=times)

min_games = st.sidebar.number_input("Mínimo de Jogos", 1, 38, 5)

# --- 3. CÁLCULO DINÂMICO ---
# Filtra antes de calcular para performance
df_filtered = df[
    (df['Team'].isin(selected_teams)) &
    (df['Games_Played'] >= min_games)
].copy()

# Recalcula o Score Final baseado nos sliders
df_filtered['Score Final'] = (
    (df_filtered['Score_Defesa'] * pct_shot) +
    (df_filtered['Score_Distribuicao'] * pct_dist) +
    (df_filtered['Score_Aereo'] * pct_cross)
).round(1)

# Ordena
df_filtered = df_filtered.sort_values(
    by='Score Final', ascending=False).reset_index(drop=True)
df_filtered.index += 1  # Começar ranking do 1

# --- 4. INTERFACE PRINCIPAL ---
st.title("🏆 Premier League GK Power Ranking")
st.caption(
    f"Dados atualizados da temporada 25/26 | Critério: {pct_shot:.0%} Defesa / {pct_dist:.0%} Dist. / {pct_cross:.0%} Aéreo")

# Top 3 Cards
col1, col2, col3 = st.columns(3)
top3 = df_filtered.head(3)

if len(top3) >= 1:
    col1.metric("🥇 1º Lugar", top3.iloc[0]['Player'],
                f"{top3.iloc[0]['Score Final']} pts")
if len(top3) >= 2:
    col2.metric("🥈 2º Lugar", top3.iloc[1]['Player'],
                f"{top3.iloc[1]['Score Final']} pts")
if len(top3) >= 3:
    col3.metric("🥉 3º Lugar", top3.iloc[2]['Player'],
                f"{top3.iloc[2]['Score Final']} pts")

st.divider()

# Layout: Tabela + Gráfico
col_tab, col_chart = st.columns([1.5, 1])

with col_tab:
    st.subheader("Classificação Detalhada")

    # Selecionar colunas para exibir
    cols_show = ['Player', 'Team', 'Score Final', 'Score_Defesa',
                 'Score_Distribuicao', 'Score_Aereo', 'Games_Played']

    # Formatação condicional (Highlight no score)
    st.dataframe(
        df_filtered[cols_show].style.background_gradient(
            subset=['Score Final'], cmap='Blues'),
        use_container_width=True,
        height=500
    )

with col_chart:
    st.subheader("🎯 Análise de Perfil")

    player_select = st.selectbox(
        "Selecione um Goleiro:", df_filtered['Player'].unique())

    if player_select:
        player_data = df_filtered[df_filtered['Player']
                                  == player_select].iloc[0]

        # Gráfico Radar (Plotly)
        categories = ['Shot Stopping', 'Distribuição', 'Aéreo']
        values = [
            player_data['Score_Defesa'],
            player_data['Score_Distribuicao'],
            player_data['Score_Aereo']
        ]

        fig = go.Figure()

        # Adiciona a área preenchida
        fig.add_trace(go.Scatterpolar(
            r=values,
            theta=categories,
            fill='toself',
            name=player_data['Player'],
            line_color='#00d4ff',
            fillcolor='rgba(0, 212, 255, 0.3)'
        ))

        # Layout bonito
        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 100],
                    tickfont=dict(color='gray'),
                    gridcolor='#333'
                ),
                angularaxis=dict(
                    tickfont=dict(size=14, color='white')
                ),
                bgcolor="rgba(0,0,0,0)"
            ),
            paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=40, r=40, t=20, b=20),
            showlegend=False
        )

        st.plotly_chart(fig, use_container_width=True)

        # Insights Rápidos
        st.info(
            f"**Análise Rápida:** {player_select} tem nota **{player_data['Score_Defesa']:.0f}** em defesa pura.")

# Rodapé
st.markdown("---")
st.markdown("Desenvolvido para análise de portfólio data-driven.")
