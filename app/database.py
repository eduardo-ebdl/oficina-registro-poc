import sqlite3
from pathlib import Path

import pandas as pd

DB_PATH = Path(__file__).parent.parent / "data" / "oficina.db"


def init_db() -> sqlite3.Connection:
    """Inicializa o banco SQLite e cria a tabela principal se não existir."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ordens_servico (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            ordem_id         TEXT UNIQUE,
            cliente_nome     TEXT NOT NULL,
            telefone         TEXT,
            documento        TEXT,
            placa            TEXT NOT NULL,
            marca_veiculo    TEXT,
            modelo_veiculo   TEXT,
            ano_veiculo      INTEGER,
            mecanico         TEXT,
            servico          TEXT NOT NULL,
            peca_utilizada   TEXT,
            valor_servico    REAL DEFAULT 0,
            valor_peca       REAL DEFAULT 0,
            valor_total      REAL,
            status           TEXT,
            pagamento        TEXT,
            data_entrada     TEXT,
            data_saida       TEXT,
            observacoes      TEXT,
            created_at       TEXT
        )
    """)
    conn.commit()
    return conn


def get_next_ordem_id(conn: sqlite3.Connection) -> str:
    """Gera o próximo ID sequencial no formato OS000001."""
    cursor = conn.execute("SELECT MAX(id) FROM ordens_servico")
    max_id = cursor.fetchone()[0]
    next_id = (max_id or 0) + 1
    return f"OS{str(next_id).zfill(6)}"


def insert_ordem(conn: sqlite3.Connection, data: dict) -> bool:
    """Insere uma nova ordem de serviço. Retorna True em caso de sucesso."""
    try:
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
            data,
        )
        conn.commit()
        return True
    except Exception:
        return False


def get_all_ordens(conn: sqlite3.Connection) -> pd.DataFrame:
    """Retorna todas as ordens de serviço ordenadas pela mais recente."""
    return pd.read_sql_query(
        "SELECT * FROM ordens_servico ORDER BY id DESC", conn
    )
