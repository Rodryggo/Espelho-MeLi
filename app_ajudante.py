import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

AJUDANTE = "Cleverson"
VALOR_DIARIA = 50.00
ARQUIVO_EXCEL = "resumo_quinzena.xlsx"
ARQUIVO_PDF = "recibo_cleverson.pdf"

st.set_page_config(page_title="Controle de Presença - Cleverson", layout="centered")
st.title("📋 Controle de Presença - Cleverson")

def carregar_dados():
    if os.path.exists(ARQUIVO_EXCEL):
        return pd.read_excel(ARQUIVO_EXCEL, engine="openpyxl")
    return pd.DataFrame(columns=["Data", "Comparecimento", "Motorista", "Valor (R$)"])

def salvar_dados(df):
    df.to_excel(ARQUIVO_EXCEL, index=False)

def gerar_recibo(df, inicio, fim):
    c = canvas.Canvas(ARQUIVO_PDF, pagesize=A4)
    largura, altura = A4
    x, y = 50, altura - 50

    c.setFont("Helvetica-Bold", 14)
    c.drawString(x, y, "RECIBO DE DIÁRIAS - CLEVerson")
    y -= 20
    c.setFont("Helvetica", 12)
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

    y -= 60
    c.setFont("Helvetica", 11)
    c.drawString(x, y, "Assinatura: ___________________________")
    y -= 20
    c.drawString(x, y, f"Data de Emissão: {datetime.today().strftime('%d/%m/%Y')}")
    c.save()
    return ARQUIVO_PDF

# Formulário de registro
with st.form("registro_form"):
    col1, col2 = st.columns(2)
    with col1:
        data = st.date_input("Data do Trabalho", value=datetime.today())
    with col2:
        compareceu = st.checkbox("Compareceu?", value=True)

    motorista = st.selectbox("Motorista", ["Felipe", "Jonas", "Rodrigo"]) if compareceu else "-"

    enviado = st.form_submit_button("Salvar Registro")
    if enviado:
        df = carregar_dados()
        data_str = data.strftime("%d/%m/%Y")
        df = df[df["Data"] != data_str]  # Evita duplicatas

        novo = pd.DataFrame([{
            "Data": data_str,
            "Comparecimento": "Presente" if compareceu else "Ausente",
            "Motorista": motorista,
            "Valor (R$)": VALOR_DIARIA if compareceu else 0.0
        }])

        df = pd.concat([df, novo], ignore_index=True).sort_values("Data")
        salvar_dados(df)
        st.success(f"Registro salvo para {data_str}.")
# Resumo e exibição de registros
df_dados = carregar_dados()
presencas = df_dados[df_dados["Comparecimento"] == "Presente"]
faltas = df_dados[df_dados["Comparecimento"] == "Ausente"]
total = presencas["Valor (R$)"].sum()

st.markdown("### 📊 Resumo Atual")
st.info(f"Dias Trabalhados: {presencas.shape[0]} | Faltas: {faltas.shape[0]} | Total: R$ {total:.2f}".replace('.', ','))

with st.expander("📅 Últimos registros"):
    st.dataframe(df_dados.sort_values("Data", ascending=False).reset_index(drop=True), use_container_width=True)

# Ações adicionais
col1, col2 = st.columns(2)
with col1:
    if st.button("🧹 Nova Quinzena"):
        if os.path.exists(ARQUIVO_EXCEL):
            os.remove(ARQUIVO_EXCEL)
            st.success("Registros apagados. Nova quinzena iniciada.")

with col2:
    if not presencas.empty:
        presencas.sort_values("Data").to_excel("dias_trabalhados.xlsx", index=False)
        with open("dias_trabalhados.xlsx", "rb") as f:
            st.download_button("📤 Baixar Dias Trabalhados", f, file_name="dias_trabalhados.xlsx")

st.markdown("---")

# Geração de Recibo
if not presencas.empty:
    st.subheader("🖨️ Gerar Recibo PDF")
    opcao = st.radio("Período do recibo:", ["Últimos 15 dias (Quinzena)", "Mês atual"], horizontal=True)
    hoje = datetime.today()
    inicio = hoje - timedelta(days=15) if "15 dias" in opcao else hoje.replace(day=1)
    fim = hoje

    df_periodo = presencas.copy()
    df_periodo["Data_ord"] = pd.to_datetime(df_periodo["Data"], dayfirst=True)
    df_filtrado = df_periodo[(df_periodo["Data_ord"] >= inicio) & (df_periodo["Data_ord"] <= fim)]

    if df_filtrado.empty:
        st.warning("Nenhum registro presente no período escolhido.")
    else:
        if st.button("📄 Gerar e Baixar Recibo"):
            pdf = gerar_recibo(df_filtrado, inicio.strftime('%d/%m/%Y'), fim.strftime('%d/%m/%Y'))
            with open(pdf, "rb") as f:
                st.download_button("📥 Baixar Recibo PDF", f, file_name=ARQUIVO_PDF)
