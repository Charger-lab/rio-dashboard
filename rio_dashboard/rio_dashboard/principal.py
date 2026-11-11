"""Ponto de entrada: sobe o servidor local e abre o navegador."""
from __future__ import annotations

import socket
import threading
import webbrowser


def porta_livre(inicio: int = 8050) -> int:
    for p in range(inicio, inicio + 50):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", p)) != 0:
                return p
    return inicio


def autoteste() -> int:
    """Verifica se todas as bibliotecas empacotadas funcionam (usado na construção do instalador)."""
    import numpy as np
    import pandas as pd
    import py7zr  # noqa: F401
    from .app import criar_app
    from .calculos import calc_resumo, calc_setor
    from .pdf import gerar_pdf
    rng = np.random.default_rng(1)
    n = 500
    rio = pd.DataFrame({
        "competenciamov": 202609, "municipio": 330455, "secao": rng.choice(list("ACFGIJQZ"), n),
        "saldomovimentacao": rng.choice([1, -1], n), "graudeinstrucao": rng.choice([1, 5, 7, 9, 80], n),
        "idade": rng.integers(15, 70, n), "racacor": rng.choice([1, 2, 3, 9], n),
        "sexo": rng.choice([1, 3], n), "tipodedeficiencia": rng.choice([0, 0, 0, 1], n),
        "salario": rng.normal(2500, 600, n).round(2), "peso": 1})
    resumo = calc_resumo(rio)
    hist = pd.concat([calc_setor(rio).assign(ano=a) for a in (2025, 2026)], ignore_index=True)
    d = {"ano": 2026, "mes": 9, "modelo": "ajustes", "resumo": resumo, "hist": hist, "historico": True,
         "corte": 202610, "faltando": []}
    pdf = gerar_pdf(d)
    criar_app()
    # leitura de um .7z de verdade (py7zr) + filtro do Rio, como no uso real
    import tempfile
    from pathlib import Path
    from .dados import extrair_7z, ler_rio
    with tempfile.TemporaryDirectory() as t:
        t = Path(t)
        bruto = rio.drop(columns="peso").rename(columns={"competenciamov": "competênciamov", "secao": "seção"})
        outros = bruto.copy(); outros["municipio"] = 355030
        (t / "CAGEDMOV202609.txt").write_text(pd.concat([bruto, outros]).to_csv(sep=";", decimal=",", index=False),
                                              encoding="utf-8")
        with py7zr.SevenZipFile(t / "CAGEDMOV202609.7z", "w") as z:
            z.write(t / "CAGEDMOV202609.txt", "CAGEDMOV202609.txt")
        txt = extrair_7z(t / "CAGEDMOV202609.7z", t / "saida")
        lido = ler_rio(txt)
        assert len(lido) == n, f"leitura do 7z devolveu {len(lido)} linhas (esperado {n})"
        from .dados import ler_rio_7z
        lido2 = ler_rio_7z(t / "CAGEDMOV202609.7z")          # leitura em fluxo, como no uso real
        assert len(lido2) == n, f"leitura em fluxo devolveu {len(lido2)} linhas (esperado {n})"
    assert pdf[:4] == b"%PDF", "PDF inválido"
    print(f"AUTOTESTE OK (pdf {len(pdf)} bytes)")
    return 0


def main(argv: list[str] | None = None) -> None:
    import logging
    import sys
    if argv and "--autoteste" in argv:
        sys.exit(autoteste())
    from .app import criar_app
    app = criar_app()
    porta = porta_livre()
    url = f"http://127.0.0.1:{porta}"
    print("=" * 60)
    print(" Rio Dashboard")
    print(f" Aberto em {url}")
    print(" Para encerrar, feche esta janela ou use o botão 'Fechar' no app.")
    print("=" * 60, flush=True)
    logging.getLogger("werkzeug").setLevel(logging.ERROR)
    threading.Timer(1.5, lambda: webbrowser.open(url)).start()
    app.run(host="127.0.0.1", port=porta, debug=False)


if __name__ == "__main__":
    main()
