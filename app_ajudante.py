import streamlit as st
import pandas as pd
import os
import json
from datetime import datetime, timedelta
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
import altair as alt
import streamlit_authenticator as stauth

# Estilo e layout
st.set_page_config(page_title="Controle de Presença - Ajudante", layout="centered")
st.markdown("""
    <style>
        body, .stApp { background-color: #1e1e1e; color: #f2f2f2; }
        .stButton>button, .stDownloadButton>button {
            background-color: #4CAF50; color: white;
            border: none; border-radius: 6px; padding: 8px 16px; font-size: 16px;
        }
        .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 { color: white; }
    </style>
""", unsafe_allow_html=True)

# Arquivos base
ARQUIVO_EXCEL = "resumo_ajudante.xlsx"
ARQUIVO_PDF = "recibo_ajudante.pdf"
ARQUIVO_AJUDANTES = "ajudantes.json"
VALOR_DIARIA = 50.0

# Login com hash de senha
nomes = ["Rodrigo", "Luana"]
usuarios = ["rodrigo", "luana"]
hashed_pw = [
    "$2b$12$tr3sZ6UJ4EFmvM0QH0IGme5KUg8VcMCur6ggWrKtToMkUue1e1Hba",  # 1234
    "$2b$12$AhPR.DGKfdM6UzI8IRW6m.F/zUV7ZzK3gP1Go9uLRsLyvvqnmVkZ2"   # senha123
]

authenticator = stauth.Authenticate(
    nomes,
    usuarios,
    hashed_pw,
    "app_ajudante_login",
    "cleverson_app",
    cookie_expiry_days=30
)

nome_usuario, autenticado, username = authenticator.login("Login", "main")
if not autenticado:
    st.stop()
# Funções de ajudantes
def carregar_ajudantes():
    if os.path.exists(ARQUIVO_AJUDANTES):
        with open(ARQUIVO_AJUDANTES, "r") as f:
            return json.load(f)
    return ["Cleverson"]

def salvar_ajudantes(lista):
    with open(ARQUIVO_AJUDANTES, "w") as f:
        json.dump(lista, f)

# Menu lateral
st.sidebar.title("📁 Menu")
ajudantes = carregar_ajudantes()
ajudante_selecionado = st.sidebar.selectbox("👤 Ajudante", ajudantes)

# Novo ajudante
with st.sidebar.expander("➕ Adicionar novo ajudante"):
    novo_ajudante = st.text_input("Nome do novo ajudante")
    if st.button("Salvar Ajudante"):
        if novo_ajudante and novo_ajudante not in ajudantes:
            ajudantes.append(novo_ajudante)
            salvar_ajudantes(ajudantes)
            st.success(f"{novo_ajudante} adicionado com sucesso!")
            st.experimental_rerun()
        elif novo_ajudante in ajudantes:
            st.warning("Ajudante já existe.")
        else:
            st.warning("Informe um nome válido.")

# Navegação entre páginas
aba = st.sidebar.radio("Ir para", ["Início", "Registrar", "Relatórios", "Recibo"])
st.sidebar.markdown(f"🔐 Logado como: **{nome_usuario}**")
# Funções para carregar e salvar presença
def carregar_dados():
    if os.path.exists(ARQUIVO_EXCEL):
        return pd.read_excel(ARQUIVO_EXCEL, engine="openpyxl")
    return pd.DataFrame(columns=["Usuário", "Ajudante", "Data", "Comparecimento", "Motorista", "Valor (R$)"])

def salvar_dados(df):
    df.to_excel(ARQUIVO_EXCEL, index=False)

# Página: Registrar
if aba == "Registrar":
    st.subheader("📝 Registro de Presença")

    with st.form("registro_presenca_form"):
        col1, col2 = st.columns(2)
        with col1:
            data = st.date_input("Data", value=datetime.today())
        with col2:
            presente = st.checkbox("Compareceu?", value=True)

        motorista = st.selectbox("Motorista", ["Felipe", "Jonas", "Rodrigo"]) if presente else "-"

        enviar = st.form_submit_button("Salvar registro")

        if enviar:
            df = carregar_dados()
            data_str = data.strftime("%d/%m/%Y")

            # Remove registro duplicado para o mesmo ajudante e dia
            df = df[~((df["Data"] == data_str) & 
                      (df["Ajudante"] == ajudante_selecionado) & 
                      (df["Usuário"] == username))]

            novo = pd.DataFrame([{
                "Usuário": username,
                "Ajudante": ajudante_selecionado,
                "Data": data_str,
                "Comparecimento": "Presente" if presente else "Ausente",
                "Motorista": motorista,
                "Valor (R$)": VALOR_DIARIA if presente else 0.0
            }])

            df = pd.concat([df, novo], ignore_index=True).sort_values("Data")
            salvar_dados(df)
            st.success(f"Registro salvo para {data_str}.")
