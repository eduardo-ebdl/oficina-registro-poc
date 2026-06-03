from __future__ import annotations

import pandas as pd
from database import fetch_ordens

_model_cache: tuple[int, object] | None = None


def _get_model(df: pd.DataFrame) -> object | None:
    global _model_cache
    if _model_cache is not None and _model_cache[0] == len(df):
        return _model_cache[1]

    try:
        from sklearn.linear_model import LinearRegression
        from sklearn.preprocessing import OneHotEncoder
        from sklearn.pipeline import Pipeline
        from sklearn.compose import ColumnTransformer
    except ModuleNotFoundError:
        return None

    X = df[["servico", "ano_veiculo"]]
    y = df["valor_total"]

    preprocessor = ColumnTransformer([
        ("servico", OneHotEncoder(handle_unknown="ignore"), ["servico"]),
        ("ano", "passthrough", ["ano_veiculo"]),
    ])
    model = Pipeline([("prep", preprocessor), ("reg", LinearRegression())])
    model.fit(X, y)

    _model_cache = (len(df), model)
    return model


def predict_valor_total(servico: str, ano_veiculo: int) -> float | None:
    df = fetch_ordens()
    if len(df) < 5:
        return None

    df = df.dropna(subset=["valor_total", "servico", "ano_veiculo"])
    df["ano_veiculo"] = pd.to_numeric(df["ano_veiculo"], errors="coerce")
    df = df.dropna(subset=["ano_veiculo"])

    model = _get_model(df)
    if model is None:
        return None

    entrada = pd.DataFrame([{"servico": servico, "ano_veiculo": float(ano_veiculo)}])
    return max(float(model.predict(entrada)[0]), 0.0)
