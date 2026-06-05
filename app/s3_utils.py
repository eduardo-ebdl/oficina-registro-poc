from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


S3_KEY_CSV = "raw/ordens_streamlit/ordens_servico_export.csv"
S3_PREFIX_CURATED = "curated/ordens_servico"


def _make_s3_client(region: str, access_key: str, secret_key: str):
    import boto3
    return boto3.client(
        "s3",
        region_name=region,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
    )


def _load_aws_env() -> tuple[str | None, str | None, str | None, str | None]:
    load_dotenv()
    return (
        os.getenv("BUCKET_RAW"),
        os.getenv("AWS_REGION"),
        os.getenv("AWS_ACCESS_KEY_ID"),
        os.getenv("AWS_SECRET_ACCESS_KEY"),
    )


def _check_missing(bucket, region, access_key, secret_key) -> list[str]:
    return [
        name
        for name, value in {
            "AWS_REGION": region,
            "AWS_ACCESS_KEY_ID": access_key,
            "AWS_SECRET_ACCESS_KEY": secret_key,
            "BUCKET_RAW": bucket,
        }.items()
        if not value
    ]


def upload_file_to_s3(file_path: str | Path) -> tuple[bool, str]:
    try:
        import boto3
        from botocore.exceptions import (
            ClientError,
            ConnectTimeoutError,
            EndpointConnectionError,
            NoCredentialsError,
            PartialCredentialsError,
        )
    except ModuleNotFoundError:
        return False, "Dependência ausente: instale boto3 para habilitar o envio para S3."

    try:
        from botocore.exceptions import (
            ClientError,
            ConnectTimeoutError,
            EndpointConnectionError,
            NoCredentialsError,
            PartialCredentialsError,
        )
    except ModuleNotFoundError:
        return False, "Dependência ausente: instale boto3 para habilitar o envio para S3."

    path = Path(file_path)
    if not path.exists():
        return False, f"Arquivo não encontrado: {path}"

    bucket, region, access_key, secret_key = _load_aws_env()
    missing = _check_missing(bucket, region, access_key, secret_key)
    if missing:
        return False, "Variáveis ausentes no .env: " + ", ".join(missing)

    try:
        s3_client = _make_s3_client(region, access_key, secret_key)
        s3_client.upload_file(str(path), bucket, S3_KEY_CSV)
        return True, f"Arquivo enviado para s3://{bucket}/{S3_KEY_CSV}"
    except (NoCredentialsError, PartialCredentialsError):
        return False, "Credenciais AWS inválidas ou incompletas."
    except (EndpointConnectionError, ConnectTimeoutError):
        return False, "Falha de conexão com a AWS. Verifique a internet e a região configurada."
    except ClientError as error:
        code = error.response.get("Error", {}).get("Code", "Erro desconhecido")
        if code in {"NoSuchBucket", "404"}:
            return False, f"Bucket não encontrado: {bucket}"
        if code in {"AccessDenied", "InvalidAccessKeyId", "SignatureDoesNotMatch"}:
            return False, "Acesso negado. Verifique bucket, permissões e credenciais AWS."
        return False, f"Erro ao enviar para o S3 ({code}): {error}"
    except Exception as error:
        return False, f"Falha inesperada ao enviar para o S3: {error}"


def upload_parquet_to_s3(curated_dir: str | Path) -> tuple[bool, str]:
    """Faz upload de todos os arquivos Parquet de curated_dir para o prefixo curated/ no S3."""
    try:
        from botocore.exceptions import (
            ClientError,
            ConnectTimeoutError,
            EndpointConnectionError,
            NoCredentialsError,
            PartialCredentialsError,
        )
    except ModuleNotFoundError:
        return False, "Dependência ausente: instale boto3 para habilitar o envio para S3."

    base = Path(curated_dir)
    if not base.exists():
        return False, f"Diretório Parquet não encontrado: {base}"

    parquet_files = list(base.rglob("*.parquet"))
    if not parquet_files:
        return False, "Nenhum arquivo .parquet encontrado no diretório curated."

    bucket, region, access_key, secret_key = _load_aws_env()
    missing = _check_missing(bucket, region, access_key, secret_key)
    if missing:
        return False, "Variáveis ausentes no .env: " + ", ".join(missing)

    try:
        s3_client = _make_s3_client(region, access_key, secret_key)
        uploaded = 0
        for file in parquet_files:
            s3_key = S3_PREFIX_CURATED + "/" + file.relative_to(base).as_posix()
            s3_client.upload_file(str(file), bucket, s3_key)
            uploaded += 1
        return True, f"{uploaded} arquivo(s) Parquet enviados para s3://{bucket}/{S3_PREFIX_CURATED}/"
    except (NoCredentialsError, PartialCredentialsError):
        return False, "Credenciais AWS inválidas ou incompletas."
    except (EndpointConnectionError, ConnectTimeoutError):
        return False, "Falha de conexão com a AWS. Verifique a internet e a região configurada."
    except ClientError as error:
        code = error.response.get("Error", {}).get("Code", "Erro desconhecido")
        if code in {"NoSuchBucket", "404"}:
            return False, f"Bucket não encontrado: {bucket}"
        if code in {"AccessDenied", "InvalidAccessKeyId", "SignatureDoesNotMatch"}:
            return False, "Acesso negado. Verifique bucket, permissões e credenciais AWS."
        return False, f"Erro ao enviar para o S3 ({code}): {error}"
    except Exception as error:
        return False, f"Falha inesperada ao enviar para o S3: {error}"
