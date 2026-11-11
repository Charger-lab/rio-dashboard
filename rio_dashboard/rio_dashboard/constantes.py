"""Constantes, dicionários e formatação (espelha o dashboard em R)."""
COD_MUN_RIO = 330455
ELABORACAO = "Observatório do Trabalho Carioca"
VERSAO_CACHE = "v2"

MES_NOME = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho",
            "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
MES_ABR = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]

COR = {"adm": "#00C26A", "des": "#FF5A5F", "saldo": "#0B4A7A", "navy": "#14365D", "cyan": "#00B5F0"}

SETORES = ["Agropecuária", "Indústria", "Construção", "Comércio", "Serviços"]
ESC_ORDEM = ["Analfabeto", "Fundamental Incompleto", "Fundamental Completo", "Médio Incompleto",
             "Médio Completo", "Superior Incompleto", "Superior Completo"]
FAIXAS_IDADE = ["Até 17 anos", "18 a 24 anos", "25 a 29 anos", "30 a 39 anos", "40 a 49 anos",
                "50 a 64 anos", "65 anos ou mais"]
DEF_ORDEM = ["Não deficiente", "Física", "Auditiva", "Visual", "Intelectual", "Múltipla", "Reabilitado"]

DIC_SEXO = {1: "Masculino", 3: "Feminino"}
DIC_RACA = {1: "Branco", 2: "Preto", 3: "Pardo", 4: "Amarela", 5: "Indígena", 6: "Não informada"}
DIC_DEF = {0: "Não deficiente", 1: "Física", 2: "Auditiva", 3: "Visual", 4: "Intelectual",
           5: "Múltipla", 6: "Reabilitado"}

COLS_NECESSARIAS = ["competenciamov", "municipio", "secao", "saldomovimentacao", "graudeinstrucao",
                    "idade", "racacor", "sexo", "tipodedeficiencia", "salario"]

TIPOS = ("CAGEDMOV", "CAGEDFOR", "CAGEDEXC")

TABELA_CATEGORIAS = [
    ("Agropecuária", "A", "São fazendas responsáveis por plantações e criação de animais ou rebanhos.",
     "Plantações de soja, arroz e milho ou criação de animais como galinha, porco, vaca e ovelhas."),
    ("Indústria", "B, C, D, E", "São fábricas responsáveis pela transformação de matéria-prima em produtos comercializáveis.",
     "A madeira da árvore para mobília, o metal das minas para ferramentas, a lã da ovelha para as roupas."),
    ("Construção", "F", "Responsável por construção de imóveis através dos recursos produzidos pela indústria, extraídos pelo extrativismo mineral ou plantação de árvores.",
     "Os imóveis podem ser casas, prédios, hospitais, escolas e etc."),
    ("Comércio", "G", "Responsável pela compra ou venda de produzidos por fábricas ou produtos vindo de terceiro.",
     "Pode ser tanto uma matéria vinda de uma fábrica ou um produto produzido por um trabalhador autônomo."),
    ("Serviços", "H a U", "É qualquer tipo de prática que gere uma renda baseada em atividades sociais que não se limita a troca ou posse de bens físicos.",
     "Ensinar, Atender, Cuidar, Explicar, Cozinhar, Arrumar, Limpar, etc."),
]


def fmt_int(x) -> str:
    """Inteiro com separador de milhar em ponto (padrão brasileiro)."""
    return f"{int(round(float(x))):,}".replace(",", ".")


def fmt_rs(x) -> str:
    import math
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "-"
    return "R$ " + f"{float(x):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
