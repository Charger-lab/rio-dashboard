"""Interface web local (Dash) do Rio Dashboard."""
from __future__ import annotations

import os
import threading
import time
import traceback
from datetime import date
from pathlib import Path

from dash import Dash, Input, Output, State, ctx, dcc, html, no_update

from . import graficos as G
from .calculos import rotulo_modelo
from .constantes import (COR, ELABORACAO, MES_ABR, MES_NOME, SETORES, TABELA_CATEGORIAS, fmt_int, fmt_rs)
from .dados import ErroCaged, Fonte, arquivos_cache, arquivos_pesados, gerar_dados, tamanho_fmt
from .exportar import json_bytes, meses_do_intervalo, nome_arquivo, zip_bytes
from .pdf import gerar_pdf, notas_metodologicas

NOMES_ABAS = ["Visão geral", "Por setor", "Salários", "Perfil demográfico", "Escolaridade", "Idade", "Metodologia"]
PASTA_PADRAO = str(Path.home() / "Rio Dashboard" / "dados")

# ---------------------------------------------------------------- estado do trabalho em andamento
JOB = {"status": "ocioso", "log": [], "v": 0.0, "detalhe": "", "res": None, "rev": 0, "erro": None,
       "zip": None, "tipo": "dash"}
_LOCK = threading.Lock()


def _log(m: str) -> None:
    linha = f"{time.strftime('%H:%M:%S')}  {m}"
    print(linha, flush=True)
    JOB["log"].append(linha)


def _prog(v: float, d: str) -> None:
    JOB["v"], JOB["detalhe"] = v, d


def _trabalho(args: dict) -> None:
    try:
        fonte = Fonte("ftp")
        res = gerar_dados(fonte, args["ano"], args["mes"], args["modelo"], args["pasta"], args["encoding"],
                          args["historico"], args["usar_cache"], args["apagar"], args["rapido"],
                          log=_log, prog=_prog)
        with _LOCK:
            JOB["res"] = res
            JOB["status"] = "pronto"
        _log("Dashboard pronto.")
    except ErroCaged as e:
        JOB["erro"] = str(e)
        JOB["status"] = "erro"
        _log("ERRO: " + str(e).splitlines()[0])
    except Exception as e:  # noqa: BLE001
        JOB["erro"] = f"Erro inesperado: {e}"
        JOB["status"] = "erro"
        _log("ERRO inesperado: " + traceback.format_exc().splitlines()[-1])
        print(traceback.format_exc(), flush=True)


def _trabalho_export(args: dict) -> None:
    """Gera vários meses e junta os JSON em um .zip (sem alterar o dashboard que está na tela)."""
    try:
        fonte = Fonte("ftp")
        meses = meses_do_intervalo(args["ano_i"], args["mes_i"], args["ano_f"], args["mes_f"])
        arquivos: dict[str, bytes] = {}
        falhas: list[str] = []
        for k, (a, m) in enumerate(meses):
            _log(f"Exportação {k + 1}/{len(meses)}: {MES_ABR[m - 1]}/{a}")
            try:
                d = gerar_dados(fonte, a, m, args["modelo"], args["pasta"], args["encoding"], False,
                                args["usar_cache"], args["apagar"], args["rapido"], log=_log,
                                prog=lambda v, t, k=k: _prog((k + v) / len(meses), f"{MES_ABR[m - 1]}/{a}: {t}"))
                arquivos[nome_arquivo(a, m)] = json_bytes(d)
            except Exception as e:  # noqa: BLE001
                falhas.append(f"{MES_ABR[m - 1]}/{a}")
                _log(f"AVISO: {MES_ABR[m - 1]}/{a} não foi exportado ({str(e).splitlines()[0]})")
        if not arquivos:
            raise ErroCaged("Nenhum mês pôde ser exportado. Veja o Andamento para saber o motivo.")
        JOB["zip"] = zip_bytes(arquivos)
        JOB["n_zip"] = len(arquivos)
        JOB["falhas_zip"] = falhas
        JOB["status"] = "pronto"
        _log(f"Exportação pronta: {len(arquivos)} mês(es)" + (f"; sem dados: {', '.join(falhas)}" if falhas else "."))
    except ErroCaged as e:
        JOB["erro"], JOB["status"] = str(e), "erro"
        _log("ERRO: " + str(e).splitlines()[0])
    except Exception as e:  # noqa: BLE001
        JOB["erro"], JOB["status"] = f"Erro inesperado: {e}", "erro"
        _log("ERRO inesperado: " + traceback.format_exc().splitlines()[-1])
        print(traceback.format_exc(), flush=True)


