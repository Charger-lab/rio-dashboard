"""Gráficos interativos (Plotly) e tabelas formatadas do boletim."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from .constantes import COR, MES_ABR, fmt_int, fmt_rs


def _titulo(txt: str) -> dict:
    return {"text": txt, "x": 0.5, "xanchor": "center", "font": {"size": 14, "color": COR["navy"]}}


def df_grupos(df: pd.DataFrame, col_cat: str) -> pd.DataFrame:
    return pd.DataFrame({"cat": df[col_cat].astype(str).values, "Admitidos": df["Admitidos"].values,
                         "Desligados": df["Desligados"].values, "Saldo": df["Saldo"].values})


def plot_grupos(df: pd.DataFrame, titulo: str, horizontal: bool = False) -> go.Figure:
    """df: colunas cat, Admitidos, Desligados, Saldo."""
    cats = list(df["cat"])
    fig = go.Figure()
    for nome, cor in (("Admitidos", COR["adm"]), ("Desligados", COR["des"]), ("Saldo", COR["saldo"])):
        v = list(df[nome])
        txt = [fmt_int(x) for x in v]
        if horizontal:
            fig.add_bar(x=v, y=cats, orientation="h", name=nome, marker_color=cor, text=txt,
                        textposition="outside", cliponaxis=False)
        else:
            fig.add_bar(x=cats, y=v, name=nome, marker_color=cor, text=txt,
                        textposition="outside", cliponaxis=False)
    fig.update_layout(
        title=_titulo(titulo), barmode="group", separators=",.", template="plotly_white",
        legend={"orientation": "h", "x": 0.5, "xanchor": "center", "y": 1.08},
        margin={"t": 70, "r": 60})
    if horizontal:
        fig.update_xaxes(title="", tickformat=",d", zeroline=True)
        fig.update_yaxes(title="", autorange="reversed", automargin=True,
                         categoryorder="array", categoryarray=cats)
    else:
        fig.update_xaxes(title="", categoryorder="array", categoryarray=cats)
        fig.update_yaxes(title="", tickformat=",d", zeroline=True)
    return fig


def plot_hist_setor(df: pd.DataFrame, mes: int, titulo: str) -> go.Figure:
    df = df.sort_values("ano")
    rot = [f"{MES_ABR[mes - 1]} {a}" for a in df["ano"]]
    cores = [COR["adm"] if s >= 0 else COR["des"] for s in df["Saldo"]]
    fig = go.Figure(go.Bar(x=rot, y=list(df["Saldo"]), marker_color=cores,
                           text=[fmt_int(x) for x in df["Saldo"]], textposition="outside", cliponaxis=False))
    fig.update_layout(title=_titulo(titulo), separators=",.", showlegend=False, template="plotly_white",
                      margin={"t": 60})
    fig.update_xaxes(title="", type="category")
    fig.update_yaxes(title="", tickformat=",d", zeroline=True)
    return fig


def plot_deficiencia(df: pd.DataFrame, titulo: str) -> go.Figure:
    cats = list(df["def_nome"])
    fig = go.Figure(go.Bar(x=list(df["Admitidos"]), y=cats, orientation="h", marker_color="#4C7DF0",
                           text=[fmt_int(x) for x in df["Admitidos"]], textposition="outside",
                           cliponaxis=False))
    fig.update_layout(title=_titulo(titulo), separators=",.", showlegend=False, template="plotly_white",
                      margin={"t": 60, "r": 60})
    fig.update_xaxes(title="", tickformat=",d")
    fig.update_yaxes(title="", autorange="reversed", automargin=True, categoryorder="array", categoryarray=cats)
    return fig


# ---- tabelas já formatadas -------------------------------------------------------------
def tab_mov(df: pd.DataFrame, rotulo: str) -> pd.DataFrame:
    return pd.DataFrame({rotulo: df.iloc[:, 0].values,
                         "Admissões": [fmt_int(x) for x in df["Admitidos"]],
                         "Desligamentos": [fmt_int(x) for x in df["Desligados"]],
                         "Saldo": [fmt_int(x) for x in df["Saldo"]]})


def tab_sal(df: pd.DataFrame, rotulo: str, nomes=("Média salarial", "Mediana salarial")) -> pd.DataFrame:
    return pd.DataFrame({rotulo: df.iloc[:, 0].values,
                         nomes[0]: [fmt_rs(x) for x in df["Media"]],
                         nomes[1]: [fmt_rs(x) for x in df["Mediana"]]})


def tab_indicadores(sal_geral: dict) -> pd.DataFrame:
    return pd.DataFrame({"Indicador": ["Salário Médio", "Salário Mediano"],
                         "Valor": [fmt_rs(sal_geral["Media"]), fmt_rs(sal_geral["Mediana"])]})


def tab_def_sal(df: pd.DataFrame) -> pd.DataFrame:
    t = tab_sal(df, "Tipo de deficiência")
    t.iloc[:, 0] = t.iloc[:, 0].replace({"Intelectual": "Intelectual (Mental)"})
    return t
