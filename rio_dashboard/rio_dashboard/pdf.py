"""PDF do boletim (5 páginas A4) desenhado com matplotlib."""
from __future__ import annotations

import io
import textwrap

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.backends.backend_pdf import PdfPages  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

from .calculos import rotulo_modelo  # noqa: E402
from .constantes import (COR, ELABORACAO, MES_ABR, MES_NOME, SETORES, fmt_int, fmt_rs)  # noqa: E402
from .graficos import df_grupos, tab_def_sal, tab_indicadores, tab_mov, tab_sal  # noqa: E402

W, H = 8.27, 11.69
CINZA = "#6b7a8c"
plt.rcParams["font.family"] = "DejaVu Sans"


class Pagina:
    """Página A4 com um canvas em polegadas (origem embaixo à esquerda, como no R)."""

    def __init__(self):
        self.fig = plt.figure(figsize=(W, H))
        self.ax = self.fig.add_axes([0, 0, 1, 1])
        self.ax.set_xlim(0, W)
        self.ax.set_ylim(0, H)
        self.ax.axis("off")

    def rect(self, x0, y0, x1, y1, cor, borda=None):
        self.ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, facecolor=cor,
                                    edgecolor=borda or "none", linewidth=0.6))

    def txt(self, x, y, s, size=8, cor="black", bold=False, ha="left", va="center"):
        self.ax.text(x, y, s, fontsize=size, color=cor, fontweight="bold" if bold else "normal",
                     ha=ha, va=va)

    def eixos(self, x0, x1, ybot, ytop):
        return self.fig.add_axes([x0 / W, ybot / H, (x1 - x0) / W, (ytop - ybot) / H])

    def cabecalho(self, titulo, sub=None, grande=False):
        alt = 1.25 if grande else 0.7
        self.rect(0, H - alt, W, H, COR["navy"])
        self.rect(0, H - alt - 0.06, W, H - alt, COR["cyan"])
        self.txt(0.5, H - alt * 0.40, titulo, size=22 if grande else 13, cor="white", bold=True)
        if sub:
            self.txt(0.5, H - alt * 0.80, sub, size=9.5 if grande else 7.5, cor="white")
        return H - alt - 0.40

    def rodape(self, pagina, texto):
        self.txt(0.5, 0.35, texto, size=5.5, cor=CINZA)
        self.txt(W - 0.5, 0.35, f"Página {pagina}", size=5.5, cor=CINZA, ha="right")

    def tabela(self, df, y, titulo=None, x0=0.5, larg=W - 1, alt_lin=0.27):
        if titulo:
            self.txt(x0, y, titulo, size=7.5, cor=COR["navy"], bold=True)
            y -= 0.22
        k = df.shape[1]
        ws = [larg * 0.28] + [larg * 0.72 / (k - 1)] * (k - 1) if k > 2 else [larg / k] * k
        xs = [x0]
        for w in ws:
            xs.append(xs[-1] + w)
        self.rect(x0, y - alt_lin, x0 + larg, y, COR["navy"])
        for j in range(k):
            self.txt((xs[j] + xs[j + 1]) / 2, y - alt_lin / 2, str(df.columns[j]), size=6.8, cor="white",
                     bold=True, ha="center")
        y -= alt_lin
        for i in range(len(df)):
            if i % 2 == 1:
                self.rect(x0, y - alt_lin, x0 + larg, y, "#EEF2F8")
            for j in range(k):
                self.txt((xs[j] + xs[j + 1]) / 2, y - alt_lin / 2, str(df.iloc[i, j]), size=6.8, ha="center")
            y -= alt_lin
        self.ax.plot([x0, x0 + larg], [y, y], color=COR["navy"], linewidth=0.8)
        return y - 0.32


def _limites(vals):
    lo = min(0, min(vals)) * 1.3
    hi = max(0, max(vals)) * 1.22
    return (-1, 1) if lo == hi else (lo, hi)


def _fmt_eixo(ax, horizontal):
    f = lambda v, _p: fmt_int(v)  # noqa: E731
    (ax.xaxis if horizontal else ax.yaxis).set_major_formatter(plt.FuncFormatter(f))
    ax.tick_params(labelsize=6.5)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)