# ---------------------------------------------------------------- aparência
CSS = f"""
body {{ background:#f4f7fb; font-family:'Segoe UI',Arial,sans-serif; margin:0; color:#222; }}
.topo {{ background:linear-gradient(90deg,{COR['navy']},{COR['saldo']}); color:#fff; padding:18px 26px;
        border-bottom:4px solid {COR['cyan']}; }}
.topo .titulo {{ font-size:28px; font-weight:800; letter-spacing:.6px; text-transform:uppercase; }}
.topo .sub {{ font-size:15px; opacity:.9; margin-top:2px; }}
.corpo {{ display:flex; gap:18px; padding:18px; align-items:flex-start; }}
.lado {{ width:310px; flex:0 0 310px; background:#fff; border-radius:8px; padding:14px 16px;
        box-shadow:0 1px 3px rgba(0,0,0,.12); }}
.lado h4 {{ color:{COR['navy']}; margin:4px 0 10px; }}
.lado label.rot {{ display:block; font-weight:600; margin:10px 0 3px; font-size:13px; }}
.lado input[type=number], .lado input[type=text], .lado .Select-control {{ width:100%; box-sizing:border-box; padding:6px; }}
.ajuda {{ font-size:11.5px; color:#6b7a8c; margin:3px 0 8px; }}
.btn {{ background:{COR['navy']}; color:#fff; border:0; border-radius:6px; padding:12px; width:100%;
       font-size:16px; font-weight:700; cursor:pointer; margin-top:10px; }}
.btn:hover {{ background:{COR['saldo']}; }}
.btn-peq {{ background:#fff; color:{COR['navy']}; border:1px solid {COR['navy']}; border-radius:6px; padding:5px 10px;
          cursor:pointer; font-size:12px; margin-top:6px; }}
.btn-perigo {{ border-color:{COR['des']}; color:{COR['des']}; }}
.principal {{ flex:1; min-width:0; }}
.kpis {{ display:flex; gap:12px; flex-wrap:wrap; margin-bottom:16px; }}
.kpi {{ flex:1 1 170px; background:#fff; border-left:6px solid {COR['cyan']}; border-radius:6px;
       padding:12px 14px; box-shadow:0 1px 3px rgba(0,0,0,.12); }}
.kpi .t {{ font-size:12px; text-transform:uppercase; color:#5a6b80; letter-spacing:.4px; }}
.kpi .v {{ font-size:26px; font-weight:700; color:{COR['navy']}; }}
.kpi.pos {{ border-left-color:{COR['adm']}; }} .kpi.neg {{ border-left-color:{COR['des']}; }}
.bloco {{ background:#fff; border-radius:8px; padding:14px 16px; margin-bottom:16px; box-shadow:0 1px 3px rgba(0,0,0,.10); }}
.bloco h4 {{ color:{COR['navy']}; margin-top:0; }}
table.tab {{ width:100%; border-collapse:collapse; margin:6px 0 4px; font-size:14px; }}
table.tab th {{ background:{COR['navy']}; color:#fff; padding:7px; text-align:center; }}
table.tab td {{ padding:6px 8px; text-align:center; border:1px solid #dde3ec; }}
table.tab tr:nth-child(even) td {{ background:#f2f5fa; }}
.fonte {{ font-size:11px; color:#6b7a8c; font-style:italic; text-align:right; margin:4px 0 0; }}
.vazio {{ background:#fff; border-radius:8px; padding:40px; text-align:center; color:{COR['navy']};
         box-shadow:0 1px 3px rgba(0,0,0,.10); }}
.aviso {{ border-radius:6px; padding:10px 14px; margin-bottom:12px; font-size:14px; }}
.aviso.info {{ background:#e1f1fb; color:#0b4a7a; }} .aviso.warn {{ background:#fff3cd; color:#7a5b00; }}
.aviso.ok {{ background:#dff5e8; color:#0b6b3a; }} .aviso.erro {{ background:#fde2e3; color:#9b1c24; }}
.log {{ font-size:11px; max-height:240px; overflow:auto; white-space:pre-wrap; word-break:break-word;
       background:#f4f7fb; padding:6px; border-radius:4px; font-family:Consolas,monospace; }}
.barra {{ background:#dde3ec; border-radius:6px; height:14px; margin:8px 0 2px; overflow:hidden; }}
.barra > div {{ background:{COR['cyan']}; height:100%; transition:width .4s; }}
.tab-parent {{ margin-bottom:12px; }}
"""