if aba == "Relatórios":
    st.subheader("📊 Relatórios e Gráficos")
    df_dados = carregar_dados()
    df_dados = df_dados[(df_dados["Ajudante"] == ajudante_selecionado) & 
                        (df_dados["Usuário"] == username)]

    if df_dados.empty:
        st.warning("Nenhum dado encontrado para este ajudante.")
    else:
        df_dados["Data_ord"] = pd.to_datetime(df_dados["Data"], dayfirst=True)

        st.markdown("#### 🔎 Filtro por período")
        col1, col2 = st.columns(2)
        with col1:
            data_ini = st.date_input("Início", value=datetime.today().replace(day=1))
        with col2:
            data_fim = st.date_input("Fim", value=datetime.today())

        df_filtrado = df_dados[(df_dados["Data_ord"] >= pd.to_datetime(data_ini)) &
                               (df_dados["Data_ord"] <= pd.to_datetime(data_fim))]

        if df_filtrado.empty:
            st.info("Nenhum registro no intervalo selecionado.")
        else:
            total_dias = df_filtrado[df_filtrado["Comparecimento"] == "Presente"].shape[0]
            st.markdown(f"**Total de dias trabalhados:** {total_dias}")

            with st.expander("📄 Ver dados filtrados"):
                st.dataframe(df_filtrado.reset_index(drop=True), use_container_width=True)

            st.markdown("#### 🚐 Presenças por Motorista")
            pres_motorista = df_filtrado[df_filtrado["Comparecimento"] == "Presente"]["Motorista"].value_counts().reset_index()
            pres_motorista.columns = ["Motorista", "Presenças"]

            chart_barra = alt.Chart(pres_motorista).mark_bar().encode(
                x=alt.X("Motorista", sort="-y"),
                y="Presenças",
                tooltip=["Motorista", "Presenças"]
            ).properties(width=500, height=300)
            st.altair_chart(chart_barra)

            st.markdown("#### 🗓️ Linha do tempo de Presença")
            linha = df_filtrado.groupby("Data_ord")["Comparecimento"].apply(
                lambda x: (x == "Presente").sum()).reset_index(name="Presenças")

            chart_linha = alt.Chart(linha).mark_line(point=True).encode(
                x="Data_ord:T",
                y="Presenças"
            ).properties(width=500, height=300)
            st.altair_chart(chart_linha)

            st.markdown("#### 🍕 Presente vs Ausente")
            contagem = df_filtrado["Comparecimento"].value_counts().reset_index()
            contagem.columns = ["Status", "Quantidade"]

            st.pyplot(contagem.set_index("Status").plot.pie(
                y="Quantidade", autopct='%1.1f%%', ylabel="", figsize=(4, 4)).figure)
# Função de gerar recibo PDF
def gerar_recibo(df, inicio, fim):
    c = canvas.Canvas(ARQUIVO_PDF, pagesize=A4)
    largura, altura = A4
    x, y = 50, altura - 50

    c.setFont("Helvetica-Bold", 14)
    c.drawString(x, y, "RECIBO DE DIÁRIAS - AJUDANTE")
    y -= 25
    c.setFont("Helvetica", 12)
    c.drawString(x, y, f"Ajudante: {ajudante_selecionado}")
    y -= 20
    c.drawString(x, y, f"Período: {inicio} a {fim}")
    y -= 30

    c.setFont("Helvetica-Bold", 11)
    c.drawString(x, y, "Data")
    c.drawString(x + 100, y, "Motorista")
    c.drawString(x + 220, y, "Valor (R$)")
    y -= 15
    c.setFont("Helvetica", 11)

    total = 0
    for _, row in df.iterrows():
        if y < 100:
            c.showPage()
            y = altura - 50
        c.drawString(x, y, row["Data"])
        c.drawString(x + 100, y, row["Motorista"])
        c.drawString(x + 220, y, f"{row['Valor (R$)']:.2f}".replace('.', ','))
        total += row["Valor (R$)"]
        y -= 15

    y -= 30
    c.setFont("Helvetica-Bold", 12)
    c.drawString(x, y, f"Total de Diárias: {df.shape[0]}")
    c.drawString(x + 200, y, f"Total a Receber: R$ {total:.2f}".replace('.', ','))

    y -= 50
    c.setFont("Helvetica", 11)
    c.drawString(x, y, "Assinatura: ___________________________")
    y -= 20
    c.drawString(x, y, f"Data de Emissão: {datetime.today().strftime('%d/%m/%Y')}")
    c.save()
    return ARQUIVO_PDF
# Página: Recibo
if aba == "Recibo":
    st.subheader("🧾 Gerar Recibo PDF")
    df = carregar_dados()
    df = df[(df["Ajudante"] == ajudante_selecionado) & (df["Usuário"] == username)]
    df["Data_ord"] = pd.to_datetime(df["Data"], dayfirst=True)
    df_presenca = df[df["Comparecimento"] == "Presente"]

    if df_presenca.empty:
        st.info("Nenhum registro de presença encontrado.")
    else:
        periodo = st.radio("Escolha o período:", ["Últimos 15 dias", "Mês atual", "Personalizado"])
        hoje = datetime.today()
        if periodo == "Últimos 15 dias":
            ini, fim = hoje - timedelta(days=15), hoje
        elif periodo == "Mês atual":
            ini, fim = hoje.replace(day=1), hoje
        else:
            col1, col2 = st.columns(2)
            with col1: ini = st.date_input("Início")
            with col2: fim = st.date_input("Fim")

        df_filtro = df_presenca[(df_presenca["Data_ord"] >= pd.to_datetime(ini)) &
                                (df_presenca["Data_ord"] <= pd.to_datetime(fim))]

        if df_filtro.empty:
            st.warning("Nenhum registro no intervalo escolhido.")
        else:
            if st.button("📄 Gerar Recibo"):
                gerar_recibo(df_filtro, ini.strftime("%d/%m/%Y"), fim.strftime("%d/%m/%Y"))
                with open(ARQUIVO_PDF, "rb") as f:
                    st.download_button("📥 Baixar Recibo PDF", f, file_name=ARQUIVO_PDF)

            st.download_button("📊 Exportar Excel",
                               df_filtro.to_excel(index=False, engine="openpyxl"),
                               file_name="dias_trabalhados.xlsx")

            if st.button("🧹 Iniciar Nova Quinzena"):
                df_antigo = carregar_dados()
                df_novo = df_antigo[~((df_antigo["Ajudante"] == ajudante_selecionado) &
                                      (df_antigo["Usuário"] == username))]
                salvar_dados(df_novo)
                st.success("Registros do ajudante apagados com sucesso.")
