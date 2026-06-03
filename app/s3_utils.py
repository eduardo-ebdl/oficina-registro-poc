from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


S3_KEY = "raw/ordens_streamlit/ordens_servico_export.csv"


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

    load_dotenv()

    path = Path(file_path)
    if not path.exists():
        return False, f"Arquivo não encontrado: {path}"

    bucket = os.getenv("BUCKET_RAW")
    region = os.getenv("AWS_REGION")
    access_key = os.getenv("AWS_ACCESS_KEY_ID")
    secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")

    missing = [
        name
        for name, value in {
            "AWS_REGION": region,
            "AWS_ACCESS_KEY_ID": access_key,
            "AWS_SECRET_ACCESS_KEY": secret_key,
            "BUCKET_RAW": bucket,
        }.items()
        if not value
    ]
    if missing:
        return False, "Variáveis ausentes no .env: " + ", ".join(missing)

    try:
        s3_client = boto3.client(
            "s3",
            region_name=region,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
        )
        s3_client.upload_file(str(path), bucket, S3_KEY)
        return True, f"Arquivo enviado para s3://{bucket}/{S3_KEY}"
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