INDEX = """<!DOCTYPE html><html><head>{%metas%}<title>Rio Dashboard</title>{%favicon%}{%css%}
<style>""" + CSS + """</style></head><body>{%app_entry%}<footer>{%config%}{%scripts%}{%renderer%}</footer></body></html>"""


def rotulo(txt):
    return html.Label(txt, className="rot")


def ajuda(txt):
    return html.Div(txt, className="ajuda")


def tabela_html(df) -> html.Table:
    return html.Table([html.Thead(html.Tr([html.Th(str(c)) for c in df.columns])),
                       html.Tbody([html.Tr([html.Td(str(v)) for v in row]) for row in df.itertuples(index=False)])],
                      className="tab")


def bloco(*filhos):
    return html.Div(list(filhos), className="bloco")


def rodape_fonte(d):
    return html.P(f"Elaboração: {ELABORACAO}     Fonte: Novo CAGED/MTE, {rotulo_modelo(d['modelo'], d['corte'])}",
                  className="fonte")


def graf(fig, altura):
    return dcc.Graph(figure=fig, style={"height": f"{altura}px"}, config={"displaylogo": False})


# ---------------------------------------------------------------- layout
def montar_layout():
    hoje = date.today()
    mes_p, ano_p = hoje.month - 2, hoje.year           # o MTE publica com ~1,5 mês de atraso
    if mes_p < 1:
        mes_p, ano_p = mes_p + 12, ano_p - 1
    lado = html.Div(className="lado", children=[
        html.H4("1. Escolha o período"),
        rotulo("Ano (digite)"),
        dcc.Input(id="ano", type="number", value=ano_p, min=2020, max=2100, step=1, debounce=False),
        rotulo("Mês"),
        dcc.Dropdown(id="mes", options=[{"label": n, "value": i + 1} for i, n in enumerate(MES_NOME)],
                     value=mes_p, clearable=False),
        rotulo("Modelo de cálculo"),
        dcc.RadioItems(id="modelo", value="ajustes", labelStyle={"display": "block", "margin": "4px 0"},
                       options=[{"label": " Oficial, com ajustes: MOV + FOR - EXC (recomendado)", "value": "ajustes"},
                                {"label": " Somente no prazo: CAGEDMOV", "value": "mov"}]),
        ajuda("O modelo oficial também lê os arquivos FOR (fora do prazo) e EXC (excluídas) de todos os meses "
              "publicados desde o mês escolhido."),
        dcc.Checklist(id="historico", value=["s"],
                      options=[{"label": " Incluir comparativo histórico por setor (2020 até o ano escolhido)", "value": "s"}]),
        ajuda("Repete o mesmo mês em cada ano anterior. A primeira vez pode demorar; depois fica em cache "
              "(só as linhas do Rio)."),
        rotulo("Pasta de trabalho (cache leve)"),
        dcc.Input(id="pasta", type="text", value=PASTA_PADRAO),
        rotulo("Codificação do arquivo"),
        dcc.Dropdown(id="encoding", options=["UTF-8", "Latin-1"], value="UTF-8", clearable=False),
        html.Div(style={"height": "8px"}),
        dcc.Checklist(id="opcoes", value=["rapido", "cache", "apagar"], labelStyle={"display": "block", "margin": "4px 0"},
                      options=[{"label": " Modo rápido (baixa vários arquivos ao mesmo tempo)", "value": "rapido"},
                               {"label": " Reaproveitar resultados já calculados (cache)", "value": "cache"},
                               {"label": " Apagar os arquivos baixados depois de gerar", "value": "apagar"}]),
        html.Button("Gerar dashboard", id="gerar", className="btn"),
        html.Div(id="disco"),
        html.Div(id="info_cache", className="ajuda", style={"marginTop": "10px"}),
        html.Button("Limpar cache...", id="limpar_cache", className="btn-peq btn-perigo"),
        html.Hr(),
        html.Div("Andamento", style={"fontWeight": 700}),
        html.Div(className="barra", children=html.Div(id="barra", style={"width": "0%"})),
        html.Div(id="detalhe", className="ajuda"),
        html.Div(id="log", className="log"),
        html.Hr(),
        html.Div("Exportar para o site", style={"fontWeight": 700}),
        ajuda("Gera os números de vários meses em arquivos pequenos (.json), para enviar ao GitHub. "
              "Usa o modelo, a fonte e as opções escolhidos acima."),
        html.Div(style={"display": "flex", "gap": "6px"}, children=[
            dcc.Input(id="exp_ano_i", type="number", value=ano_p, min=2020, max=2100, step=1, style={"width": "70px"}),
            dcc.Dropdown(id="exp_mes_i", options=[{"label": n[:3], "value": i + 1} for i, n in enumerate(MES_NOME)],
                         value=1, clearable=False, style={"width": "78px"}),
            html.Span("até", style={"alignSelf": "center"}),
            dcc.Input(id="exp_ano_f", type="number", value=ano_p, min=2020, max=2100, step=1, style={"width": "70px"}),
            dcc.Dropdown(id="exp_mes_f", options=[{"label": n[:3], "value": i + 1} for i, n in enumerate(MES_NOME)],
                         value=mes_p, clearable=False, style={"width": "78px"})]),
        html.Button("Gerar arquivos do site", id="exportar", className="btn-peq"),
        html.Div(id="exp_area"),
        html.Hr(),
        html.Button("Fechar o Rio Dashboard", id="fechar", className="btn-peq btn-perigo"),
    ])
    return html.Div([
        html.Div(className="topo", children=[html.Div("Boletim do Trabalho", className="titulo"),
                                            html.Div(id="subtitulo", className="sub")]),
        html.Div(className="corpo", children=[lado, html.Div(className="principal", children=[
            html.Div(id="painel"),
            html.Div(id="area_abas", style={"display": "none"}, children=[
                html.Div([html.Button("Baixar dados do site (.json)", id="baixar_json", className="btn-peq",
                                      style={"marginRight": "8px", "padding": "9px 14px", "fontSize": "14px"}),
                          html.Button("Baixar PDF", id="baixar_pdf", className="btn",
                                      style={"width": "auto", "padding": "8px 18px", "marginTop": 0})],
                         style={"textAlign": "right", "marginBottom": "6px"}),
                dcc.Tabs(id="abas", value="Visão geral", className="tab-parent", children=[
                    dcc.Tab(label=n, value=n, children=html.Div(id=f"aba_{i}", style={"paddingTop": "12px"}))
                    for i, n in enumerate(NOMES_ABAS)])])])]),
        dcc.Interval(id="tick", interval=700, disabled=True),
        dcc.Store(id="versao", data=0),
        dcc.Download(id="download_pdf"),
        dcc.Download(id="download_zip"),
        dcc.Download(id="download_json"),
        dcc.ConfirmDialog(id="confirma_limpar", message=""),
        dcc.ConfirmDialog(id="confirma_cache", message=""),
        dcc.ConfirmDialog(id="confirma_fechar", message="Fechar o Rio Dashboard? Esta janela do navegador deixará de funcionar."),
        html.Div(id="saida_vazia", style={"display": "none"}),
    ])


