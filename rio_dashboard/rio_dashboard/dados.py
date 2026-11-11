"""Download, leitura e cache dos arquivos do Novo CAGED (somente o município do Rio de Janeiro)."""
from __future__ import annotations

import ftplib
import os
import shutil
import subprocess
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path
from typing import Callable

import pandas as pd

from .calculos import calc_resumo, calc_setor
from .constantes import COD_MUN_RIO, COLS_NECESSARIAS, MES_ABR, VERSAO_CACHE, fmt_int

FTP_HOST = os.environ.get("RIO_FTP_HOST", "ftp.mtps.gov.br")
FTP_PORT = int(os.environ.get("RIO_FTP_PORT", "21"))
FTP_BASE = "/pdet/microdados/NOVO CAGED"

Log = Callable[[str], None]
Prog = Callable[[float, str], None]


class ErroCaged(Exception):
    """Erro com mensagem pronta para mostrar ao usuário."""


def _nada_log(_m: str) -> None:
    pass


def _nada_prog(_v: float, _d: str) -> None:
    pass


# ------------------------------------------------------------------ nomes e caminhos
def comp_str(ano: int, mes: int) -> str:
    return f"{ano}{mes:02d}"


def nome_7z(tipo: str, ano: int, mes: int) -> str:
    return f"{tipo}{comp_str(ano, mes)}.7z"


def caminho_cache(pasta: Path, tipo: str, ano: int, mes: int) -> Path:
    return pasta / f"rio_{VERSAO_CACHE}_{tipo}{comp_str(ano, mes)}.pkl.gz"


# ------------------------------------------------------------------ download
def baixar_ftp(ano: int, mes: int, tipo: str, destino: Path) -> None:
    """Baixa um arquivo do FTP do MTE para 'destino' (via .part, para nunca deixar arquivo pela metade)."""
    comp = comp_str(ano, mes)
    parcial = destino.with_name(destino.name + ".part")
    try:
        with ftplib.FTP() as ftp:
            ftp.connect(FTP_HOST, FTP_PORT, timeout=60)     # 60 s sem receber nada = desiste
            ftp.login()
            ftp.set_pasv(True)
            ftp.cwd(f"{FTP_BASE}/{ano}/{comp}")
            with open(parcial, "wb") as f:
                ftp.retrbinary(f"RETR {nome_7z(tipo, ano, mes)}", f.write, blocksize=1 << 20)
        os.replace(parcial, destino)
    except Exception as e:  # noqa: BLE001
        parcial.unlink(missing_ok=True)
        raise ErroCaged(
            f"Falha no download de {destino.name}.\n"
            f"Possíveis causas: a competência {comp} ainda não foi divulgada, o FTP do MTE está fora do ar, "
            f"ou um firewall/antivírus bloqueia o FTP.\n"
            f"Alternativa: baixe o arquivo manualmente (ftp://ftp.mtps.gov.br/pdet/microdados/NOVO%20CAGED/"
            f"{ano}/{comp}/{destino.name}) e use a fonte 'Pasta no computador'.\nErro: {e}") from e


def extrair_7z(arquivo: Path, pasta_saida: Path) -> Path:
    """Extrai o .7z e devolve o caminho do .txt."""
    pasta_saida.mkdir(parents=True, exist_ok=True)
    ok = False
    try:
        import py7zr
        with py7zr.SevenZipFile(arquivo, "r") as z:
            z.extractall(path=pasta_saida)
        ok = True
    except Exception:  # noqa: BLE001
        sete = shutil.which("7z") or shutil.which("7za") or shutil.which("7zr")
        if sete:
            r = subprocess.run([sete, "x", str(arquivo), f"-o{pasta_saida}", "-y"],
                               capture_output=True)
            ok = r.returncode == 0
    txts = sorted(pasta_saida.rglob("*.txt"))
    if not ok or not txts:
        raise ErroCaged(f"Não consegui descompactar {arquivo.name}. O arquivo pode estar incompleto; "
                        "apague-o e tente de novo.")
    return txts[0]