def barras_grupo(pg: Pagina, df, titulo, horizontal, regiao):
    x0, x1, yb, yt = regiao
    cats = list(df["cat"])
    series = [("Admitidos", COR["adm"]), ("Desligados", COR["des"]), ("Saldo", COR["saldo"])]
    todos = [v for n, _ in series for v in df[n]]
    lo, hi = _limites(todos)
    if horizontal:
        ax = pg.eixos(x0 + 1.9, x1 - 0.5, yb + 0.35, yt - 0.9)
        n = len(cats)
        for s, (nome, cor) in enumerate(series):
            ys = [i + (s - 1) * 0.26 for i in range(n)]
            ax.barh(ys, list(df[nome]), height=0.25, color=cor, label=nome)
            for y_, v in zip(ys, df[nome]):
                ax.text(v, y_, " " + fmt_int(v) + " ", fontsize=5.5, va="center", ha="left" if v >= 0 else "right")
        ax.set_yticks(range(n))
        ax.set_yticklabels(cats)
        ax.invert_yaxis()
        ax.set_xlim(lo, hi)
        ax.axvline(0, color="#444444", linewidth=0.6)
        _fmt_eixo(ax, True)
    else:
        ax = pg.eixos(x0 + 0.6, x1 - 0.2, yb + 0.5, yt - 0.9)
        n = len(cats)
        for s, (nome, cor) in enumerate(series):
            xs = [i + (s - 1) * 0.26 for i in range(n)]
            ax.bar(xs, list(df[nome]), width=0.25, color=cor, label=nome)
            for x_, v in zip(xs, df[nome]):
                ax.text(x_, v, fmt_int(v), fontsize=5.5, ha="center", va="bottom" if v >= 0 else "top")
        ax.set_xticks(range(n))
        ax.set_xticklabels(cats, fontsize=6.5)
        ax.set_ylim(lo, hi)
        ax.axhline(0, color="#444444", linewidth=0.6)
        _fmt_eixo(ax, False)
    ax.set_title(titulo, fontsize=8, fontweight="bold", color=COR["navy"], pad=26)
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=3, frameon=False, fontsize=6.5)


def barras_hist(pg: Pagina, df, mes, titulo, regiao):
    x0, x1, yb, yt = regiao
    df = df.sort_values("ano")
    v = list(df["Saldo"])
    ax = pg.eixos(x0 + 0.55, x1 - 0.1, yb + 0.45, yt - 0.45)
    xs = range(len(v))
    ax.bar(xs, v, color=[COR["adm"] if s >= 0 else COR["des"] for s in v], width=0.7)
    for x_, s in zip(xs, v):
        ax.text(x_, s, fmt_int(s), fontsize=5.5, ha="center", va="bottom" if s >= 0 else "top")
    ax.set_xticks(list(xs))
    ax.set_xticklabels([f"{MES_ABR[mes - 1]}\n{a}" for a in df["ano"]], fontsize=6)
    lo, hi = _limites(v)
    ax.set_ylim(lo, hi)
    ax.axhline(0, color="#444444", linewidth=0.6)
    _fmt_eixo(ax, False)
    ax.set_title(titulo, fontsize=6.8, fontweight="bold", color=COR["navy"], pad=6)


def barras_def(pg: Pagina, df, titulo, regiao):
    x0, x1, yb, yt = regiao
    ax = pg.eixos(x0 + 1.4, x1 - 0.6, yb + 0.3, yt - 0.5)
    cats = list(df["def_nome"])
    v = list(df["Admitidos"])
    ax.barh(range(len(v)), v, color="#4C7DF0", height=0.7)
    for i, x_ in enumerate(v):
        ax.text(x_, i, " " + fmt_int(x_), fontsize=6, va="center")
    ax.set_yticks(range(len(v)))
    ax.set_yticklabels(cats)
    ax.invert_yaxis()
    ax.set_xlim(0, max(1, max(v)) * 1.18)
    _fmt_eixo(ax, True)
    ax.set_title(titulo, fontsize=8, fontweight="bold", color=COR["navy"], pad=6)


