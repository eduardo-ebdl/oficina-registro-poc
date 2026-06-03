from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "oficina.db"


def get_connection() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH, timeout=30)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ordens_servico (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ordem_id TEXT UNIQUE,
                cliente_nome TEXT,
                telefone TEXT,
                documento TEXT,
                placa TEXT,
                marca_veiculo TEXT,
                modelo_veiculo TEXT,
                ano_veiculo INTEGER,
                mecanico TEXT,
                servico TEXT,
                peca_utilizada TEXT,
                valor_servico REAL,
                valor_peca REAL,
                valor_total REAL,
                status TEXT,
                pagamento TEXT,
                data_entrada TEXT,
                data_saida TEXT,
                observacoes TEXT,
                created_at TEXT
            )
            """
        )
        conn.commit()


def generate_ordem_id(conn: sqlite3.Connection) -> str:
    cursor = conn.execute("SELECT MAX(id) AS max_id FROM ordens_servico")
    row = cursor.fetchone()
    next_id = (row["max_id"] or 0) + 1
    return f"OS{next_id:06d}"


def insert_ordem(data: dict[str, Any]) -> str:
    with get_connection() as conn:
        ordem_id = generate_ordem_id(conn)
        valor_servico = float(data.get("valor_servico") or 0)
        valor_peca = float(data.get("valor_peca") or 0)
        valor_total = valor_servico + valor_peca

        payload = {
            **data,
            "ordem_id": ordem_id,
            "valor_servico": valor_servico,
            "valor_peca": valor_peca,
            "valor_total": valor_total,
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }

        conn.execute(
            """
            INSERT INTO ordens_servico (
                ordem_id, cliente_nome, telefone, documento, placa,
                marca_veiculo, modelo_veiculo, ano_veiculo, mecanico,
                servico, peca_utilizada, valor_servico, valor_peca,
                valor_total, status, pagamento, data_entrada, data_saida,
                observacoes, created_at
            ) VALUES (
                :ordem_id, :cliente_nome, :telefone, :documento, :placa,
                :marca_veiculo, :modelo_veiculo, :ano_veiculo, :mecanico,
                :servico, :peca_utilizada, :valor_servico, :valor_peca,
                :valor_total, :status, :pagamento, :data_entrada, :data_saida,
                :observacoes, :created_at
            )
            """,
            payload,
        )
        conn.commit()
        return ordem_id


def fetch_ordens() -> pd.DataFrame:
    with get_connection() as conn:
        return pd.read_sql_query(
            "SELECT * FROM ordens_servico ORDER BY id DESC",
            conn,
        )


def export_ordens_to_csv(path: Path | None = None) -> Path:
    output_path = path or (DATA_DIR / "ordens_servico_export.csv")
    df = fetch_ordens()
    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    return output_path
