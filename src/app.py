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

# Estilo CSS Customizado
st.markdown("""
<style>
    [data-testid="stMetricValue"] { font-size: 24px; }
    .stDataFrame { border: 1px solid #333; }
</style>
""", unsafe_allow_html=True)

# --- 1. CARGA DE DADOS ---


@st.cache_data
def load_data():
    path = "notebooks/data/processed/final_ranking_table.csv"

    if not os.path.exists(path):
        st.error(
            f"⚠️ Arquivo não encontrado: {path}. Execute o notebook '02_ranking_logic.ipynb' primeiro.")
        return pd.DataFrame()

    df = pd.read_csv(path)

    # Garante que as colunas de score existem e preenche nulos com 0
    score_cols = ['Score_Shot_Stopping',
                  'Score_Distribution', 'Score_Aerial', 'Games_Played']
    for col in score_cols:
        if col not in df.columns:
            st.error(
                f"Coluna '{col}' faltando no CSV. O notebook 02 precisa ser atualizado.")
            return pd.DataFrame()
        df[col] = df[col].fillna(0)

    return df


df = load_data()
if df.empty:
    st.stop()

# --- 2. SIDEBAR (CONTROLES) ---
st.sidebar.header("⚙️ Ajuste de Pesos")

# Sliders para definir a importância de cada atributo
w_shot = st.sidebar.slider("🧤 Shot Stopping (Defesa)", 0, 100, 70)
w_dist = st.sidebar.slider("👟 Distribuição (Pés)", 0, 100, 15)
w_aerial = st.sidebar.slider("✈️ Controle Aéreo", 0, 100, 15)

# Normaliza os pesos para somar 1.0 (evita notas explosivas)
total_w = w_shot + w_dist + w_aerial
if total_w == 0:
    total_w = 1

pct_shot = w_shot / total_w
pct_dist = w_dist / total_w
pct_aerial = w_aerial / total_w

st.sidebar.divider()

# Filtros
st.sidebar.subheader("Filtros")
min_games = st.sidebar.number_input(
    "Mínimo de Jogos", 1, 38, int(df['Games_Played'].min()))
times = sorted(df['Team'].unique())
selected_teams = st.sidebar.multiselect("Times", times, default=times)

# --- 3. CÁLCULO FINAL (USANDO OS SCORES DO CSV) ---
# Filtra os dados
df_filtered = df[
    (df['Team'].isin(selected_teams)) &
    (df['Games_Played'] >= min_games)
].copy()

# APLICA OS PESOS NOS SCORES JÁ CALCULADOS PELO NOTEBOOK
# Nota: Adicionei o Bônus de Consistência igual ao do notebook (+5 pts max)
max_games = df['Games_Played'].max() if not df.empty else 1
consistency_bonus = (df_filtered['Games_Played'] / max_games) * 5

df_filtered['Novo_Score_Final'] = (
    (df_filtered['Score_Shot_Stopping'] * pct_shot) +
    (df_filtered['Score_Distribution'] * pct_dist) +
    (df_filtered['Score_Aerial'] * pct_aerial)
) + consistency_bonus

# Arredonda e Ordena
df_filtered['Novo_Score_Final'] = df_filtered['Novo_Score_Final'].round(1)
df_filtered = df_filtered.sort_values(
    by='Novo_Score_Final', ascending=False).reset_index(drop=True)
df_filtered.index += 1  # Ranking começa em 1

# --- 4. INTERFACE VISUAL ---
st.title("🏆 Premier League GK Power Ranking")
st.markdown(
    f"**Critério Atual:** Defesa **{pct_shot:.0%}** | Pés **{pct_dist:.0%}** | Aéreo **{pct_aerial:.0%}**")

# Top 3 Destaques
col1, col2, col3 = st.columns(3)
top3 = df_filtered.head(3)

if len(top3) >= 1:
    col1.metric("🥇 1º Lugar", top3.iloc[0]['Player'],
                f"{top3.iloc[0]['Novo_Score_Final']} pts")
if len(top3) >= 2:
    col2.metric("🥈 2º Lugar", top3.iloc[1]['Player'],
                f"{top3.iloc[1]['Novo_Score_Final']} pts")
if len(top3) >= 3:
    col3.metric("🥉 3º Lugar", top3.iloc[2]['Player'],
                f"{top3.iloc[2]['Novo_Score_Final']} pts")

st.divider()

# Tabela e Gráfico
col_tab, col_chart = st.columns([1.5, 1])

with col_tab:
    st.subheader("📋 Classificação")

    # Seleção de colunas para exibir na tabela
    cols_show = ['Player', 'Team', 'Novo_Score_Final', 'Score_Shot_Stopping',
                 'Score_Distribution', 'Score_Aerial', 'Games_Played']

    # Renomear para ficar bonito na tabela
    display_df = df_filtered[cols_show].rename(columns={
        'Novo_Score_Final': 'Score Final',
        'Score_Shot_Stopping': 'Defesa (0-100)',
        'Score_Distribution': 'Pés (0-100)',
        'Score_Aerial': 'Aéreo (0-100)',
        'Games_Played': 'Jogos'
    })

    st.dataframe(
        display_df.style.background_gradient(
            subset=['Score Final'], cmap='Blues'),
        use_container_width=True,
        height=600
    )

with col_chart:
    st.subheader("🎯 Radar de Atributos")

    player_select = st.selectbox(
        "Selecione um Goleiro:", df_filtered['Player'].unique())

    if player_select:
        p_data = df_filtered[df_filtered['Player'] == player_select].iloc[0]

        # Dados para o Radar
        categories = ['Shot Stopping', 'Distribuição', 'Aéreo']
        values = [
            p_data['Score_Shot_Stopping'],
            p_data['Score_Distribution'],
            p_data['Score_Aerial']
        ]

        fig = go.Figure()

        fig.add_trace(go.Scatterpolar(
            r=values,
            theta=categories,
            fill='toself',
            name=p_data['Player'],
            line_color='#00d4ff',
            fillcolor='rgba(0, 212, 255, 0.3)'
        ))

        fig.update_layout(
            polar=dict(
                radialaxis=dict(visible=True, range=[0, 100]),
                angularaxis=dict(tickfont=dict(size=14))
            ),
            margin=dict(l=40, r=40, t=20, b=20),
            showlegend=False
        )

        st.plotly_chart(fig, use_container_width=True)

        st.info(f"""
        **Análise de {player_select}:**
        - Defesa: {p_data['Score_Shot_Stopping']:.1f}
        - Jogo com Pés: {p_data['Score_Distribution']:.1f}
        - Saída Aérea: {p_data['Score_Aerial']:.1f}
        """)