# ---------------------------------------------------------------- painel
def aviso_ajustes(d):
    if d["modelo"] != "ajustes":
        return html.Div("Modelo sem ajustes: só o CAGEDMOV, sem as declarações fora do prazo nem as exclusões. "
                        "Os números podem diferir do painel oficial do MTE.", className="aviso info")
    if d["faltando"]:
        return html.Div("Alguns arquivos FOR/EXC não puderam ser obtidos, então os ajustes podem estar incompletos: "
                        + ", ".join(d["faltando"]) + ". Gere o dashboard de novo mais tarde.", className="aviso warn")
    c = d["corte"]
    return html.Div(f"Modelo oficial com ajustes (MOV + FOR - EXC), com arquivos publicados até "
                    f"{'-' if not c else f'{c % 100:02d}/{c // 100}'}. O saldo deste mês pode mudar quando o MTE "
                    "publicar novos arquivos.", className="aviso ok")


def painel_vazio():
    return html.Div(className="vazio", children=[
        html.H3("Escolha o ano e o mês ao lado"),
        html.P(["O dashboard é montado depois que você clicar em ", html.B("Gerar dashboard"), "."]),
        html.P("Ele reproduz os gráficos e tabelas do Boletim do Trabalho para o município do Rio de Janeiro.")])


