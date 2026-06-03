from __future__ import annotations
import sqlite3
from datetime import date
import re
from pathlib import Path
from database import export_ordens_to_csv, fetch_ordens, init_db, insert_ordem
from ml_utils import predict_valor_total
from s3_utils import upload_file_to_s3
from spark_utils import run_spark_curated_pipeline
import pandas as pd
import streamlit as st
import altair as alt


def format_currency(value: float) -> str:
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


CSS_FILE = Path(__file__).with_name("styles.css")

TIPOS_SERVICO = [
    "Troca de óleo", "Revisão completa", "Alinhamento e balanceamento", "Troca de freios", "Suspensão",
    "Elétrica", "Ar-condicionado", "Câmbio", "Motor", "Funilaria e pintura", "Outro",
]

STATUS = [
    "Aberto", "Em andamento", "Aguardando peça",
    "Concluído", "Cancelado",
]

FORMAS_PAGAMENTO = [
    "Dinheiro", "Cartão débito", "Cartão crédito",
    "Pix", "Pendente",
]

STATUS_ABERTO = {"Aberto", "Em andamento", "Aguardando peça"}

EMPTY_ORDENS_COLUMNS = [
    "id", "ordem_id", "cliente_nome", "telefone", "documento", "placa", "marca_veiculo", "modelo_veiculo",
    "ano_veiculo", "mecanico", "servico", "peca_utilizada", "valor_servico", "valor_peca", "valor_total",
    "status", "pagamento", "data_entrada", "data_saida", "observacoes", "created_at",
]

FORM_DEFAULTS: dict[str, object] = {
    "form_cliente_nome": "",
    "form_telefone": "",
    "form_documento": "",
    "form_placa": "",
    "form_marca_veiculo": "",
    "form_modelo_veiculo": "",
    "form_ano_veiculo": date.today().year,
    "form_mecanico": "",
    "form_servico": TIPOS_SERVICO[0],
    "form_peca_utilizada": "",
    "form_valor_servico": 0.0,
    "form_valor_peca": 0.0,
    "form_status": STATUS[0],
    "form_pagamento": FORMAS_PAGAMENTO[0],
    "form_data_entrada": date.today(),
    "form_data_saida": None,
    "form_observacoes": "",
    "form_errors": {},
}


def apply_filters(df: pd.DataFrame, status: str, servico: str, termo: str) -> pd.DataFrame:
    filtered = df.copy()
    if status != "Todos":
        filtered = filtered[filtered["status"] == status]
    if servico != "Todos":
        filtered = filtered[filtered["servico"] == servico]
    if termo:
        termo_normalizado = termo.strip().lower()
        filtered = filtered[
            filtered["placa"].fillna("").str.lower().str.contains(termo_normalizado)
            | filtered["cliente_nome"].fillna("").str.lower().str.contains(termo_normalizado)
        ]
    return filtered


def empty_ordens_df() -> pd.DataFrame:
    return pd.DataFrame(columns=EMPTY_ORDENS_COLUMNS)


def is_database_locked(error: sqlite3.OperationalError) -> bool:
    return "database is locked" in str(error).lower()


def fetch_ordens_safely() -> pd.DataFrame:
    try:
        return fetch_ordens()
    except sqlite3.OperationalError as error:
        if not is_database_locked(error):
            raise
        st.warning("O banco SQLite está temporariamente ocupado. Tente atualizar a tela em alguns segundos.")
        return empty_ordens_df()


