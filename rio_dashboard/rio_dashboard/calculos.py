"""Cálculos do boletim, a partir dos códigos originais do CAGED (espelha o dashboard em R).

A coluna 'peso' vale +1 (CAGEDMOV e CAGEDFOR) ou -1 (CAGEDEXC): exclusões descontam do saldo.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .constantes import (DEF_ORDEM, DIC_DEF, DIC_RACA, DIC_SEXO, ESC_ORDEM, FAIXAS_IDADE, SETORES)

NAO_IDENT = "Não identificado"
_SERVICOS = set("HIJKLMNOPQRSTU")


def setor_da_secao(secao: pd.Series) -> pd.Series:
    s = secao.astype(str).str.strip().str.upper()
    out = np.select(
        [s == "A", s.isin(list("BCDE")), s == "F", s == "G", s.isin(_SERVICOS)],
        ["Agropecuária", "Indústria", "Construção", "Comércio", "Serviços"],
        default=NAO_IDENT)
    return pd.Series(out, index=secao.index)


def grupo_escolaridade(g: pd.Series) -> pd.Series:
    g = pd.to_numeric(g, errors="coerce")
    out = np.select(
        [g == 1, g.isin([2, 3, 4]), g == 5, g == 6, g == 7, g == 8, g.isin([9, 10, 11, 80])],
        ["Analfabeto", "Fundamental Incompleto", "Fundamental Completo", "Médio Incompleto",
         "Médio Completo", "Superior Incompleto", "Superior Completo"],
        default=NAO_IDENT)
    return pd.Series(out, index=g.index)


def rotular(x: pd.Series, dic: dict) -> pd.Series:
    n = pd.to_numeric(x, errors="coerce")
    return n.map(dic).fillna(NAO_IDENT)


def agregar(d: pd.DataFrame, por: str) -> pd.DataFrame:
    t = pd.DataFrame({
        por: d[por].values,
        "Admitidos": (d["peso"] * (d["saldomovimentacao"] == 1)).values,
        "Desligados": (d["peso"] * (d["saldomovimentacao"] == -1)).values,
        "Saldo": (d["peso"] * d["saldomovimentacao"]).values})
    return t.groupby(por, sort=False, dropna=False, as_index=False).sum()


def completar(df: pd.DataFrame, col: str, niveis: list[str]) -> pd.DataFrame:
    out = df.set_index(col).reindex(niveis).reset_index()
    out = out.rename(columns={"index": col}) if col not in out.columns else out
    for j in ("Admitidos", "Desligados", "Saldo"):
        out[j] = out[j].fillna(0).astype(int)
    return out


def ordenar_por(df: pd.DataFrame, col: str, ordem: list[str]) -> pd.DataFrame:
    """Categorias na ordem dada; as que não constam na ordem vão para o fim (como no R)."""
    pos = df[col].map({v: i for i, v in enumerate(ordem)})
    pos = pos.fillna(len(ordem) + 1)
    return df.assign(_o=pos.values).sort_values("_o", kind="stable").drop(columns="_o").reset_index(drop=True)


def sal_stats(d: pd.DataFrame, por: str | None) -> pd.DataFrame:
    adm = d[(d["peso"] > 0) & (d["saldomovimentacao"] == 1) & d["salario"].notna() & (d["salario"] > 0)]
    if por is None:
        return pd.DataFrame({"Media": [adm["salario"].mean() if len(adm) else np.nan],
                             "Mediana": [adm["salario"].median() if len(adm) else np.nan],
                             "N": [len(adm)]})
    g = adm.groupby(por, sort=False, as_index=False)["salario"].agg(Media="mean", Mediana="median", N="size")
    return g


def _preparar(rio: pd.DataFrame) -> pd.DataFrame:
    d = rio.copy()
    if "peso" not in d.columns:
        d["peso"] = 1
    d["peso"] = d["peso"].astype(int)
    d["saldomovimentacao"] = pd.to_numeric(d["saldomovimentacao"], errors="coerce")
    d["setor"] = setor_da_secao(d["secao"])
    return d


def calc_setor(rio: pd.DataFrame) -> pd.DataFrame:
    d = _preparar(rio)
    st = completar(agregar(d, "setor"), "setor", SETORES)
    return st.rename(columns={"setor": "Setor"})


def calc_resumo(rio: pd.DataFrame) -> dict:
    d = _preparar(rio)
    d["sexo_nome"] = rotular(d["sexo"], DIC_SEXO)
    d["raca_nome"] = rotular(d["racacor"], DIC_RACA)
    d["def_nome"] = rotular(d["tipodedeficiencia"], DIC_DEF)
    d["esc"] = grupo_escolaridade(d["graudeinstrucao"])
    idade = pd.to_numeric(d["idade"], errors="coerce")
    d["faixa"] = pd.cut(idade, bins=[-np.inf, 17, 24, 29, 39, 49, 64, np.inf],
                        labels=FAIXAS_IDADE).astype(object)

    adm = d["peso"] * (d["saldomovimentacao"] == 1)
    des = d["peso"] * (d["saldomovimentacao"] == -1)
    total = {"Setor": "Total", "Admitidos": int(adm.sum()), "Desligados": int(des.sum()),
             "Saldo": int((d["peso"] * d["saldomovimentacao"]).sum())}

    setor = completar(agregar(d, "setor"), "setor", SETORES).rename(columns={"setor": "Setor"})
    sexo = ordenar_por(agregar(d, "sexo_nome"), "sexo_nome", ["Masculino", "Feminino"])
    raca = agregar(d, "raca_nome").sort_values("Admitidos", ascending=False, kind="stable").reset_index(drop=True)
    deff = ordenar_por(agregar(d, "def_nome"), "def_nome", DEF_ORDEM)
    niv_esc = ESC_ORDEM + ([NAO_IDENT] if (d["esc"] == NAO_IDENT).any() else [])
    esc = completar(agregar(d, "esc"), "esc", niv_esc)
    ida = completar(agregar(d[d["faixa"].notna()], "faixa"), "faixa", FAIXAS_IDADE)

    return {
        "n_linhas": len(d),
        "total": total,
        "setor": setor,
        "nao_ident": int(d.loc[d["setor"] == NAO_IDENT, "peso"].sum()),
        "sexo": sexo,
        "raca": raca,
        "deficiencia": deff,
        "escolaridade": esc,
        "idade": ida,
        "sal_geral": sal_stats(d, None).iloc[0].to_dict(),
        "sal_sexo": ordenar_por(sal_stats(d, "sexo_nome"), "sexo_nome", ["Masculino", "Feminino"]),
        "sal_raca": ordenar_por(sal_stats(d, "raca_nome"), "raca_nome", list(raca["raca_nome"])),
        "sal_def": ordenar_por(sal_stats(d, "def_nome"), "def_nome", DEF_ORDEM),
    }


def rotulo_modelo(modelo: str, corte: int | None = None) -> str:
    if modelo == "ajustes":
        base = "com ajustes (MOV + FOR - EXC)"
        if corte:
            return f"{base}, arquivos até {corte % 100:02d}/{corte // 100}"
        return base
    return "sem ajustes (somente CAGEDMOV)"