def montar_painel(d: dict) -> list:
    import pandas as pd
    r = d["resumo"]
    per = f"{MES_ABR[d['mes'] - 1]}/{d['ano']}"
    rod = rodape_fonte(d)
    saldo = r["total"]["Saldo"]
    sg = r["sal_geral"]
    g1 = pd.concat([r["setor"], pd.DataFrame([r["total"]])], ignore_index=True)
    obs = (html.P(f"Obs.: {fmt_int(r['nao_ident'])} movimentações sem seção CNAE identificada entram no Total, "
                  "mas não em nenhum setor.", className="fonte") if r["nao_ident"] > 0 else None)

    anos = sorted(d["hist"]["ano"].unique())
    if not d["historico"]:
        aviso_h = html.Div(f"O comparativo histórico está desativado: cada gráfico mostra só {per}. Marque a opção "
                           "na barra lateral e gere o dashboard novamente.", className="aviso warn")
    elif len(anos) < d["ano"] - 2020 + 1:
        aviso_h = html.Div("Alguns anos não puderam ser lidos e foram omitidos (veja o Andamento). Anos exibidos: "
                           + ", ".join(str(a) for a in anos) + ".", className="aviso warn")
    else:
        aviso_h = None

    tit_setor = ["2.1 Setor agropecuário", "2.2 Setor industrial", "2.3 Setor de construção civil",
                 "2.4 Setor comercial", "2.5 Setor de serviços"]
    gtit = ["Gráfico 2 - Comparativo do setor agropecuário", "Gráfico 3 - Comparativo do setor industrial",
            "Gráfico 4 - Comparativo do setor de construção civil", "Gráfico 5 - Comparativo do setor comercial",
            "Gráfico 6 - Comparativo do setor de serviços"]

    def kpi(t, v, cls=""):
        return html.Div(className=f"kpi {cls}", children=[html.Div(t, className="t"), html.Div(v, className="v")])

    visao = [aviso_ajustes(d),
             html.Div(className="kpis", children=[
                 kpi("Admitidos", fmt_int(r["total"]["Admitidos"]), "pos"),
                 kpi("Desligados", fmt_int(r["total"]["Desligados"]), "neg"),
                 kpi("Saldo", fmt_int(saldo), "pos" if saldo >= 0 else "neg"),
                 kpi("Salário médio (admitidos)", fmt_rs(sg["Media"])),
                 kpi("Salário mediano (admitidos)", fmt_rs(sg["Mediana"]))]),
             bloco(graf(G.plot_grupos(G.df_grupos(g1, "Setor"), f"Gráfico 1 - Saldo total de empregos formais ({per})"), 460),
                   rod, obs)]
    setores = [aviso_h] if aviso_h else []
    for k in range(5):
        setores.append(bloco(html.H4(tit_setor[k]),
                             graf(G.plot_hist_setor(d["hist"][d["hist"]["Setor"] == SETORES[k]], d["mes"], gtit[k]), 360), rod))
    salarios = [bloco(html.H4("3. Salários - perfil dos admitidos"),
                      html.B(f"Tabela 2 - Indicadores salariais (admitidos {per})"),
                      tabela_html(G.tab_indicadores(sg)), rod)]
    demografia = [
        bloco(html.H4("4. Perfil demográfico"),
              html.B(f"Tabela 3 - Admissões por gênero ({per})"), tabela_html(G.tab_mov(r["sexo"], "Gênero")), rod,
              html.B(f"Tabela 4 - Salário por gênero ({per})"), tabela_html(G.tab_sal(r["sal_sexo"], "Gênero")), rod),
        bloco(html.B(f"Tabela 5 - Admissões, Desligamentos e Saldo por raça/cor ({per})"),
              tabela_html(G.tab_mov(r["raca"], "Raça")), rod,
              html.B(f"Tabela 6 - Média, Mediana de Salário por raça/cor ({per})"),
              tabela_html(G.tab_sal(r["sal_raca"], "Raça", ("Média", "Mediana"))), rod),
        bloco(graf(G.plot_deficiencia(r["deficiencia"], f"Gráfico 7 - Admissões de pessoas com deficiência ({per})"), 380),
              rod, html.B(f"Tabela 7 - Média, Mediana de Salário por deficiência ({per})"),
              tabela_html(G.tab_def_sal(r["sal_def"])), rod)]
    escol = [bloco(html.H4("5. Escolaridade dos admitidos"),
                   graf(G.plot_grupos(G.df_grupos(r["escolaridade"], "esc"), f"Gráfico 8 - Escolaridade dos admitidos ({per})", True), 560), rod)]
    idade = [bloco(html.H4("6. Idade dos admitidos"),
                   graf(G.plot_grupos(G.df_grupos(r["idade"], "faixa"), f"Gráfico 9 - Idade dos admitidos ({per})", True), 560), rod)]
    cat = pd.DataFrame(TABELA_CATEGORIAS, columns=["Categoria", "Seções CNAE", "Descrição", "Exemplos"])
    metodo = [bloco(html.H4("Categorias do CAGED (Tabela 1)"), tabela_html(cat),
                    html.H4("Como os números são calculados"),
                    html.Ul([html.Li(n) for n in notas_metodologicas(d)]))]

    return [visao, setores, salarios, demografia, escol, idade, metodo]


