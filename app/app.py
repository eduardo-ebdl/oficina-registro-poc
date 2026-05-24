import os
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

# Carrega .env antes de qualquer leitura de os.getenv
load_dotenv(Path(__file__).parent.parent / ".env")

# Garante que as importações locais funcionem independente do diretório de execução
sys.path.insert(0, str(Path(__file__).parent))
from database import get_all_ordens, get_next_ordem_id, init_db, insert_ordem
from s3_utils import upload_file_to_s3

EXPORT_PATH = Path(__file__).parent.parent / "data" / "ordens_servico_export.csv"

SERVICOS = [
    "Troca de óleo",
    "Revisão completa",
    "Alinhamento e balanceamento",
    "Troca de freios",
    "Suspensão",
    "Elétrica",
    "Ar-condicionado",
    "Câmbio",
    "Motor",
    "Funilaria e pintura",
    "Outro",
]
STATUS_OPTIONS  = ["Aberto", "Em andamento", "Aguardando peça", "Concluído", "Cancelado"]
PAGAMENTO_OPTIONS = ["Dinheiro", "Cartão débito", "Cartão crédito", "Pix", "Pendente"]

# ── Configuração da página ─────────────────────────────────────────────────────
st.set_page_config(
    layout="wide",
    page_title="PoC - OS Registro",
    page_icon="🔧",
)

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&display=swap');

/* Sidebar */
section[data-testid="stSidebar"] {
    border-right: 1px solid #333;
    padding-top: 1.25rem;
}

/* Headers estilizados */
.section-header {
    font-family: 'Bebas Neue', monospace;
    font-size: 2rem;
    letter-spacing: 0.05em;
    margin-bottom: 0.25rem;
    color: #F0EDE8;
}
.sub-header {
    font-family: 'Bebas Neue', monospace;
    font-size: 1.4rem;
    letter-spacing: 0.05em;
    color: #E8370D;
    margin-top: 1rem;
}

/* Metric cards */
[data-testid="metric-container"] {
    border: 1px solid #444;
    padding: 0.75rem 1rem;
    background-color: #1A1A1A;
}

/* Botões */
.stButton > button {
    text-transform: uppercase;
    letter-spacing: 0.1em;
    border-radius: 0 !important;
    border: 1px solid #E8370D !important;
    color: #E8370D !important;
    background: transparent !important;
    font-weight: bold;
    transition: all 0.15s ease;
}
.stButton > button:hover {
    background: #E8370D !important;
    color: #0F0F0F !important;
}

/* Download button herda o mesmo estilo */
.stDownloadButton > button {
    text-transform: uppercase;
    letter-spacing: 0.1em;
    border-radius: 0 !important;
    border: 1px solid #E8370D !important;
    color: #E8370D !important;
    background: transparent !important;
    font-weight: bold;
}
.stDownloadButton > button:hover {
    background: #E8370D !important;
    color: #0F0F0F !important;
}

/* Inputs */
.stTextInput input,
.stNumberInput input,
.stTextArea textarea {
    background-color: #1A1A1A !important;
    border: 1px solid #444 !important;
    color: #F0EDE8 !important;
}

