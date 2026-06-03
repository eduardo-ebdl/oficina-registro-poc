from __future__ import annotations

from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
CURATED_DIR = DATA_DIR / "curated" / "ordens_servico"


def run_spark_curated_pipeline(csv_path: str | Path) -> tuple[bool, str, Path | None]:
    """Transforma o CSV bruto em parquet curated usando Spark local."""
    path = Path(csv_path)
    if not path.exists():
        return False, f"Arquivo CSV não encontrado: {path}", None

    try:
        from pyspark.sql import SparkSession
        from pyspark.sql import functions as F
        from pyspark.sql.window import Window
    except ModuleNotFoundError:
        return (
            False,
            "Dependência ausente: instale pyspark para habilitar a transformação Spark.",
            None,
        )

    spark = (
        SparkSession.builder.appName("oficina-registro-curated")
        .master("local[*]")
        .config("spark.sql.session.timeZone", "America/Sao_Paulo")
        .getOrCreate()
    )

    try:
        df = (
            spark.read.option("header", "true")
            .option("inferSchema", "true")
            .csv(str(path))
        )

        normalized = (
            df.withColumn("placa", F.upper(F.regexp_replace(F.col("placa"), r"[^A-Za-z0-9]", "")))
            .withColumn("valor_servico", F.col("valor_servico").cast("double"))
            .withColumn("valor_peca", F.col("valor_peca").cast("double"))
            .withColumn("valor_total", F.col("valor_total").cast("double"))
            .withColumn("data_entrada_dt", F.to_date("data_entrada"))
            .withColumn("data_saida_dt", F.to_date("data_saida"))
            .withColumn("created_at_ts", F.to_timestamp("created_at"))
            .withColumn(
                "ordem_aberta",
                F.col("status").isin("Aberto", "Em andamento", "Aguardando peça"),
            )
        )

        row_order = Window.partitionBy("ordem_id").orderBy(F.col("created_at_ts").desc_nulls_last())
        deduped = (
            normalized.withColumn("_rn", F.row_number().over(row_order))
            .filter(F.col("_rn") == 1)
            .drop("_rn")
        )

        curated = deduped.withColumn("ano_mes", F.date_format("data_entrada_dt", "yyyy-MM"))

        output_path = CURATED_DIR
        output_path.mkdir(parents=True, exist_ok=True)

        (
            curated.write.mode("overwrite")
            .partitionBy("ano_mes")
            .parquet(str(output_path))
        )

        total_rows = curated.count()
        return True, f"Curated parquet gerado com Spark em {output_path} ({total_rows} linhas).", output_path
    except Exception as error:
        return False, f"Falha na transformação Spark: {error}", None
    finally:
        spark.stop()
