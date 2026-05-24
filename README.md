# PoC — Registro de Ordens de Serviço | Oficina Automotiva

## 1. Objetivo

Esta aplicação é a **camada de coleta de dados** de uma oficina mecânica de pequeno porte.
O objetivo é registrar ordens de serviço, clientes, veículos, peças e pagamentos em um
banco SQLite local, e exportar os dados como CSV para uma arquitetura analítica existente
(S3 + Glue + dashboards) que consome os arquivos a partir do prefixo `raw/ordens_streamlit/`.

Escopo deliberadamente limitado: **cadastro e exportação apenas**.
Sem autenticação, sem edição de registros, sem relacionamentos complexos, sem dashboards.

---

## 2. Setup

```bash
# 1. Criar e ativar virtualenv
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux / macOS
source .venv/bin/activate

# 2. Instalar dependências
pip install -r requirements.txt

# 3. Configurar variáveis de ambiente (apenas necessário para envio ao S3)
copy .env.example .env   # Windows
cp .env.example .env     # Linux / macOS
# Edite .env com suas credenciais AWS e nome do bucket
```

---

## 3. Executar

```bash
# A partir da raiz do projeto (oficina_registro_poc/)
streamlit run app/app.py
```

O banco `data/oficina.db` é criado automaticamente na primeira execução.

---

## 4. Exportação

**Download CSV:** na página "Exportar / S3", clique em **BAIXAR CSV** para baixar o arquivo
diretamente pelo navegador. Uma cópia local também é salva em `data/ordens_servico_export.csv`.

**Envio para S3:** após configurar o arquivo `.env` com as credenciais AWS, clique em
**ENVIAR PARA S3**. O arquivo é enviado para:

```
s3://<BUCKET_RAW>/raw/ordens_streamlit/ordens_servico_export.csv
```

O Glue Crawler ou job da camada analítica lê a partir desse prefixo.

---

## 5. Estrutura do projeto

```
oficina_registro_poc/
├── app/
│   ├── app.py          # Aplicação Streamlit principal (UI + lógica de páginas)
│   ├── database.py     # Funções SQLite: init, insert, select, geração de OS ID
│   └── s3_utils.py     # Upload para S3 com tratamento de erros AWS
├── .streamlit/
│   └── config.toml     # Tema visual (cores, fonte monospace)
├── data/
│   └── .gitkeep        # Mantém o diretório no git; oficina.db é gerado em runtime
├── requirements.txt    # Dependências Python
├── .env.example        # Modelo de variáveis de ambiente para credenciais AWS
└── README.md           # Este arquivo
```
