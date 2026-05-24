import os
from typing import Tuple

import boto3
import botocore.exceptions


def upload_file_to_s3(filepath: str) -> Tuple[bool, str]:
    """Envia o arquivo para o S3. Retorna (sucesso, mensagem)."""
    bucket     = os.getenv("BUCKET_RAW", "").strip()
    region     = os.getenv("AWS_REGION", "").strip()
    access_key = os.getenv("AWS_ACCESS_KEY_ID", "").strip()
    secret_key = os.getenv("AWS_SECRET_ACCESS_KEY", "").strip()

    missing = [
        name
        for name, val in {
            "BUCKET_RAW": bucket,
            "AWS_REGION": region,
            "AWS_ACCESS_KEY_ID": access_key,
            "AWS_SECRET_ACCESS_KEY": secret_key,
        }.items()
        if not val
    ]
    if missing:
        return False, f"Variáveis de ambiente ausentes ou vazias: {', '.join(missing)}"

    try:
        client = boto3.client(
            "s3",
            region_name=region,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
        )
        key = "raw/ordens_streamlit/ordens_servico_export.csv"
        client.upload_file(filepath, bucket, key)
        return True, f"Upload realizado com sucesso para s3://{bucket}/{key}"

    except botocore.exceptions.NoCredentialsError:
        return False, "Credenciais AWS inválidas ou não encontradas."
    except botocore.exceptions.ClientError as e:
        code = e.response["Error"]["Code"]
        if code == "NoSuchBucket":
            return False, f"Bucket '{bucket}' não existe."
        if code == "AccessDenied":
            return False, "Acesso negado. Verifique as permissões IAM."
        return False, f"Erro AWS ({code}): {str(e)}"
    except Exception as e:
        return False, f"Erro inesperado: {str(e)}"