def apply_page_style() -> None:
    with CSS_FILE.open(encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


def render_sidebar(df: pd.DataFrame) -> str:
    st.sidebar.markdown("## Oficina Registro")
    st.sidebar.markdown(
        '<p class="sidebar-caption">Controle operacional das ordens de serviço da oficina.</p>',
        unsafe_allow_html=True,
    )
    st.sidebar.divider()

    menu = st.sidebar.radio(
        "Navegação",
        ["Cadastrar ordem", "Consultar registros", "Exportar / Enviar para S3"],
        label_visibility="collapsed",
    )

    st.sidebar.divider()
    total_ordens = len(df)
    ordens_abertas = int(df[df["status"].isin(STATUS_ABERTO)].shape[0]) if total_ordens else 0
    receita_total = float(df["valor_total"].sum()) if total_ordens else 0.0
    st.sidebar.metric("Ordens registradas", total_ordens)
    st.sidebar.metric("Em aberto", ordens_abertas)
    st.sidebar.metric("Receita acumulada", format_currency(receita_total))

    return menu


def render_header(df: pd.DataFrame) -> None:
    total_ordens = len(df)
    ordens_abertas = int(df[df["status"].isin(STATUS_ABERTO)].shape[0]) if total_ordens else 0
    ultima_ordem = df["ordem_id"].iloc[0] if total_ordens else "Ainda sem OS"

    st.markdown(
        f"""
        <div class="app-hero">
            <div class="hero-copy">
                <h1>Registro de Ordens de Serviço</h1>
                <p>
                    Cadastre atendimentos, acompanhe o status da oficina e exporte os dados
                    estruturados para alimentar a próxima etapa analítica.
                </p>
            </div>
            <div class="hero-panel">
                <div>
                    <span>Última ordem</span>
                    <strong>{ultima_ordem}</strong>
                </div>
                <div class="panel-footer">{ordens_abertas} ordens precisam de acompanhamento</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_section_intro(title: str, description: str) -> None:
    st.markdown(
        f"""
        <div class="section-card">
            <h3>{title}</h3>
            <p>{description}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_status_strip(df: pd.DataFrame) -> None:
    if df.empty:
        return
    counts = df["status"].value_counts().to_dict()
    pills = "".join(
        f'<div class="status-pill"><span>{status}</span><strong>{counts.get(status, 0)}</strong></div>'
        for status in STATUS
    )
    st.markdown(f'<div class="status-strip">{pills}</div>', unsafe_allow_html=True)


def _init_form_state() -> None:
    for key, value in FORM_DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _reset_form_state() -> None:
    for key, value in FORM_DEFAULTS.items():
        st.session_state[key] = value


def render_cadastro() -> None:
    _init_form_state()

    render_section_intro(
        "Nova ordem de serviço",
        "Preencha os dados essenciais do cliente, veículo e atendimento. Campos com asterisco são obrigatórios.",
    )

    errors: dict[str, str] = st.session_state["form_errors"]

    col1, col2 = st.columns(2, gap="large")

    with col1:
        st.markdown('<div class="form-panel-title">Cliente e veículo</div>', unsafe_allow_html=True)
        cliente_nome = st.text_input(
            "Nome do cliente *",
            placeholder="Ex.: Ana Souza",
            key="form_cliente_nome",
        )
        if "cliente_nome" in errors:
            st.error(errors["cliente_nome"])
        telefone = st.text_input(
            "Telefone",
            placeholder="(11) 99999-9999",
            key="form_telefone",
        )
        documento = st.text_input("CPF ou CNPJ", key="form_documento")
        placa_input = st.text_input(
            "Placa *",
            placeholder="ABC1D23",
            key="form_placa",
        )
        if "placa" in errors:
            st.error(errors["placa"])
        marca_veiculo = st.text_input("Marca do veículo", placeholder="Ex.: Toyota", key="form_marca_veiculo")
        modelo_veiculo = st.text_input("Modelo do veículo", placeholder="Ex.: Corolla", key="form_modelo_veiculo")
        ano_veiculo = st.number_input(
            "Ano do veículo",
            min_value=1900,
            max_value=2100,
            key="form_ano_veiculo",
        )
        mecanico = st.text_input("Mecânico responsável", key="form_mecanico")

    with col2:
        st.markdown('<div class="form-panel-title">Serviço e cobrança</div>', unsafe_allow_html=True)
        servico = st.selectbox("Tipo de serviço *", TIPOS_SERVICO, key="form_servico")
        peca_utilizada = st.text_input("Peça utilizada", key="form_peca_utilizada")
        valor_servico = st.number_input(
            "Valor do serviço *",
            min_value=0.0,
            step=10.0,
            format="%.2f",
            key="form_valor_servico",
        )
        if "valor_servico" in errors:
            st.error(errors["valor_servico"])
        valor_peca = st.number_input(
            "Valor da peça",
            min_value=0.0,
            step=10.0,
            format="%.2f",
            key="form_valor_peca",
        )
        status = st.selectbox("Status", STATUS, key="form_status")
        pagamento = st.selectbox("Forma de pagamento", FORMAS_PAGAMENTO, key="form_pagamento")
        date_col1, date_col2 = st.columns(2, gap="small")
        data_entrada = date_col1.date_input("Data de entrada", key="form_data_entrada")
        data_saida = date_col2.date_input("Data de saída", value=None, key="form_data_saida")
        if "data_saida" in errors:
            st.error(errors["data_saida"])

    observacoes = st.text_area(
        "Observações",
        placeholder="Descreva sintomas, peças recomendadas ou combinados com o cliente.",
        key="form_observacoes",
    )

    total_estimado = float(valor_servico or 0) + float(valor_peca or 0)
    st.markdown(
        f"""
        <div class="total-card">
            <div class="total-card__label">Total estimado</div>
            <div class="total-card__value">{format_currency(total_estimado)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    predicao = predict_valor_total(
        st.session_state.get("form_servico", TIPOS_SERVICO[0]),
        st.session_state.get("form_ano_veiculo", date.today().year),
    )
    if predicao is not None:
        st.info(
            f"Estimativa de valor total por IA: **{format_currency(predicao)}**  \n"
            f"Baseado no histórico de ordens com o mesmo tipo de serviço e ano do veículo."
        )

    submitted = st.button("Salvar ordem", use_container_width=True)

    if not submitted:
        return

    new_errors: dict[str, str] = {}

    if not cliente_nome.strip():
        new_errors["cliente_nome"] = "Nome do cliente é obrigatório."

    placa = re.sub(r"[^A-Z0-9]", "", (placa_input or "").upper())

    if not placa:
        new_errors["placa"] = "Placa é obrigatória."
    else:
        if not re.match(r"^[A-Z]{3}[0-9][A-Z][0-9]{2}$", placa):
            new_errors["placa"] = "Placa inválida. Use o padrão Mercosul (ex.: ABC1D23)."

    if valor_servico < 0:
        new_errors["valor_servico"] = "Valor do serviço deve ser maior ou igual a zero."

    if data_saida and data_saida < data_entrada:
        new_errors["data_saida"] = "Data de saída não pode ser anterior à data de entrada."

    st.session_state["form_errors"] = new_errors

    if new_errors:
        st.rerun()
        return

    ordem_id = insert_ordem(
        {
            "cliente_nome": cliente_nome.strip(),
            "telefone": telefone.strip(),
            "documento": documento.strip(),
            "placa": placa,
            "marca_veiculo": marca_veiculo.strip(),
            "modelo_veiculo": modelo_veiculo.strip(),
            "ano_veiculo": int(ano_veiculo),
            "mecanico": mecanico.strip(),
            "servico": servico,
            "peca_utilizada": peca_utilizada.strip(),
            "valor_servico": valor_servico,
            "valor_peca": valor_peca,
            "status": status,
            "pagamento": pagamento,
            "data_entrada": data_entrada.isoformat(),
            "data_saida": data_saida.isoformat() if data_saida else "",
            "observacoes": observacoes.strip(),
        }
    )

    st.session_state["form_errors"] = {}
    st.success(f"Ordem de serviço {ordem_id} cadastrada com sucesso.")


def render_consulta() -> None:
    render_section_intro(
        "Consulta de registros",
        "Use os filtros para localizar ordens por status, tipo de serviço, placa ou nome do cliente.",
    )
    df = fetch_ordens_safely()

    if df.empty:
        st.info("Nenhuma ordem de serviço cadastrada ainda.")
        return

    render_status_strip(df)

    col1, col2, col3 = st.columns(3, gap="large")
    with col1:
        status_filter = st.selectbox("Filtrar por status", ["Todos"] + STATUS)
    with col2:
        servico_filter = st.selectbox("Filtrar por serviço", ["Todos"] + TIPOS_SERVICO)
    with col3:
        termo_busca = st.text_input("Buscar por placa ou cliente", placeholder="Digite placa ou cliente")

    filtered = apply_filters(df, status_filter, servico_filter, termo_busca)

    total_ordens = len(filtered)
    receita_total = float(filtered["valor_total"].sum()) if total_ordens else 0.0
    ticket_medio = receita_total / total_ordens if total_ordens else 0.0
    ordens_abertas = int(filtered[filtered["status"].isin(STATUS_ABERTO)].shape[0])

    try:
        # Status distribution
        status_counts = filtered["status"].value_counts().reindex(STATUS, fill_value=0).reset_index()
        status_counts.columns = ["status", "count"]

        # Receita por mês (data_entrada)
        if "data_entrada" in filtered.columns:
            df_time = filtered.copy()
            df_time["data_entrada_dt"] = pd.to_datetime(df_time["data_entrada"], errors="coerce")
            monthly = (
                df_time.dropna(subset=["data_entrada_dt"])
                .set_index("data_entrada_dt")
                .resample("ME")["valor_total"].sum()
                .reset_index()
            )
        else:
            monthly = pd.DataFrame({"data_entrada_dt": [], "valor_total": []})

        # Top serviços
        top_servicos = (
            filtered["servico"].value_counts()
            .reset_index(name="count")
            .head(6)
        )

        c1, c2, c3 = st.columns([1, 1, 1], gap="large")
        with c1:
            bar = alt.Chart(status_counts).mark_bar().encode(
                x=alt.X("status:N", sort=STATUS, title=None),
                y=alt.Y("count:Q", title="Quantidade"),
                color=alt.Color("status:N", legend=None, scale=alt.Scale(scheme="tableau10")),
            ).properties(height=180)
            st.altair_chart(bar, use_container_width=True)

        with c2:
            line = alt.Chart(monthly).mark_line(point=True).encode(
                x=alt.X("data_entrada_dt:T", title="Mês"),
                y=alt.Y("valor_total:Q", title="Receita"),
                tooltip=[alt.Tooltip("valor_total:Q", format=",")],
            ).properties(height=180)
            st.altair_chart(line, use_container_width=True)

        with c3:
            if not top_servicos.empty:
                pie = alt.Chart(top_servicos).mark_arc().encode(
                    theta=alt.Theta("count:Q"),
                    color=alt.Color("servico:N", legend=None),
                    tooltip=["servico:N", "count:Q"],
                ).properties(height=180)
                st.altair_chart(pie, use_container_width=True)
            else:
                st.info("Sem dados de serviços para exibir")
    except Exception as exc:
        st.warning(f"Erro ao renderizar gráficos: {exc}")

    met1, met2, met3, met4 = st.columns(4, gap="medium")
    met1.metric("Total de ordens", total_ordens)
    met2.metric("Receita total", format_currency(receita_total))
    met3.metric("Ticket médio", format_currency(ticket_medio))
    met4.metric("Ordens em aberto", ordens_abertas)

    display_df = filtered.rename(
        columns={
            "ordem_id": "Ordem",
            "cliente_nome": "Cliente",
            "placa": "Placa",
            "servico": "Serviço",
            "status": "Status",
            "pagamento": "Pagamento",
            "valor_servico": "Serviço (R$)",
            "valor_peca": "Peça (R$)",
            "valor_total": "Total (R$)",
            "data_entrada": "Entrada",
            "data_saida": "Saída",
            "mecanico": "Mecânico",
        }
    )
    priority_columns = [
        "Ordem", "Cliente", "Placa", "Serviço", "Status",
        "Pagamento", "Total (R$)", "Entrada", "Saída", "Mecânico",
    ]
    display_df = display_df[[c for c in priority_columns if c in display_df.columns]]

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Total (R$)": st.column_config.NumberColumn("Total (R$)", format="R$ %.2f"),
        },
    )


def render_exportacao() -> None:
    render_section_intro(
        "Exportação dos dados",
        "Gere um CSV atualizado para download local, envie para o S3 e execute a camada curated com Spark.",
    )
    df = fetch_ordens_safely()

    if df.empty:
        st.info("Nenhum registro disponível para exportação.")
        return

    csv_path = export_ordens_to_csv()
    csv_bytes = df.to_csv(index=False).encode("utf-8-sig")

    col1, col2, col3 = st.columns([1, 1, 1], gap="large")
    with col1:
        st.markdown("#### Download")
        st.write("Baixe uma cópia com todos os registros da base local.")
        st.download_button(
            label="Baixar CSV",
            data=csv_bytes,
            file_name="ordens_servico_export.csv",
            mime="text/csv",
            use_container_width=True,
        )
        st.success(f"Cópia local atualizada em {csv_path}")

    with col2:
        st.markdown("#### Envio para AWS S3")
        st.write("Use esta ação quando quiser disponibilizar o arquivo para a camada analítica.")
        if st.button("Enviar CSV para S3", use_container_width=True):
            ok, message = upload_file_to_s3(csv_path)
            if ok:
                st.success(message)
            else:
                st.error(message)

    with col3:
        st.markdown("#### Curated com Spark")
        st.write("Transforme o CSV em Parquet particionado para consumo analítico local.")
        if st.button("Gerar Curated Spark", use_container_width=True):
            ok, message, _ = run_spark_curated_pipeline(csv_path)
            if ok:
                st.success(message)
            else:
                st.error(message)


def main() -> None:
    st.set_page_config(page_title="Oficina Registro", layout="wide")
    apply_page_style()
    try:
        init_db()
    except sqlite3.OperationalError as error:
        if not is_database_locked(error):
            raise
        st.warning("O banco SQLite está temporariamente ocupado. A interface foi carregada em modo de consulta limitada.")

    df = fetch_ordens_safely()
    menu = render_sidebar(df)
    render_header(df)

    if menu == "Cadastrar ordem":
        render_cadastro()
    elif menu == "Consultar registros":
        render_consulta()
    else:
        render_exportacao()


if __name__ == "__main__":
    main()