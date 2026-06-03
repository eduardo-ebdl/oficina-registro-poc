"""Popula o banco SQLite com dados fictícios para testes e validação do modelo de IA."""
from __future__ import annotations

import random
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "app"))

from database import init_db, insert_ordem

CLIENTES = [
    ("Ana Souza", "(62) 99111-2233", "123.456.789-00"),
    ("Bruno Lima", "(62) 98222-3344", "234.567.890-11"),
    ("Carla Mendes", "(62) 97333-4455", "345.678.901-22"),
    ("Diego Rocha", "(62) 96444-5566", "456.789.012-33"),
    ("Elaine Costa", "(62) 95555-6677", "567.890.123-44"),
    ("Fábio Alves", "(62) 94666-7788", "678.901.234-55"),
    ("Gisele Nunes", "(62) 93777-8899", "789.012.345-66"),
    ("Henrique Dias", "(62) 92888-9900", "890.123.456-77"),
    ("Isabela Ferreira", "(62) 91999-0011", "901.234.567-88"),
    ("João Martins", "(62) 90000-1122", "012.345.678-99"),
    ("Karla Ribeiro", "(62) 99123-4567", "111.222.333-44"),
    ("Lucas Carvalho", "(62) 98234-5678", "222.333.444-55"),
    ("Marina Oliveira", "(62) 97345-6789", "333.444.555-66"),
    ("Nelson Sousa", "(62) 96456-7890", "444.555.666-77"),
    ("Patricia Gomes", "(62) 95567-8901", "555.666.777-88"),
]

VEICULOS = [
    ("Toyota", "Corolla", range(2015, 2024)),
    ("Honda", "Civic", range(2014, 2024)),
    ("Volkswagen", "Gol", range(2010, 2023)),
    ("Chevrolet", "Onix", range(2013, 2024)),
    ("Ford", "Ka", range(2012, 2022)),
    ("Hyundai", "HB20", range(2013, 2024)),
    ("Renault", "Kwid", range(2017, 2024)),
    ("Fiat", "Uno", range(2008, 2022)),
    ("Nissan", "Versa", range(2012, 2023)),
    ("Jeep", "Renegade", range(2015, 2024)),
]

PLACAS = [
    "ABC1D23", "DEF2E34", "GHI3F45", "JKL4G56", "MNO5H67",
    "PQR6I78", "STU7J89", "VWX8K90", "YZA9L01", "BCD0M12",
    "EFG1N23", "HIJ2O34", "KLM3P45", "NOP4Q56", "QRS5R67",
    "TUV6S78", "WXY7T89", "ZAB8U90", "CDE9V01", "FGH0W12",
    "IJK1X23", "LMN2Y34", "OPQ3Z45", "RST4A56", "UVW5B67",
]

MECANICOS = ["Carlos", "Rui", "Sandro", "Tiago", "Wanderson"]

TIPOS_SERVICO = [
    "Troca de óleo", "Revisão completa", "Alinhamento e balanceamento",
    "Troca de freios", "Suspensão", "Elétrica", "Ar-condicionado",
    "Câmbio", "Motor", "Funilaria e pintura", "Outro",
]

PECAS_POR_SERVICO: dict[str, list[tuple[str, float, float]]] = {
    "Troca de óleo":               [("Óleo 5W30", 60, 120), ("Filtro de óleo", 25, 60)],
    "Revisão completa":            [("Kit revisão", 150, 350), ("Velas", 80, 200)],
    "Alinhamento e balanceamento": [("", 0, 0)],
    "Troca de freios":             [("Pastilha dianteira", 80, 200), ("Disco de freio", 150, 400)],
    "Suspensão":                   [("Amortecedor", 200, 600), ("Pivô", 80, 200)],
    "Elétrica":                    [("Bateria", 250, 600), ("Alternador", 300, 700)],
    "Ar-condicionado":             [("Gás R134a", 80, 150), ("Filtro cabine", 40, 100)],
    "Câmbio":                      [("Kit embreagem", 350, 800), ("", 0, 0)],
    "Motor":                       [("Junta do cabeçote", 200, 500), ("Correia dentada", 150, 400)],
    "Funilaria e pintura":         [("Tinta automotiva", 200, 800), ("", 0, 0)],
    "Outro":                       [("Peça avulsa", 30, 300)],
}

VALOR_SERVICO_POR_TIPO: dict[str, tuple[float, float]] = {
    "Troca de óleo":               (80, 150),
    "Revisão completa":            (300, 700),
    "Alinhamento e balanceamento": (80, 150),
    "Troca de freios":             (150, 350),
    "Suspensão":                   (200, 500),
    "Elétrica":                    (100, 400),
    "Ar-condicionado":             (150, 400),
    "Câmbio":                      (400, 1000),
    "Motor":                       (500, 2000),
    "Funilaria e pintura":         (500, 3000),
    "Outro":                       (50, 500),
}

STATUS = ["Aberto", "Em andamento", "Aguardando peça", "Concluído", "Cancelado"]
STATUS_WEIGHTS = [5, 10, 10, 65, 10]

PAGAMENTOS = ["Dinheiro", "Cartão débito", "Cartão crédito", "Pix", "Pendente"]
PAGAMENTO_WEIGHTS = [20, 15, 20, 35, 10]


def random_date(start: date, end: date) -> date:
    return start + timedelta(days=random.randint(0, (end - start).days))


def gerar_ordem() -> dict:
    cliente_nome, telefone, documento = random.choice(CLIENTES)
    marca, modelo, anos = random.choice(VEICULOS)
    ano_veiculo = random.choice(list(anos))
    placa = random.choice(PLACAS)
    mecanico = random.choice(MECANICOS)
    servico = random.choice(TIPOS_SERVICO)

    peca_nome, peca_min, peca_max = random.choice(PECAS_POR_SERVICO[servico])
    valor_peca = round(random.uniform(peca_min, peca_max), 2) if peca_nome else 0.0

    svc_min, svc_max = VALOR_SERVICO_POR_TIPO[servico]
    valor_servico = round(random.uniform(svc_min, svc_max), 2)

    status = random.choices(STATUS, weights=STATUS_WEIGHTS)[0]
    pagamento = random.choices(PAGAMENTOS, weights=PAGAMENTO_WEIGHTS)[0]

    data_entrada = random_date(date(2024, 1, 1), date(2026, 5, 30))
    data_saida = None
    if status in ("Concluído", "Cancelado"):
        data_saida = data_entrada + timedelta(days=random.randint(0, 7))

    return {
        "cliente_nome": cliente_nome,
        "telefone": telefone,
        "documento": documento,
        "placa": placa,
        "marca_veiculo": marca,
        "modelo_veiculo": modelo,
        "ano_veiculo": ano_veiculo,
        "mecanico": mecanico,
        "servico": servico,
        "peca_utilizada": peca_nome,
        "valor_servico": valor_servico,
        "valor_peca": valor_peca,
        "status": status,
        "pagamento": pagamento,
        "data_entrada": data_entrada.isoformat(),
        "data_saida": data_saida.isoformat() if data_saida else "",
        "observacoes": "",
    }


def main(n: int = 500) -> None:
    init_db()
    for i in range(1, n + 1):
        insert_ordem(gerar_ordem())
        if i % 50 == 0:
            print(f"  {i}/{n} ordens inseridas...")
    print(f"Concluído: {n} ordens inseridas.")


if __name__ == "__main__":
    total = int(sys.argv[1]) if len(sys.argv) > 1 else 500
    main(total)
