"""Exportação dos resultados de cada mês para o site (arquivos JSON pequenos, sem linhas individuais)."""
from __future__ import annotations

import io
import json
import math
import zipfile
from datetime import datetime

import pandas as pd

from . import __version__


def _limpa(v):
    """Converte para tipos JSON puros (NaN vira null)."""
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return None
    if hasattr(v, "item"):
        return _limpa(v.item())
    if v is pd.NA:
        return None
    return v


def _linhas(df: pd.DataFrame) -> list[dict]:
    return [{str(c): _limpa(v) for c, v in zip(df.columns, row)} for row in df.itertuples(index=False)]


def resumo_para_dict(d: dict) -> dict:
    """Tudo que o site precisa de UM mês, a partir do resultado de gerar_dados()."""
    r = d["resumo"]
    return {
        "versao_formato": 1,
        "gerado_em": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "gerado_por": f"Rio Dashboard {__version__}",
        "municipio": "Rio de Janeiro",
        "ano": int(d["ano"]),
        "mes": int(d["mes"]),
        "modelo": d["modelo"],
        "corte": _limpa(d["corte"]),
        "faltando": list(d["faltando"]),
        "n_linhas": int(r["n_linhas"]),
        "nao_ident": int(r["nao_ident"]),
        "total": {k: _limpa(v) for k, v in r["total"].items()},
        "setor": _linhas(r["setor"]),
        "sexo": _linhas(r["sexo"]),
        "raca": _linhas(r["raca"]),
        "deficiencia": _linhas(r["deficiencia"]),
        "escolaridade": _linhas(r["escolaridade"]),
        "idade": _linhas(r["idade"]),
        "sal_geral": {k: _limpa(v) for k, v in r["sal_geral"].items()},
        "sal_sexo": _linhas(r["sal_sexo"]),
        "sal_raca": _linhas(r["sal_raca"]),
        "sal_def": _linhas(r["sal_def"]),
    }


def nome_arquivo(ano: int, mes: int) -> str:
    return f"{ano}{mes:02d}.json"


def json_bytes(d: dict) -> bytes:
    return json.dumps(resumo_para_dict(d), ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def zip_bytes(arquivos: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for nome, conteudo in arquivos.items():
            z.writestr(nome, conteudo)
    return buf.getvalue()


def meses_do_intervalo(ano_i: int, mes_i: int, ano_f: int, mes_f: int) -> list[tuple[int, int]]:
    a, b = ano_i * 12 + mes_i - 1, ano_f * 12 + mes_f - 1
    return [(k // 12, k % 12 + 1) for k in range(a, b + 1)]