# ---------------------------------------------------------------- app e callbacks
def criar_app() -> Dash:
    app = Dash(__name__, title="Rio Dashboard", index_string=INDEX, suppress_callback_exceptions=True,
               update_title=None)
    app.layout = montar_layout()

    @app.callback(Output("tick", "disabled"), Output("saida_vazia", "children"),
                  Input("gerar", "n_clicks"),
                  State("ano", "value"), State("mes", "value"), State("modelo", "value"),
                  State("historico", "value"),
                  State("pasta", "value"), State("encoding", "value"), State("opcoes", "value"),
                  prevent_initial_call=True)
    def _gerar(_n, ano, mes, modelo, hist, pasta, enc, opcoes):
        if JOB["status"] == "rodando":
            return no_update, no_update
        try:
            ano = int(ano)
        except (TypeError, ValueError):
            ano = 0
        if ano < 2020 or ano > 2100:
            JOB.update(status="erro", erro="Digite um ano válido (o Novo CAGED começa em 2020).", log=[], tipo="dash")
            return False, ""
        opcoes = opcoes or []
        JOB.update(status="rodando", log=[], v=0.0, detalhe="Iniciando...", erro=None, res=None, tipo="dash")
        args = dict(ano=ano, mes=int(mes), modelo=modelo, historico="s" in (hist or []),
                    pasta=(pasta or PASTA_PADRAO).strip(),
                    encoding=enc, usar_cache="cache" in opcoes, apagar="apagar" in opcoes, rapido="rapido" in opcoes)
        threading.Thread(target=_trabalho, args=(args,), daemon=True).start()
        return False, ""

    @app.callback(Output("tick", "disabled", allow_duplicate=True), Output("exp_area", "children", allow_duplicate=True),
                  Input("exportar", "n_clicks"),
                  State("exp_ano_i", "value"), State("exp_mes_i", "value"), State("exp_ano_f", "value"),
                  State("exp_mes_f", "value"), State("modelo", "value"),
                  State("pasta", "value"), State("encoding", "value"),
                  State("opcoes", "value"), prevent_initial_call=True)
    def _exportar(_n, ai, mi, af, mf, modelo, pasta, enc, opcoes):
        if JOB["status"] == "rodando":
            return no_update, no_update
        try:
            ai, mi, af, mf = int(ai), int(mi), int(af), int(mf)
        except (TypeError, ValueError):
            ai = af = 0
        if ai < 2020 or af < 2020 or (ai, mi) > (af, mf):
            JOB.update(status="erro", erro="Intervalo inválido: o ano começa em 2020 e o início deve vir antes do fim.", log=[], tipo="export")
            return False, ""
        opcoes = opcoes or []
        JOB.update(status="rodando", log=[], v=0.0, detalhe="Iniciando exportação...", erro=None, zip=None, tipo="export")
        args = dict(ano_i=ai, mes_i=mi, ano_f=af, mes_f=mf, modelo=modelo,
                    pasta=(pasta or PASTA_PADRAO).strip(),
                    encoding=enc, usar_cache="cache" in opcoes, apagar="apagar" in opcoes, rapido="rapido" in opcoes)
        threading.Thread(target=_trabalho_export, args=(args,), daemon=True).start()
        return False, ""

    @app.callback(Output("download_zip", "data"), Input("baixar_zip", "n_clicks"), prevent_initial_call=True)
    def _baixa_zip(n):
        if not n or not JOB.get("zip"):
            return no_update
        return dcc.send_bytes(JOB["zip"], "rio_dashboard_dados_do_site.zip")

    @app.callback(Output("download_json", "data"), Input("baixar_json", "n_clicks"), prevent_initial_call=True)
    def _baixa_json(n):
        d = JOB["res"]
        if not n or d is None:
            return no_update
        return dcc.send_bytes(json_bytes(d), nome_arquivo(d["ano"], d["mes"]))

    @app.callback(Output("barra", "style"), Output("detalhe", "children"), Output("log", "children"),
                  Output("tick", "disabled", allow_duplicate=True), Output("versao", "data"),
                  Output("disco", "children"), Output("exp_area", "children"),
                  Input("tick", "n_intervals"), State("pasta", "value"),
                  State("versao", "data"), prevent_initial_call=True)
    def _acompanhar(_n, pasta, versao_atual):
        st = JOB["status"]
        if st not in ("rodando", "pronto", "erro"):
            return no_update, no_update, no_update, True, no_update, no_update, no_update   # nada a fazer: para o relógio
        detalhe = JOB["detalhe"] if st == "rodando" else ("Concluído" if st == "pronto" else (JOB["erro"] or ""))
        log = "\n".join(JOB["log"][-60:])
        barra = {"width": f"{int(JOB['v'] * 100)}%"}
        if st == "rodando":
            return barra, detalhe, log, False, no_update, no_update, no_update
        # terminou: entrega o resultado uma única vez e para o relógio
        JOB["rev"] += 1
        JOB["status"] = "ocioso_" + st
        disco = []
        arqs = arquivos_pesados(pasta or PASTA_PADRAO)
        if arqs:
            tam = sum(a.stat().st_size for a in arqs)
            disco = [html.Div(f"{len(arqs)} arquivo(s) pesado(s) na pasta, ocupando {tamanho_fmt(tam)}.", className="ajuda"),
                     html.Button("Apagar arquivos pesados...", id="limpar", className="btn-peq btn-perigo")]
        exp = []
        if st == "pronto" and JOB.get("tipo") == "export" and JOB.get("zip"):
            exp = [html.Div(f"{JOB.get('n_zip', 0)} mês(es) pronto(s)."
                            + (f" Sem dados: {', '.join(JOB['falhas_zip'])}." if JOB.get("falhas_zip") else ""),
                            className="ajuda"),
                   html.Button("Baixar arquivos do site (.zip)", id="baixar_zip", className="btn-peq")]
        return barra, detalhe, log, True, JOB["rev"], disco, exp

    @app.callback(Output("painel", "children"), Output("area_abas", "style"), Output("subtitulo", "children"),
                  *[Output(f"aba_{i}", "children") for i in range(len(NOMES_ABAS))],
                  Input("versao", "data"))
    def _painel(_versao):
        vazio = [no_update] * len(NOMES_ABAS)
        if JOB.get("tipo") == "export":                 # exportar não mexe no dashboard que está na tela
            return (no_update,) * (3 + len(NOMES_ABAS))
        if JOB["status"] == "ocioso_erro":
            return (html.Div(["Não foi possível gerar o dashboard.", html.Br(), html.Br(), JOB["erro"] or ""],
                             className="aviso erro", style={"whiteSpace": "pre-wrap"}),
                    {"display": "none"}, "Escolha o período para gerar o dashboard", *vazio)
        d = JOB["res"]
        if d is None:
            return painel_vazio(), {"display": "none"}, "Escolha o período para gerar o dashboard", *vazio
        return ("", {"display": "block"},
                f"{MES_NOME[d['mes'] - 1]} de {d['ano']}  ·  Município do Rio de Janeiro", *montar_painel(d))

    @app.callback(Output("download_pdf", "data"), Input("baixar_pdf", "n_clicks"), prevent_initial_call=True)
    def _pdf(n):
        d = JOB["res"]
        if not n or d is None:
            return no_update
        return dcc.send_bytes(gerar_pdf(d), f"boletim_trabalho_rio_{d['ano']}{d['mes']:02d}.pdf")

    @app.callback(Output("confirma_limpar", "displayed"), Output("confirma_limpar", "message"),
                  Input("limpar", "n_clicks"), State("pasta", "value"), prevent_initial_call=True)
    def _pede_limpar(n, pasta):
        if not n:
            return no_update, no_update
        arqs = arquivos_pesados(pasta or PASTA_PADRAO)
        if not arqs:
            return no_update, no_update
        lista = "\n".join(f"{a.name} ({tamanho_fmt(a.stat().st_size)})" for a in arqs[:15])
        return True, ("Apagar arquivos pesados? Serão apagados só os downloads do CAGED (.7z) desta pasta de trabalho; "
                      "eles podem ser baixados de novo. O cache leve e o resto da pasta não são tocados.\n\n" + lista)

    @app.callback(Output("detalhe", "children", allow_duplicate=True), Input("confirma_limpar", "submit_n_clicks"),
                  State("pasta", "value"), prevent_initial_call=True)
    def _limpar(n, pasta):
        if not n:
            return no_update
        arqs = arquivos_pesados(pasta or PASTA_PADRAO)
        tam = sum(a.stat().st_size for a in arqs)
        for a in arqs:
            a.unlink(missing_ok=True)
        return f"{len(arqs)} arquivo(s) apagado(s); {tamanho_fmt(tam)} liberados."

    @app.callback(Output("info_cache", "children"), Input("versao", "data"), Input("pasta", "value"),
                  Input("confirma_cache", "submit_n_clicks"))
    def _info_cache(_v, pasta, _n):
        arqs = arquivos_cache(pasta or PASTA_PADRAO)
        if not arqs:
            return "Cache: vazio."
        return f"Cache: {len(arqs)} arquivo(s), {tamanho_fmt(sum(a.stat().st_size for a in arqs))}."

    @app.callback(Output("confirma_cache", "displayed"), Output("confirma_cache", "message"),
                  Input("limpar_cache", "n_clicks"), State("pasta", "value"), prevent_initial_call=True)
    def _pede_limpar_cache(n, pasta):
        if not n:
            return no_update, no_update
        arqs = arquivos_cache(pasta or PASTA_PADRAO)
        if not arqs:
            return True, "O cache já está vazio."
        return True, (f"Limpar o cache? Serão apagados {len(arqs)} arquivo(s) ({tamanho_fmt(sum(a.stat().st_size for a in arqs))}) "
                      "com os resultados já calculados do Rio. Na próxima geração o app lê os arquivos do MTE de novo, "
                      "então o primeiro carregamento será mais demorado. O dashboard na tela não muda.")

    @app.callback(Output("detalhe", "children", allow_duplicate=True), Input("confirma_cache", "submit_n_clicks"),
                  State("pasta", "value"), prevent_initial_call=True)
    def _limpar_cache(n, pasta):
        if not n:
            return no_update
        arqs = arquivos_cache(pasta or PASTA_PADRAO)
        tam = sum(a.stat().st_size for a in arqs)
        for a in arqs:
            a.unlink(missing_ok=True)
        return f"Cache limpo: {len(arqs)} arquivo(s) apagado(s), {tamanho_fmt(tam)} liberados."

    @app.callback(Output("confirma_fechar", "displayed"), Input("fechar", "n_clicks"), prevent_initial_call=True)
    def _pede_fechar(n):
        return bool(n)

    @app.callback(Output("saida_vazia", "children", allow_duplicate=True),
                  Input("confirma_fechar", "submit_n_clicks"), prevent_initial_call=True)
    def _fechar(n):
        if n:
            threading.Timer(0.6, lambda: os._exit(0)).start()
        return no_update

    return app