/* Tabela compacta */
.stDataFrame { font-size: 0.85rem; }
</style>
""",
    unsafe_allow_html=True,
)

# ── Inicialização do banco ─────────────────────────────────────────────────────
if "conn" not in st.session_state:
    st.session_state.conn = init_db()

conn = st.session_state.conn

# ── Sidebar ────────────────────────────────────────────────────────────────────
st.sidebar.markdown('<div class="section-header">🔧 OFICINA</div>', unsafe_allow_html=True)
st.sidebar.divider()
page = st.sidebar.radio(
    "nav",
    ["Cadastrar Ordem", "Consultar Registros", "Exportar / S3"],
    label_visibility="collapsed",
)

# ══════════════════════════════════════════════════════════════════════════════
# PÁGINA 1 — CADASTRAR ORDEM
# ══════════════════════════════════════════════════════════════════════════════
if page == "Cadastrar Ordem":
    st.markdown('<div class="section-header">NOVA ORDEM DE SERVIÇO</div>', unsafe_allow_html=True)

    with st.form("ordem_form"):
        # Linha 1 — Cliente
        c1, c2, c3 = st.columns([3, 2, 2])
        cliente_nome = c1.text_input("Cliente *", placeholder="Nome completo")
        telefone     = c2.text_input("Telefone", placeholder="(11) 99999-9999")
        documento    = c3.text_input("CPF/CNPJ (opcional)", placeholder="000.000.000-00")

        # Linha 2 — Veículo
        c1, c2, c3, c4 = st.columns([2, 2, 2, 1])
        placa          = c1.text_input("Placa *", placeholder="ABC1234")
        marca_veiculo  = c2.text_input("Marca", placeholder="Toyota")
        modelo_veiculo = c3.text_input("Modelo", placeholder="Corolla")
        ano_veiculo    = c4.number_input("Ano", min_value=1900, max_value=2100, value=2020, step=1)

        # Linha 3 — Serviço
        c1, c2, c3, c4 = st.columns(4)
        mecanico  = c1.text_input("Mecânico", placeholder="Responsável")
        servico   = c2.selectbox("Serviço *", SERVICOS)
        status    = c3.selectbox("Status", STATUS_OPTIONS)
        pagamento = c4.selectbox("Pagamento", PAGAMENTO_OPTIONS)

        # Linha 4 — Valores
        c1, c2, c3 = st.columns([3, 2, 2])
        peca_utilizada = c1.text_input("Peça utilizada (opcional)", placeholder="Ex: Filtro de óleo")
        valor_servico  = c2.number_input("Valor serviço (R$)", min_value=0.0, step=0.01, format="%.2f")
        valor_peca     = c3.number_input("Valor peça (R$)",    min_value=0.0, step=0.01, format="%.2f")

        # Linha 5 — Datas
        c1, c2 = st.columns(2)
        data_entrada   = c1.date_input("Data de entrada", value=date.today())
        data_saida_raw = c2.date_input("Data de saída (opcional)", value=None)

        # Linha 6 — Observações
        observacoes = st.text_area("Observações", placeholder="Informações adicionais sobre o serviço...")

        submitted = st.form_submit_button("REGISTRAR ORDEM", use_container_width=True)

    if submitted:
        errors: list[str] = []
        if not cliente_nome.strip():
            errors.append("Nome do cliente é obrigatório.")
        if not placa.strip():
            errors.append("Placa é obrigatória.")
        if data_saida_raw is not None and data_saida_raw < data_entrada:
            errors.append("Data de saída não pode ser anterior à data de entrada.")

        if errors:
            for err in errors:
                st.error(err)
        else:
            ordem_id    = get_next_ordem_id(conn)
            valor_total = valor_servico + valor_peca

            record = {
                "ordem_id":       ordem_id,
                "cliente_nome":   cliente_nome.strip(),
                "telefone":       telefone.strip() or None,
                "documento":      documento.strip() or None,
                "placa":          placa.strip().upper(),
                "marca_veiculo":  marca_veiculo.strip() or None,
                "modelo_veiculo": modelo_veiculo.strip() or None,
                "ano_veiculo":    int(ano_veiculo),
                "mecanico":       mecanico.strip() or None,
                "servico":        servico,
                "peca_utilizada": peca_utilizada.strip() or None,
                "valor_servico":  valor_servico,
                "valor_peca":     valor_peca,
                "valor_total":    valor_total,
                "status":         status,
                "pagamento":      pagamento,
                "data_entrada":   data_entrada.isoformat(),
                "data_saida":     data_saida_raw.isoformat() if data_saida_raw else None,
                "observacoes":    observacoes.strip() or None,
                "created_at":     pd.Timestamp.now().isoformat(),
            }

            if insert_ordem(conn, record):
                st.success(f"Ordem **{ordem_id}** registrada com sucesso!")
            else:
                st.error("Erro ao registrar a ordem. Verifique os dados e tente novamente.")

# ══════════════════════════════════════════════════════════════════════════════
# PÁGINA 2 — CONSULTAR REGISTROS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Consultar Registros":
    st.markdown('<div class="section-header">CONSULTA DE ORDENS</div>', unsafe_allow_html=True)

    df = get_all_ordens(conn)

    if df.empty:
        st.info("Nenhuma ordem registrada ainda.")
        st.stop()

    total     = len(df)
    receita   = df["valor_total"].fillna(0).sum()
    ticket    = receita / total if total else 0.0
    em_aberto = int((df["status"] == "Aberto").sum())

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total de Ordens",  total)
    c2.metric("Receita Total",    f"R$ {receita:,.2f}")
    c3.metric("Ticket Médio",     f"R$ {ticket:,.2f}")
    c4.metric("Ordens em Aberto", em_aberto)

    st.divider()

    fc1, fc2, fc3 = st.columns([2, 2, 3])
    status_f  = fc1.selectbox("Filtrar por status",  ["Todos"] + STATUS_OPTIONS)
    servico_f = fc2.selectbox("Filtrar por serviço", ["Todos"] + SERVICOS)
    search    = fc3.text_input("Buscar por placa ou cliente", placeholder="ABC1234 ou João Silva")

    filtered = df.copy()
    if status_f != "Todos":
        filtered = filtered[filtered["status"] == status_f]
    if servico_f != "Todos":
        filtered = filtered[filtered["servico"] == servico_f]
    if search.strip():
        q    = search.strip().lower()
        mask = filtered["placa"].str.lower().str.contains(q, na=False) | \
               filtered["cliente_nome"].str.lower().str.contains(q, na=False)
        filtered = filtered[mask]

    st.markdown(f"**{len(filtered)} resultado(s)**")
    st.dataframe(filtered, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# PÁGINA 3 — EXPORTAR / S3
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Exportar / S3":
    st.markdown('<div class="section-header">EXPORTAR DADOS</div>', unsafe_allow_html=True)

    df        = get_all_ordens(conn)
    csv_bytes = df.to_csv(index=False).encode("utf-8")

    st.markdown(f"**{len(df)} registro(s) disponíveis para exportação.**")

    if st.download_button(
        label="BAIXAR CSV",
        data=csv_bytes,
        file_name="ordens_servico_export.csv",
        mime="text/csv",
    ):
        # Salva cópia local junto com o download
        EXPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        EXPORT_PATH.write_bytes(csv_bytes)

    st.divider()
    st.markdown('<div class="sub-header">ENVIO PARA S3</div>', unsafe_allow_html=True)

    bucket     = os.getenv("BUCKET_RAW", "")
    region     = os.getenv("AWS_REGION", "")
    key_id     = os.getenv("AWS_ACCESS_KEY_ID", "")
    secret     = os.getenv("AWS_SECRET_ACCESS_KEY", "")

    def _mask(val: str) -> str:
        return f"****{val[-4:]}" if len(val) >= 4 else "(não configurado)"

    st.info(
        f"**BUCKET_RAW:** `{bucket or '(não configurado)'}`  \n"
        f"**AWS_REGION:** `{region or '(não configurado)'}`  \n"
        f"**AWS_ACCESS_KEY_ID:** `{_mask(key_id)}`  \n"
        f"**AWS_SECRET_ACCESS_KEY:** `{_mask(secret)}`"
    )

    if st.button("ENVIAR PARA S3"):
        EXPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        EXPORT_PATH.write_bytes(csv_bytes)
        success, message = upload_file_to_s3(str(EXPORT_PATH))
        if success:
            st.success(message)
        else:
            st.error(message)