def gerar_pdf(d: dict) -> bytes:
    r = d["resumo"]
    periodo = f"{MES_ABR[d['mes'] - 1]}/{d['ano']}"
    sub = f"{MES_NOME[d['mes'] - 1]} de {d['ano']}  |  Município do Rio de Janeiro"
    rod = f"Elaboração: {ELABORACAO}     Fonte: Novo CAGED/MTE, {rotulo_modelo(d['modelo'], d['corte'])}"
    buf = io.BytesIO()
    with PdfPages(buf) as pdf:
        def salvar(pg):
            pdf.savefig(pg.fig)
            plt.close(pg.fig)

        # ---- Página 1: visão geral
        pg = Pagina()
        y = pg.cabecalho("BOLETIM DO TRABALHO", sub, grande=True)
        saldo = r["total"]["Saldo"]
        kp = [("ADMITIDOS", fmt_int(r["total"]["Admitidos"]), COR["adm"]),
              ("DESLIGADOS", fmt_int(r["total"]["Desligados"]), COR["des"]),
              ("SALDO", fmt_int(saldo), COR["adm"] if saldo >= 0 else COR["des"]),
              ("SALÁRIO MÉDIO", fmt_rs(r["sal_geral"]["Media"]), COR["cyan"]),
              ("SALÁRIO MEDIANO", fmt_rs(r["sal_geral"]["Mediana"]), COR["cyan"])]
        bw = (W - 1 - 4 * 0.12) / 5
        for k, (t, v, c) in enumerate(kp):
            x = 0.5 + k * (bw + 0.12)
            pg.rect(x, y - 0.85, x + bw, y, "white", "#d5dbe5")
            pg.rect(x, y - 0.85, x + 0.07, y, c)
            pg.txt(x + 0.17, y - 0.25, t, size=5, cor="#5a6b80")
            pg.txt(x + 0.17, y - 0.58, v, size=9.5, cor=COR["navy"], bold=True)
        pg.txt(0.5, y - 1.05, "Salário médio e mediano: admitidos com salário informado maior que zero.",
               size=5.5, cor=CINZA)
        import pandas as pd
        g1 = pd.concat([r["setor"], pd.DataFrame([r["total"]])], ignore_index=True)
        barras_grupo(pg, df_grupos(g1, "Setor"), f"Gráfico 1 - Saldo total de empregos formais ({periodo})",
                     False, (0.5, W - 0.5, y - 6.5, y - 1.3))
        if r["nao_ident"] > 0:
            pg.txt(0.5, y - 6.7, f"Obs.: {fmt_int(r['nao_ident'])} movimentações sem seção CNAE identificada "
                   "entram no Total, mas não em nenhum setor.", size=5.5, cor=CINZA)
        pg.rodape(1, rod)
        salvar(pg)

        # ---- Página 2: setores
        pg = Pagina()
        y = pg.cabecalho("Análise por setor", sub)
        tit = ["Gráfico 2 - Comparativo do setor agropecuário", "Gráfico 3 - Comparativo do setor industrial",
               "Gráfico 4 - Comparativo do setor de construção civil", "Gráfico 5 - Comparativo do setor comercial",
               "Gráfico 6 - Comparativo do setor de serviços"]
        for k in range(5):
            x1 = 0.5 + (k % 2) * 3.75
            yt = y - (k // 2) * 3.3
            barras_hist(pg, d["hist"][d["hist"]["Setor"] == SETORES[k]], d["mes"], tit[k],
                        (x1, x1 + 3.55, yt - 3.05, yt))
        if d["historico"]:
            t6 = ["Saldo do mesmo mês em cada ano.", "Verde = saldo positivo; vermelho = negativo."]
        else:
            t6 = ["Comparativo histórico desativado:", f"cada gráfico mostra só {periodo}."]
        pg.txt(4.25, y - 2 * 3.3 - 1.4, t6[0], size=6.5, cor="#5a6b80")
        pg.txt(4.25, y - 2 * 3.3 - 1.65, t6[1], size=6.5, cor="#5a6b80")
        pg.rodape(2, rod)
        salvar(pg)

        # ---- Página 3: salários e perfil
        pg = Pagina()
        y = pg.cabecalho("Salários e perfil demográfico", sub)
        y = pg.tabela(tab_indicadores(r["sal_geral"]), y, f"Tabela 2 - Indicadores salariais (admitidos {periodo})", larg=4)
        y = pg.tabela(tab_mov(r["sexo"], "Gênero"), y, f"Tabela 3 - Admissões por gênero ({periodo})")
        y = pg.tabela(tab_sal(r["sal_sexo"], "Gênero"), y, f"Tabela 4 - Salário por gênero ({periodo})")
        y = pg.tabela(tab_mov(r["raca"], "Raça"), y,
                      f"Tabela 5 - Admissões, Desligamentos e Saldo por raça/cor ({periodo})")
        y = pg.tabela(tab_sal(r["sal_raca"], "Raça", ("Média", "Mediana")), y,
                      f"Tabela 6 - Média, Mediana de Salário por raça/cor ({periodo})")
        pg.rodape(3, rod)
        salvar(pg)

        # ---- Página 4: deficiência e escolaridade
        pg = Pagina()
        y = pg.cabecalho("Deficiência e escolaridade", sub)
        barras_def(pg, r["deficiencia"], f"Gráfico 7 - Admissões de pessoas com deficiência ({periodo})",
                   (0.5, W - 0.5, y - 3.0, y))
        y -= 3.2
        y = pg.tabela(tab_def_sal(r["sal_def"]), y, f"Tabela 7 - Média, Mediana de Salário por deficiência ({periodo})")
        barras_grupo(pg, df_grupos(r["escolaridade"], "esc"), f"Gráfico 8 - Escolaridade dos admitidos ({periodo})",
                     True, (0.5, W - 0.5, 0.7, max(2.5, y)))
        pg.rodape(4, rod)
        salvar(pg)

        # ---- Página 5: idade e notas
        pg = Pagina()
        y = pg.cabecalho("Idade dos admitidos", sub)
        barras_grupo(pg, df_grupos(r["idade"], "faixa"), f"Gráfico 9 - Idade dos admitidos ({periodo})",
                     True, (0.5, W - 0.5, y - 5.2, y))
        y -= 5.6
        pg.txt(0.5, y, "Notas metodológicas", size=8, cor=COR["navy"], bold=True)
        notas = notas_metodologicas(d)
        linhas = []
        for n in notas:
            linhas += textwrap.wrap("- " + n, width=125, subsequent_indent="  ")
        for i, l in enumerate(linhas):
            pg.txt(0.5, y - 0.28 - i * 0.2, l, size=6.2, cor="#333333")
        pg.rodape(5, rod)
        salvar(pg)
    return buf.getvalue()


def notas_metodologicas(d: dict) -> list[str]:
    aj = d["modelo"] == "ajustes"
    n = ["Admitido = movimentação com saldo +1; desligado = saldo -1; saldo = admitidos - desligados.",
         "Município do Rio de Janeiro (código IBGE 330455).",
         "Setores pela seção CNAE: Agropecuária (A), Indústria (B a E), Construção (F), Comércio (G) e Serviços (H a U).",
         "Salário médio e mediano: somente admitidos com salário informado maior que zero."]
    if aj:
        n.append("No modelo com ajustes, os salários usam MOV e FOR; as exclusões não são descontadas dos salários.")
    n.append("Escolaridade: Fundamental Incompleto = até o 9º ano incompleto; Superior Completo inclui mestrado, doutorado e pós-graduação.")
    n.append(f"Modelo de cálculo: Novo CAGED {rotulo_modelo(d['modelo'], d['corte'])}.")
    if aj:
        n.append("Saldo = CAGEDMOV + CAGEDFOR - CAGEDEXC; o resultado pode mudar quando o MTE publica novos arquivos.")
    n.append("Comparativo histórico: o mesmo mês de cada ano, de 2020 até o ano escolhido." if d["historico"]
             else "Comparativo histórico não incluído nesta versão.")
    return n
