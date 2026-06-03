# PoC - Registro de Ordens de Serviço

Aplicativo MVP em Streamlit para registrar ordens de serviço de uma oficina automotiva. A PoC valida a camada de coleta dos dados reais da oficina, salvando os registros em SQLite, exportando para CSV, enviando para S3 e gerando uma camada curated local com Spark em formato Parquet.

## Objetivo

A oficina parceira ainda não possui registro estruturado de atendimentos, clientes, veículos, peças, valores e status dos serviços. Este app resolve a primeira etapa do fluxo de dados: capturar informações reais de ordens de serviço em uma interface simples.

## Estrutura

```text
oficina_registro_poc/
├── app/
│   ├── app.py
│   ├── database.py
│   └── s3_utils.py
├── data/
│   └── oficina.db
├── requirements.txt
├── .env.example
└── README.md
```

O arquivo `data/oficina.db` é criado automaticamente na primeira execução.

## Criar ambiente virtual

```bash
python -m venv venv
source venv/bin/activate
```

No Windows:

```bash
python -m venv venv
venv\Scripts\activate
```

## Instalar dependências

```bash
pip install -r requirements.txt
```

## Configurar .env

Copie o arquivo de exemplo:

```bash
cp .env.example .env
```

Preencha as variáveis somente se quiser usar o envio opcional para S3:

```env
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=sua_access_key
AWS_SECRET_ACCESS_KEY=sua_secret_key
BUCKET_RAW=nome-do-bucket-raw
```

O upload envia o CSV para:

```text
raw/ordens_streamlit/ordens_servico_export.csv
```

## Rodar o Streamlit

Execute a partir da pasta do projeto:

```bash
streamlit run app/app.py
```

## Funcionalidades

- Cadastro de ordens de serviço com dados do cliente, veículo, serviço, peças, valores, status e pagamento.
- Geração automática de `ordem_id` no formato `OS000001`, `OS000002` etc.
- Cálculo automático de `valor_total`.
- Registro automático de `created_at`.
- Consulta com filtros por status, tipo de serviço e busca por placa ou cliente.
- Métricas simples: total de ordens, receita total, ticket médio e ordens em aberto.
- Exportação dos registros para `data/ordens_servico_export.csv`.
- Download do CSV pela interface.
- Envio opcional do CSV para AWS S3 usando `boto3`.
- Transformação local com Spark para `data/curated/ordens_servico/` em Parquet particionado por `ano_mes`.

## Spark nesta PoC

O botão **Gerar Curated Spark** (na tela de exportação) executa um pipeline local que:

- Lê o CSV exportado.
- Normaliza campos como `placa`.
- Faz cast dos valores numéricos.
- Converte datas (`data_entrada`, `data_saida`) e `created_at`.
- Cria a coluna booleana `ordem_aberta`.
- Remove duplicidade por `ordem_id` mantendo o registro mais recente.
- Escreve parquet particionado por `ano_mes` em `data/curated/ordens_servico/`.

Requisitos adicionais para Spark local:

- Java (JRE/JDK) instalado.
- Dependência `pyspark` (já incluída no `requirements.txt`).

## Escopo da PoC

Esta PoC é apenas o aplicativo de registro e preparação inicial de dados. Ela não implementa login, autenticação, dashboards avançados, banco relacional complexo, Glue Crawlers ou orquestração de jobs em produção. O foco é validar um MVP funcional para iniciar a coleta e a primeira camada analítica dos dados reais da oficina.
