import streamlit as st
import pandas as pd
import os
import json
from datetime import datetime, timedelta
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
import altair as alt
import hashlib

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
# Usuários autorizados
usuarios = {
    "rodrigo": hashlib.sha256("1234".encode()).hexdigest(),
    "luana": hashlib.sha256("senha123".encode()).hexdigest()
}

def autenticar(usuario, senha):
    senha_hash = hashlib.sha256(senha.encode()).hexdigest()
    return usuario in usuarios and usuarios[usuario] == senha_hash

if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
    st.session_state.usuario = ""

if not st.session_state.autenticado:
    st.title("🔐 Login")
    usuario = st.text_input("Usuário")
    senha = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        if autenticar(usuario, senha):
            st.success("Bem-vindo!")
            st.session_state.autenticado = True
            st.session_state.usuario = usuario
            st.experimental_rerun()
        else:
            st.error("Usuário ou senha incorretos.")
    st.stop()

username = st.session_state.usuario
nome_usuario = username.capitalize()

ARQUIVO_EXCEL = "resumo_ajudante.xlsx"
ARQUIVO_PDF = "recibo_ajudante.pdf"
ARQUIVO_AJUDANTES = "ajudantes.json"
VALOR_DIARIA = 50.0

def carregar_ajudantes():
    if os.path.exists(ARQUIVO_AJUDANTES):
        with open(ARQUIVO_AJUDANTES, "r") as f:
            return json.load(f)
    return ["Cleverson"]

def salvar_ajudantes(lista):
    with open(ARQUIVO_AJUDANTES, "w") as f:
        json.dump(lista, f)

st.sidebar.title("📁 Menu")
ajudantes = carregar_ajudantes()
ajudante_selecionado = st.sidebar.selectbox("👤 Ajudante", ajudantes)

with st.sidebar.expander("➕ Adicionar novo ajudante"):
    novo = st.text_input("Novo ajudante")
    if st.button("Salvar Ajudante"):
        if novo and novo not in ajudantes:
            ajudantes.append(novo)
            salvar_ajudantes(ajudantes)
            st.experimental_rerun()
        elif novo in ajudantes:
            st.warning("Ajudante já existe.")

aba = st.sidebar.radio("Ir para", ["Registrar", "Relatórios", "Recibo"])
st.sidebar.markdown(f"🔐 Logado como: **{nome_usuario}**")

def carregar_dados():
    if os.path.exists(ARQUIVO_EXCEL):
        return pd.read_excel(ARQUIVO_EXCEL, engine="openpyxl")
    return pd.DataFrame(columns=["Usuário", "Ajudante", "Data", "Comparecimento", "Motorista", "Valor (R$)"])

def salvar_dados(df):
    df.to_excel(ARQUIVO_EXCEL, index=False)

if aba == "Registrar":
    st.subheader("📝 Registro de Presença")
    with st.form("registro"):
        col1, col2 = st.columns(2)
        with col1:
            data = st.date_input("Data", value=datetime.today())
        with col2:
            presente = st.checkbox("Compareceu?", value=True)

        motorista = st.selectbox("Motorista", ["Felipe", "Jonas", "Rodrigo"]) if presente else "-"
        salvar = st.form_submit_button("Salvar registro")

        if salvar:
            df = carregar_dados()
            data_str = data.strftime("%d/%m/%Y")
            df = df[~((df["Data"] == data_str) & (df["Ajudante"] == ajudante_selecionado) & (df["Usuário"] == username))]
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
            st.success("Registro salvo!")

if aba == "Relatórios":
    st.subheader("📊 Relatórios e Gráficos")
    df = carregar_dados()
    df = df[(df["Ajudante"] == ajudante_selecionado) & (df["Usuário"] == username)]

    if df.empty:
        st.warning("Nenhum registro encontrado.")
    else:
        df["Data_ord"] = pd.to_datetime(df["Data"], dayfirst=True)
        data_ini = st.date_input("Início", value=datetime.today().replace(day=1))
        data_fim = st.date_input("Fim", value=datetime.today())
        df_filtrado = df[(df["Data_ord"] >= pd.to_datetime(data_ini)) & (df["Data_ord"] <= pd.to_datetime(data_fim))]

        if df_filtrado.empty:
            st.info("Sem dados no período.")
        else:
            st.write(f"**Dias trabalhados:** {df_filtrado[df_filtrado['Comparecimento'] == 'Presente'].shape[0]}")
            st.dataframe(df_filtrado)

            chart = alt.Chart(df_filtrado[df_filtrado["Comparecimento"] == "Presente"]).mark_bar().encode(
                x=alt.X("Motorista", sort="-y"),
                y="count()"
            )
            st.altair_chart(chart)

            linha = df_filtrado.groupby("Data_ord")["Comparecimento"].apply(lambda x: (x == "Presente").sum()).reset_index(name="Presenças")
            st.altair_chart(alt.Chart(linha).mark_line(point=True).encode(
                x="Data_ord:T", y="Presenças"
            ))
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
    c.drawString(x + 200, y, f"Total: R$ {total:.2f}".replace('.', ','))
    y -= 50
    c.setFont("Helvetica", 11)
    c.drawString(x, y, "Assinatura: _________________________")
    y -= 20
    c.drawString(x, y