# ------------------------------------------------------------------ leitura (só o Rio)
def _normaliza(nome: str) -> str:
    s = unicodedata.normalize("NFKD", nome.strip().lower())
    return "".join(c for c in s if not unicodedata.combining(c))


def ler_rio(txt: Path, encoding: str = "UTF-8") -> pd.DataFrame:
    cab = pd.read_csv(txt, sep=";", nrows=0, encoding=encoding, dtype=str)
    std = [_normaliza(c) for c in cab.columns]
    faltam = [c for c in COLS_NECESSARIAS if c not in std]
    if faltam:
        raise ErroCaged("Colunas não encontradas no arquivo: " + ", ".join(faltam) +
                        ". Se os acentos estiverem errados, tente a codificação 'Latin-1'.")
    idx = [i for i, c in enumerate(std) if c in COLS_NECESSARIAS]
    nomes = [std[i] for i in idx]
    partes = []
    for ch in pd.read_csv(txt, sep=";", encoding=encoding, dtype=str, usecols=idx,
                          chunksize=400_000, header=0):
        ch.columns = [std[i] for i in sorted(idx)]            # usecols mantém a ordem do arquivo
        mun = pd.to_numeric(ch["municipio"], errors="coerce")
        sel = ch[mun == COD_MUN_RIO]
        if len(sel):
            partes.append(sel)
    d = pd.concat(partes, ignore_index=True) if partes else pd.DataFrame(columns=sorted(nomes, key=std.index))
    for c in ("competenciamov", "saldomovimentacao", "idade", "graudeinstrucao", "racacor", "sexo",
              "tipodedeficiencia", "municipio"):
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d["salario"] = pd.to_numeric(d["salario"].astype(str).str.replace(",", ".", regex=False), errors="coerce")
    d["competenciamov"] = d["competenciamov"].astype("Int64")
    return d.reset_index(drop=True)


# ------------------------------------------------------------------ um arquivo -> linhas do Rio (cache)
class Fonte:
    """De onde vêm os .7z: 'ftp' (MTE) ou 'pasta' (uma pasta no computador, p.ex. a do Google Drive)."""

    def __init__(self, tipo: str = "ftp", pasta_arquivos: str | Path | None = None):
        self.tipo = tipo
        self.pasta_arquivos = Path(pasta_arquivos) if pasta_arquivos else None


def obter_7z(fonte: Fonte, tipo: str, ano: int, mes: int, pasta: Path, log: Log) -> tuple[Path, bool]:
    """Devolve (caminho do .7z, se_foi_baixado_por_nos). Arquivos da pasta do usuário nunca são apagados."""
    nome = nome_7z(tipo, ano, mes)
    if fonte.tipo == "pasta":
        if not fonte.pasta_arquivos or not fonte.pasta_arquivos.is_dir():
            raise ErroCaged("Escolha uma pasta válida com os arquivos .7z do MTE.")
        achados = list(fonte.pasta_arquivos.rglob(nome))
        if not achados:
            raise ErroCaged(f"O arquivo '{nome}' não está na pasta '{fonte.pasta_arquivos}'. "
                            "Coloque o .7z original do MTE nessa pasta e tente de novo.")
        return achados[0], False
    destino = pasta / nome
    if destino.exists():
        log(f"[{comp_str(ano, mes)}] {nome} já existe; pulando download.")
        return destino, destino in _PREBAIXADOS
    log(f"[{comp_str(ano, mes)}] Baixando {nome}...")
    baixar_ftp(ano, mes, tipo, destino)
    return destino, True


_PREBAIXADOS: set[Path] = set()


