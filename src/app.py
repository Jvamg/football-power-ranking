import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Configuração da página
st.set_page_config(page_title="GK Ranker - Premier League", layout="wide")

# --- 1. CARGA DE DADOS (Simulação baseada nos seus resultados) ---


@st.cache_data
def load_data():
    # Aqui você carregaria seu CSV gerado pelo script de scraping
    data = {
        'Jogador': ['Robin Roefs', 'Jordan Pickford', 'David Raya', 'Alisson', 'Robert Sánchez'],
        'Time': ['Sunderland', 'Everton', 'Arsenal', 'Liverpool', 'Chelsea'],
        'Defesa (PSxG)': [96, 92, 75, 72, 80],
        'Distribuição': [40, 92, 88, 85, 82],
        'Saída de Área': [30, 75, 90, 80, 88],
        'Concentração': [60, 85, 95, 98, 70],
        'Gols Evitados': [3.1, 1.8, 0.5, 0.4, 0.9]
    }
    return pd.DataFrame(data)


df = load_data()

# --- 2. SIDEBAR (Filtros e Pesos Customizáveis) ---
st.sidebar.header("⚙️ Ajuste os Pesos do Ranking")
w_defesa = st.sidebar.slider("Peso Defesa (Shot Stopping)", 0.0, 1.0, 0.7)
w_dist = st.sidebar.slider("Peso Distribuição", 0.0, 1.0, 0.15)
w_area = st.sidebar.slider("Peso Domínio de Área", 0.0, 1.0, 0.15)

st.sidebar.markdown("---")
st.sidebar.write("Filtrar por Time:")
selected_teams = st.sidebar.multiselect(
    "Times", df['Time'].unique(), default=df['Time'].unique())

# --- 3. LÓGICA DO RANKING (Dinâmico) ---
df_filtered = df[df['Time'].isin(selected_teams)].copy()

# Cálculo do Score Final baseado nos Sliders
df_filtered['Score Final'] = (
    (df_filtered['Defesa (PSxG)'] * w_defesa) +
    (df_filtered['Distribuição'] * w_dist) +
    (df_filtered['Saída de Área'] * w_area)
).round(2)

df_filtered = df_filtered.sort_values(by='Score Final', ascending=False)

# --- 4. INTERFACE PRINCIPAL ---
st.title("🧤 Premier League GK Power Ranking 25/26")
st.markdown(
    f"**Critério Atual:** Defesa ({w_defesa*100}%) | Distribuição ({w_dist*100}%) | Área ({w_area*100}%)")

# Cards de Destaque (Top 3)
cols = st.columns(3)
for i, (idx, row) in enumerate(df_filtered.head(3).iterrows()):
    cols[i].metric(label=f"#{i+1} {row['Jogador']}",
                   value=row['Score Final'], delta=row['Time'])

st.divider()

# Tabela e Gráfico
col_left, col_right = st.columns([1.2, 1])

with col_left:
    st.subheader("📋 Classificação Detalhada")
    st.dataframe(df_filtered[['Jogador', 'Time', 'Score Final', 'Gols Evitados', 'Concentração']],
                 use_container_width=True, hide_index=True)

with col_right:
    st.subheader("🎯 Comparação de Atributos")
    target_player = st.selectbox(
        "Selecione um goleiro para ver o Radar:", df_filtered['Jogador'])

    # Gráfico de Radar usando Plotly
    p_data = df_filtered[df_filtered['Jogador'] == target_player].iloc[0]
    categories = ['Defesa', 'Distribuição', 'Saída de Área', 'Concentração']

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=[p_data['Defesa (PSxG)'], p_data['Distribuição'],
           p_data['Saída de Área'], p_data['Concentração']],
        theta=categories,
        fill='toself',
        name=target_player
    ))
    fig.update_layout(polar=dict(
        radialaxis=dict(visible=True, range=[0, 100])))
    st.plotly_chart(fig, use_container_width=True)
