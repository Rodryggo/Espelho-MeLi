import streamlit as st
import pandas as pd
import os
import json
from datetime import datetime, timedelta
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
import streamlit_authenticator as stauth
import altair as alt

# Estilo escuro
st.set_page_config(page_title="Controle de Presença - Ajudante", layout="centered")
st.markdown("""
    <style>
        body { background-color: #1e1e1e; color: #f2f2f2; }
        .stApp { background-color: #1e1e1e; color: #f2f2f2; }
        .stButton>button, .stDownloadButton>button {
            background-color: #4CAF50; color: white; border: none; border-radius: 6px;
            padding: 8px 16px; font-size: 16px;
        }
        .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 { color: #ffffff; }
    </style>
""", unsafe_allow_html=True)

# Arquivos e constantes
VALOR_DIARIA = 50.0
ARQUIVO_EXCEL = "resumo_ajudante.xlsx"
ARQUIVO_PDF = "recibo_ajudante.pdf"
ARQUIVO_AJUDANTES = "ajudantes.json"

# Carregar ou salvar lista de ajudantes
def carregar_ajudantes():
    if os.path.exists(ARQUIVO_AJUDANTES):
        with open(ARQUIVO_AJUDANTES, "r") as f:
            return json.load(f)
    return ["Cleverson"]

def salvar_ajudantes(lista):
    with open(ARQUIVO_AJUDANTES, "w") as f:
        json.dump(lista, f)

# Login com múltiplos usuários
nomes = ["Rodrigo", "Luana"]
usuarios = ["rodrigo", "luana"]
senhas_hash = stauth.Hasher(["1234", "senha123"]).generate()

auth = stauth.Authenticate(nomes, usuarios, senhas_hash, "app_ajudante_login", "abcdef", cookie_expiry_days=30)
nome_usuario, autenticado, username = auth.login("Login", "main")
if not autenticado:
    st.stop()
# Menu lateral e seleção de ajudante
st.sidebar.title("📁 Menu")

# Carregar ajudantes
ajudantes = carregar_ajudantes()

# Seletor de ajudante
ajudante_selecionado = st.sidebar.selectbox("👤 Ajudante", ajudantes)

# Adicionar novo ajudante
with st.sidebar.expander("➕ Adicionar novo ajudante"):
    novo_ajudante = st.text_input("Novo nome")
    if st.button("Salvar Ajudante"):
        if novo_ajudante and novo_ajudante not in ajudantes:
            ajudantes.append(novo_ajudante)
            salvar_ajudantes(ajudantes)
            st.success(f"{novo_ajudante} adicionado!")
            st.experimental_rerun()
        elif novo_ajudante in ajudantes:
            st.warning("Ajudante já existe.")

# Menu de abas
aba = st.sidebar.radio("Navegação", ["Início", "Registrar", "Relatórios", "Recibo"])
st.sidebar.markdown(f"🔐 Logado como **{nome_usuario}**")
# Funções para carregar e salvar dados
def carregar_dados():
    if os.path.exists(ARQUIVO_EXCEL):
        return pd.read_excel(ARQUIVO_EXCEL, engine="openpyxl")
    return pd.DataFrame(columns=["Usuário", "Ajudante", "Data", "Comparecimento", "Motorista", "Valor (R$)"])

def salvar_dados(df):
    df.to_excel(ARQUIVO_EXCEL, index=False)

# Página: Registrar
if aba == "Registrar":
    st.subheader("📝 Registro de Presença")

    with st.form("registro_form"):
        col1, col2 = st.columns(2)
        with col1:
            data = st.date_input("Data", value=datetime.today())
        with col2:
            presente = st.checkbox("Compareceu?", value=True)

        motorista = st.selectbox("Motorista", ["Felipe", "Jonas", "Rodrigo"]) if presente else "-"

        enviar = st.form_submit_button("Salvar Registro")
        if enviar:
            df = carregar_dados()
            data_str = data.strftime("%d/%m/%Y")
            df = df[~((df["Data"] == data_str) & (df["Ajudante"] == ajudante_selecionado))]  # Evita duplicatas

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
    st.subheader("📈 Relatórios e Gráficos")
    df_dados = carregar_dados()
    df_dados = df_dados[df_dados["Ajudante"] == ajudante_selecionado]
    df_dados = df_dados[df_dados["Usuário"] == username]
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
            st.warning("Nenhum registro no intervalo selecionado.")
        else:
            st.markdown(f"Total de dias trabalhados: **{df_filtrado[df_filtrado['Comparecimento']=='Presente'].shape[0]}**")
            
            with st.expander("📄 Visualizar registros"):
                st.dataframe(df_filtrado.reset_index(drop=True), use_container_width=True)

            st.markdown("#### 📊 Presenças por motorista")
            pres_motorista = df_filtrado[df_filtrado["Comparecimento"] == "Presente"]["Motorista"].value_counts().reset_index()
            pres_motorista.columns = ["Motorista", "Presenças"]
            chart = alt.Chart(pres_motorista).mark_bar().encode(
                x=alt.X("Motorista", sort="-y"),
                y="Presenças",
                tooltip=["Motorista", "Presenças"]
            ).properties(width=500, height=300)
            st.altair_chart(chart)

            st.markdown("#### 📅 Linha do tempo")
            linha = df_filtrado.groupby("Data_ord")["Comparecimento"].apply(lambda x: (x=="Presente").sum()).reset_index(name="Presenças")
            st.altair_chart(alt.Chart(linha).mark_line(point=True).encode(
                x="Data_ord:T",
                y="Presenças"
            ).properties(width=500, height=300))
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
        st.info("Nenhum registro de presença para este ajudante.")
    else:
        opcao = st.radio("Período", ["Últimos 15 dias", "Mês atual", "Personalizado"])
        hoje = datetime.today()

        if "15 dias" in opcao:
            inicio, fim = hoje - timedelta(days=15), hoje
        elif "Mês" in opcao:
            inicio, fim = hoje.replace(day=1), hoje
        else:
            col1, col2 = st.columns(2)
            with col1: inicio = st.date_input("Início")
            with col2: fim = st.date_input("Fim")

        df_filtrado = df_presenca[
            (df_presenca["Data_ord"] >= pd.to_datetime(inicio)) &
            (df_presenca["Data_ord"] <= pd.to_datetime(fim))
        ]

        if df_filtrado.empty:
            st.warning("Nenhum dado no período selecionado.")
        else:
            if st.button("📄 Gerar e Baixar Recibo"):
                pdf = gerar_recibo(df_filtrado, inicio.strftime('%d/%m/%Y'), fim.strftime('%d/%m/%Y'))
                with open(pdf, "rb") as f:
                    st.download_button("📥 Baixar Recibo PDF", f, file_name=ARQUIVO_PDF)

            st.download_button("📤 Exportar Excel", df_filtrado.to_excel(index=False, engine="openpyxl"), file_name="dias_trabalhados.xlsx")

            if st.button("🧹 Iniciar Nova Quinzena"):
                df_antigo = carregar_dados()
                df_novo = df_antigo[~((df_antigo["Ajudante"] == ajudante_selecionado) & (df_antigo["Usuário"] == username))]
                salvar_dados(df_novo)
                st.success("Registros do ajudante apagados com sucesso.")