def rio_do_arquivo(fonte: Fonte, tipo: str, ano: int, mes: int, pasta: Path, encoding: str,
                   usar_cache: bool, apagar: bool, log: Log = _nada_log) -> pd.DataFrame:
    cache = caminho_cache(pasta, tipo, ano, mes)
    if usar_cache and cache.exists():
        return pd.read_pickle(cache)
    pasta.mkdir(parents=True, exist_ok=True)
    arq, baixado = obter_7z(fonte, tipo, ano, mes, pasta, log)
    tmp = pasta / f"_extraindo_{tipo}{comp_str(ano, mes)}"
    try:
        log(f"[{comp_str(ano, mes)}] Descompactando...")
        txt = extrair_7z(arq, tmp)
        log(f"[{tipo} {comp_str(ano, mes)}] Lendo e filtrando o Rio de Janeiro...")
        rio = ler_rio(txt, encoding)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)          # o .txt (centenas de MB) nunca fica no disco
    rio.to_pickle(cache)                                # poucos MB
    if apagar and baixado:
        arq.unlink(missing_ok=True)
        _PREBAIXADOS.discard(arq)
    return rio


# ------------------------------------------------------------------ modo rápido: baixar em paralelo
def meses_necessarios(ano: int, mes: int, modelo: str, historico: bool) -> list[tuple[str, int, int]]:
    anos = [ano] + (list(range(2020, ano)) if historico and ano > 2020 else [])
    hoje = date.today().year * 12 + date.today().month - 1
    out: list[tuple[str, int, int]] = []
    for a in anos:
        out.append(("CAGEDMOV", a, mes))
        if modelo == "ajustes":
            for k in range(a * 12 + mes - 1, hoje + 1):
                for tipo in ("CAGEDFOR", "CAGEDEXC"):
                    out.append((tipo, k // 12, k % 12 + 1))
    return out


def prebaixar_paralelo(ano: int, mes: int, modelo: str, historico: bool, pasta: Path,
                       usar_cache: bool, log: Log = _nada_log, conexoes: int = 4) -> int:
    """Baixa vários arquivos ao mesmo tempo. Falhas são ignoradas: o fluxo normal baixa o que faltar."""
    pasta.mkdir(parents=True, exist_ok=True)
    pend = []
    for tipo, a, m in dict.fromkeys(meses_necessarios(ano, mes, modelo, historico)):   # sem repetidos
        d7 = pasta / nome_7z(tipo, a, m)
        if (usar_cache and caminho_cache(pasta, tipo, a, m).exists()) or d7.exists():
            continue
        pend.append((tipo, a, m, d7))
    if not pend:
        return 0
    log(f"Modo rápido: baixando {len(pend)} arquivo(s) ao mesmo tempo...")

    def um(x):
        tipo, a, m, d7 = x
        try:
            baixar_ftp(a, m, tipo, d7)
            return d7
        except Exception:  # noqa: BLE001
            return None

    with ThreadPoolExecutor(max_workers=conexoes) as ex:
        ok = [r for r in ex.map(um, pend) if r]
    _PREBAIXADOS.update(ok)
    log(f"Modo rápido: {len(ok)} de {len(pend)} arquivo(s) baixados em paralelo.")
    return len(ok)


# ------------------------------------------------------------------ modelo "com ajustes"
def coletar_mes(fonte: Fonte, ano: int, mes: int, modelo: str, pasta: Path, encoding: str,
                usar_cache: bool, apagar: bool, log: Log = _nada_log, prog: Prog = _nada_prog,
                p_ini: float = 0.0, p_fim: float = 1.0) -> dict:
    """Movimentações do Rio no mês: MOV (+ FOR - EXC no modelo 'ajustes')."""
    alvo = ano * 100 + mes
    prog(p_ini, f"{MES_ABR[mes - 1]}/{ano}: CAGEDMOV")
    mov = rio_do_arquivo(fonte, "CAGEDMOV", ano, mes, pasta, encoding, usar_cache, apagar, log)
    if len(mov) == 0:
        raise ErroCaged(f"Nenhuma linha do Rio de Janeiro (330455) no CAGEDMOV {alvo}")
    mov = mov.assign(peso=1)
    if modelo != "ajustes":
        return {"dados": mov, "corte": None, "faltando": []}

    hoje = date.today().year * 12 + date.today().month - 1
    ini = ano * 12 + mes - 1
    n = max(0, hoje - ini + 1)
    partes = [mov]
    faltando: list[str] = []
    corte = None
    for i in range(1, n + 1):
        k = ini + i - 1
        a, m = k // 12, k % 12 + 1
        mes_ok = True
        for tipo in ("CAGEDFOR", "CAGEDEXC"):
            prog(p_ini + (p_fim - p_ini) * i / n, f"{MES_ABR[mes - 1]}/{ano}: {tipo} {m:02d}/{a}")
            try:
                r = rio_do_arquivo(fonte, tipo, a, m, pasta, encoding, usar_cache, apagar, log)
            except Exception as e:  # noqa: BLE001
                log(f"AVISO: {tipo}{a}{m:02d} indisponível ({str(e).splitlines()[0]})")
                mes_ok = False
                faltando.append(f"{tipo}{a}{m:02d}")
                continue
            r = r[r["competenciamov"] == alvo]
            if len(r):
                partes.append(r.assign(peso=1 if tipo == "CAGEDFOR" else -1))
        if mes_ok:
            corte = a * 100 + m
    # Arquivos depois do corte simplesmente ainda não foram publicados (normal).
    if corte is not None:
        faltando = [f for f in faltando if int(f[8:]) < corte]
    return {"dados": pd.concat(partes, ignore_index=True), "corte": corte, "faltando": faltando}


def gerar_dados(fonte: Fonte, ano: int, mes: int, modelo: str, pasta: str | Path, encoding: str,
                historico: bool, usar_cache: bool, apagar: bool = True, rapido: bool = False,
                log: Log = _nada_log, prog: Prog = _nada_prog) -> dict:
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    if rapido and fonte.tipo == "ftp":
        prog(0.01, "Modo rápido: baixando arquivos em paralelo")
        try:
            prebaixar_paralelo(ano, mes, modelo, historico, pasta, usar_cache, log)
        except Exception as e:  # noqa: BLE001
            log(f"Modo rápido indisponível, seguindo no modo normal: {e}")
    anos = [ano] + (list(range(2020, ano)) if historico and ano > 2020 else [])
    n = len(anos)
    partes = []
    resumo = None
    corte = None
    faltando: list[str] = []
    for k, a in enumerate(anos):
        atual = k == 0
        p_ini = 0.02 + 0.95 * k / n
        p_fim = 0.02 + 0.95 * (k + 1) / n
        try:
            res = coletar_mes(fonte, a, mes, modelo, pasta, encoding, usar_cache, apagar, log, prog, p_ini, p_fim)
        except Exception as e:  # noqa: BLE001
            if atual:
                raise
            log(f"AVISO: {MES_ABR[mes - 1]}/{a} ignorado ({str(e).splitlines()[0]})")
            continue
        if atual:
            log(f"[{MES_ABR[mes - 1]}/{a}] Rio de Janeiro: {fmt_int(len(res['dados']))} linhas consideradas.")
            resumo = calc_resumo(res["dados"])
            corte, faltando = res["corte"], res["faltando"]
            st = resumo["setor"].copy()
        else:
            st = calc_setor(res["dados"])
        partes.append(st.assign(ano=a))
        del res
    prog(1.0, "Concluído")
    return {"ano": ano, "mes": mes, "modelo": modelo, "resumo": resumo,
            "hist": pd.concat(partes, ignore_index=True), "historico": historico,
            "corte": corte, "faltando": faltando}


# ------------------------------------------------------------------ arquivos pesados na pasta
def arquivos_pesados(pasta: str | Path) -> list[Path]:
    import re
    p = Path(pasta)
    if not p.is_dir():
        return []
    rx = re.compile(r"^CAGED(MOV|FOR|EXC)\d{6}(\.7z|\.7z\.part)$", re.I)
    return sorted(f for f in p.iterdir() if f.is_file() and rx.match(f.name))


def tamanho_fmt(b: float) -> str:
    return f"{b / 1e9:.1f} GB" if b >= 1e9 else f"{b / 1e6:.0f} MB"
