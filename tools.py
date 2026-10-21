"""
Atlas - Camada de Ferramentas (grounding)
=========================================
Este modulo da ao Atlas acesso a dados REAIS do sistema em vez de deixar o
modelo inventar. Ele oferece dois caminhos:

1) HEURISTICA (sem custo de LLM extra)
   coletar_por_texto(mensagem) -> {nome: dados_reais}
   Palavras-chave na pergunta ativam a coleta automatica. Ex: "como esta a cpu"
   -> CPU/RAM/disco/temperatura reais.

2) TOOL CALLING (o modelo pede o dado)
   O modelo escreve [[FERRAMENTA: nome | argumento]] e o modulo executa,
   devolvendo o resultado real para o modelo usar na resposta.

Todas as ferramentas aqui sao SOMENTE LEITURA. Acoes que mudam o sistema
(abrir, fechar, criar, apagar) continuam no fluxo existente de comandos.
"""

import re
import socket
from datetime import datetime

# ---------------------------------------------------------------------------
# Implementacoes das ferramentas
# ---------------------------------------------------------------------------


def _t_data_hora(arg=None):
    """Data e hora atuais."""
    agora = datetime.now()
    dias = ["segunda-feira", "terca-feira", "quarta-feira", "quinta-feira",
            "sexta-feira", "sabado", "domingo"]
    meses = ["janeiro", "fevereiro", "marco", "abril", "maio", "junho", "julho",
             "agosto", "setembro", "outubro", "novembro", "dezembro"]
    return (
        f"Data: {agora.day} de {meses[agora.month - 1]} de {agora.year}\n"
        f"Dia da semana: {dias[agora.weekday()]}\n"
        f"Hora: {agora.strftime('%H:%M:%S')}"
    )


def _t_monitorar_pc(arg=None):
    """Uso de CPU, RAM, disco, temperatura e bateria."""
    from system_control import monitor_pc, monitor_pc_fala
    return monitor_pc() + "\n\nResumo: " + monitor_pc_fala()


def _t_programas_abertos(arg=None):
    """Processos em execucao."""
    from system_control import list_running, list_running_fala
    return list_running() + "\n\nResumo: " + list_running_fala()


def _t_espaco_disco(arg=None):
    """Uso de espaco em cada disco."""
    import psutil
    linhas = []
    for part in psutil.disk_partitions(all=False):
        try:
            uso = psutil.disk_usage(part.mountpoint)
            linhas.append(
                f"{part.device} ({part.fstype}): {uso.used // (1024**3)}GB usados "
                f"de {uso.total // (1024**3)}GB ({uso.percent:.0f}% usado)"
            )
        except Exception:
            continue
    return "\n".join(linhas) if linhas else "Nenhum disco legivel encontrado."


def _t_rede(arg=None):
    """Hostname, IPs e interfaces ativas."""
    partes = []
    try:
        partes.append(f"Hostname: {socket.gethostname()}")
    except Exception:
        pass
    try:
        partes.append(f"IP local: {socket.gethostbyname(socket.gethostname())}")
    except Exception:
        pass
    try:
        # IP de saida: o socket UDP nao envia nada, mas revela o endereco
        # que o sistema usaria para sair. Atras de NAT pode ser o IP privado.
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(2)
        try:
            s.connect(("8.8.8.8", 80))
            saida = s.getsockname()[0]
            rotulo = "IP de saida" if saida.startswith("192.168.") or saida.startswith("10.") \
                else "IP publico"
            partes.append(f"{rotulo}: {saida}")
        finally:
            s.close()
    except Exception:
        partes.append("IP de saida: indisponivel (sem conexao ou bloqueado)")
    try:
        import psutil
        ativos = [n for n, st in psutil.net_if_stats().items() if st.isup]
        partes.append(f"Interfaces ativas: {', '.join(ativos) if ativos else 'nenhuma'}")
    except Exception:
        pass
    return "\n".join(partes) if partes else "Nenhuma informacao de rede disponivel."


def _t_listar_arquivos(arg=None):
    """Conteudo de uma pasta."""
    from file_manager import list_dir
    caminho = (arg or "").strip() or "."
    return list_dir(caminho)


def _t_ler_arquivo(arg=None):
    """Conteudo de um arquivo."""
    from file_manager import read_file
    caminho = (arg or "").strip()
    if not caminho:
        return "ERRO: nenhum caminho de arquivo informado."
    return read_file(caminho)


def _t_lembretes(arg=None):
    """Lembretes cadastrados."""
    from reminders import list_reminders
    return list_reminders()


# Codigos WMO de tempo -> descricao em portugues.
_CODIGOS_TEMPO = {
    0: "Ceu limpo", 1: "Quase limpo", 2: "Parcialmente nublado", 3: "Encoberto",
    45: "Nevoeiro", 48: "Nevoeiro com geada",
    51: "Garoa fraca", 53: "Garoa", 55: "Garoa forte",
    56: "Garoa gelada", 57: "Garoa gelada forte",
    61: "Chuva fraca", 63: "Chuva", 65: "Chuva forte",
    66: "Chuva gelada", 67: "Chuva gelada forte",
    71: "Neve fraca", 73: "Neve", 75: "Neve forte", 77: "Graos de neve",
    80: "Pancadas de chuva fracas", 81: "Pancadas de chuva", 82: "Pancadas de chuva fortes",
    85: "Pancadas de neve", 86: "Pancadas de neve fortes",
    95: "Trovoada", 96: "Trovoada com granizo", 99: "Trovoada forte com granizo",
}


def _t_tempo_atual(arg=None):
    """Tempo atual de uma cidade (Open-Meteo, nao exige chave de API)."""
    cidade = (arg or "").strip()
    if not cidade:
        return "ERRO: nenhuma cidade informada para consultar o tempo."

    try:
        import requests
    except ImportError:
        return "ERRO: o modulo 'requests' nao esta instalado."

    # 1) Descobrir as coordenadas da cidade
    try:
        resp = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": cidade, "count": 1, "language": "pt", "format": "json"},
            timeout=8,
        )
        resp.raise_for_status()
        locais = (resp.json() or {}).get("results") or []
        if not locais:
            return f"ERRO: nao encontrei a cidade '{cidade}'."
        local = locais[0]
    except Exception as e:
        return f"ERRO ao localizar a cidade '{cidade}': {e}"

    # 2) Consultar o tempo atual
    try:
        resp = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": local["latitude"],
                "longitude": local["longitude"],
                "current": ("temperature_2m,relative_humidity_2m,apparent_temperature,"
                            "precipitation,weather_code,wind_speed_10m"),
                "timezone": "auto",
            },
            timeout=8,
        )
        resp.raise_for_status()
        atual = (resp.json() or {}).get("current") or {}
    except Exception as e:
        return f"ERRO ao consultar o tempo de '{local.get('name', cidade)}': {e}"

    if not atual:
        return f"ERRO: a API nao devolveu dados de tempo para '{local.get('name', cidade)}'."

    codigo = atual.get("weather_code")
    try:
        condicao = _CODIGOS_TEMPO.get(int(codigo), "Condicao desconhecida")
    except (TypeError, ValueError):
        condicao = "Condicao desconhecida"

    return "\n".join([
        f"Local: {local.get('name', cidade)} - {local.get('admin1', '')} - {local.get('country', '')}",
        f"Temperatura atual: {atual.get('temperature_2m')} graus C",
        f"Sensacao termica: {atual.get('apparent_temperature')} graus C",
        f"Umidade relativa: {atual.get('relative_humidity_2m')}%",
        f"Condicao do tempo: {condicao}",
        f"Precipitacao: {atual.get('precipitation')} mm",
        f"Vento: {atual.get('wind_speed_10m')} km/h",
        f"Observado as: {atual.get('time')}",
        "Fonte: Open-Meteo (dados reais da estacao meteorologica mais proxima)",
    ])


def _t_pesquisar(arg=None):
    """Busca na internet."""
    from web_search import search
    consulta = (arg or "").strip()
    if not consulta:
        return "ERRO: nenhuma consulta informada para a busca."
    return search(consulta)


def _t_ver_tela(arg=None, api_key=None):
    """Descricao da tela atual (usa visao do Gemini)."""
    from brain import ver_tela
    if not api_key:
        return "ERRO: e necessaria uma API key do Gemini para ver a tela."
    return ver_tela(api_key=api_key)


# ---------------------------------------------------------------------------
# Extracao de argumento (usada pelo caminho heuristico)
# ---------------------------------------------------------------------------

_ALIAS_PASTAS = (
    "area de trabalho", "desktop", "downloads", "documentos", "imagens",
    "videos", "musicas", "pasta inicial", "appdata local", "appdata roaming", "appdata",
)

_EXTENSOES = r"txt|py|md|json|log|csv|ini|cfg|conf|bat|ps1|xml|html|htm|css|js|java|c|cpp|h|jpg|jpeg|png|gif|pdf|zip|rar|exe|docx|xlsx|pptx|mp3|mp4"


def _arg_pesquisar(mensagem: str) -> str:
    """Extrai a consulta de busca da frase."""
    t = mensagem.strip()
    # Cada remocao e separada para nao haber retrocesso do regex.
    t = re.sub(r"^\s*por\s+favor\s*[,:]?\s*", "", t, flags=re.IGNORECASE)
    t = re.sub(r"^\s*(?:(?:me\s+)?(?:d[áa]|de|da|do|fa[çc]a|faz|fazer|quero|preciso|gostaria|poss[ií]vel|pode|vc|voce|qual|quais|quanto|quanta|quem|onde|quando|me\s+diga|me\s+fale)\s+)+", "", t, flags=re.IGNORECASE)
    t = re.sub(r"^\s*(?:pesquis\w*|busc\w*|procur\w*|olh\w*)\s*", "", t, flags=re.IGNORECASE)
    t = re.sub(r"^\s*(?:na\s+internet|online|na\s+web|no\s+google|no\s+site)\s*", "", t, flags=re.IGNORECASE)
    # Preposicao uma vez, artigos repetidamente (para nao comer "da AMD").
    t = re.sub(r"^\s*(?:por|sobre|para|do|da|na|em|no)\s+", "", t, flags=re.IGNORECASE)
    t = re.sub(r"^\s*(?:(?:a|o|as|os|um|uma)\s+)+", "", t, flags=re.IGNORECASE)
    t = t.strip(" ?!.,:")
    return t or mensagem.strip()


def _arg_listar_arquivos(mensagem: str) -> str:
    """Extrai a pasta a ser listada."""
    m = re.search(r"([A-Za-z]:\\[^\s\"']+|\\\\[^\s\"']+)", mensagem)
    if m:
        return m.group(1)

    t = mensagem.lower()
    for alias in _ALIAS_PASTAS:
        if alias in t:
            return alias
    return ""


def _arg_ler_arquivo(mensagem: str) -> str:
    """Extrai o caminho do arquivo a ser lido."""
    m = re.search(r"([A-Za-z]:\\[^\s\"']+|\\\\[^\s\"']+)", mensagem)
    if m:
        return m.group(1)

    t = mensagem.strip()
    # Remove o comando e as palavras de preenchimento antes do nome do arquivo.
    t = re.sub(r"^\s*por\s+favor\s*[,:]?\s*", "", t, flags=re.IGNORECASE)
    t = re.sub(r"^\s*(?:(?:me\s+)?(?:leia|ler|mostra|mostram|mostre|mostrar|ver|abrir|exiba|exibir)\s+)+", "", t, flags=re.IGNORECASE)
    t = re.sub(r"^\s*(?:(?:o|a|os|as|do|da|de|em|no|na|para|pra|conteudo|conteúdo|arquivo|file)\s+)+", "", t, flags=re.IGNORECASE)
    # Nome do arquivo sem palavras junto (o comando ja foi removido acima).
    m = re.search(r"([\w\-]+\.(?:" + _EXTENSOES + r"))\b", t, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return ""


# Palavras que indicam hardware, clima ou tempo: nunca sao lugares.
_NAO_LUGAR = re.compile(
    r"^(?:cpu|processador|pc|computador|sistema|grafica|placa|notebook|"
    r"memoria|ram|disco|bateria|celular|tela|monitor|"
    r"programa|aplicativo|arquivo|site|pagina|download|video|jogo|codigo|"
    r"tempo|clima|chuva|chova|previs[ãa]o|horas|hora|dia|"
    r"hoje|agora|amanha|amanh[ãa]|de|do|da|em|para|no|na)\b", re.IGNORECASE)

# "Tempo" no sentido de duracao ("quanto tempo gasta") nao e clima.
_RE_TEMPO_CONSUMO = re.compile(
    r"\b(?:quanto|o\s+quanto|todo\s+o)\s+tempo\b"
    r"|\btempo\s+(?:gasta|leva|demora|resta|sobra|total|real|livre|"
    r"de\s+espera|para\s+esperar|que\s+leva)\b",
    re.IGNORECASE,
)

# Ancora na palavra do clima para nao capturar "previsao DO TEMPO para hoje".
_ANCORA_TEMPO = re.compile(
    r"\b(?:tempo|clima|temperatura|chuva|chover|chovendo|previs[ãa]o)\b"
    r"[^.?!]{0,30}?\b(?:em|para|no|na|de|do)\s+"
    r"([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ]*(?:\s+[A-Za-zÀ-ÿ]+){0,3})",
    re.IGNORECASE,
)


def _arg_cidade(mensagem: str) -> str:
    """Extrai o nome de uma cidade da frase."""
    # "Quanto tempo gasta" e duracao, nao e clima.
    if _RE_TEMPO_CONSUMO.search(mensagem):
        return ""

    m = _ANCORA_TEMPO.search(mensagem)
    if not m:
        return ""

    cidade = m.group(1).strip()
    # Tira palavras de tempo que podem ter vindo junto ("Lisboa agora").
    cidade = re.sub(
        r"\s+(?:hoje|agora|amanh[ãa]?|atual|atualmente|desta|deste|nesta|neste|"
        r"para|prevista|previsto|tarde|manha|noite)\b.*$", "", cidade, flags=re.IGNORECASE)
    cidade = cidade.strip(" ?!.,")

    if not cidade or _NAO_LUGAR.match(cidade):
        return ""
    return cidade


# ---------------------------------------------------------------------------
# Registro das ferramentas
# ---------------------------------------------------------------------------
# "gatilhos": padroes regex. Se algum casar com a mensagem, a ferramenta e
# executada automaticamente (caminho heuristico, sem custo de LLM extra).

FERRAMENTAS = {
    "data_hora": {
        "descricao": "Data, dia da semana e hora atuais",
        "executar": _t_data_hora,
        "gatilhos": [
            r"\bque horas\b", r"\bque dia\b", r"\bdata de hoje\b", r"\bhorario\b",
            r"\bhora atual\b", r"\bque dia da semana\b", r"\bdata atual\b",
        ],
    },
    "monitorar_pc": {
        "descricao": "Uso de CPU, RAM, disco, temperatura e bateria do computador",
        "executar": _t_monitorar_pc,
        "gatilhos": [
            r"\bcpu\b", r"\bprocessador\b", r"\bram\b", r"\bmemoria\b",
            r"\bbateria\b", r"\buptime\b",
            # "temperatura" so vale para o computador quando perto de um termo
            # de hardware. Sem isso, "temperatura em Lisboa" cairia aqui.
            r"\btemperatura\b.{0,30}\b(?:cpu|processador|pc|computador|sistema|grafica|placa|notebook)\b",
            r"\b(?:cpu|processador|pc|computador|sistema|grafica|placa)\b.{0,30}\btemperatura\b",
            r"\b(?:monitorar|monitora|status|desempenho|situacao|estado)\b.{0,20}\b(?:pc|computador|machine|maquina|sistema)\b",
            r"\bcomo (?:esta|estao|vao)\b.{0,20}\b(?:pc|computador|sistema)\b",
        ],
    },
    "programas_abertos": {
        "descricao": "Lista de programas e processos em execucao",
        "executar": _t_programas_abertos,
        "gatilhos": [
            r"\bprocessos?\b",
            r"\bprogramas?\b.{0,20}\b(?:abertos?|aberta|rodando|executando|em\s+(?:execu|uso)cao)\b",
            r"\b(?:abertos?|rodando|executando)\b.{0,25}\bprogramas?\b",
            r"\b(?:o que|quais|quais programas?)\b.{0,30}\b(?:abertos?|aberta|rodando|executando)\b",
            r"\btask ?manager\b", r"\bgerenciador de tarefas\b",
        ],
    },
    "espaco_disco": {
        "descricao": "Espaco usado e total em cada disco",
        "executar": _t_espaco_disco,
        "gatilhos": [
            r"\bespa[çc]o em disco\b", r"\barmazenamento\b", r"\bquanto (?:tem|sobra|ha) de espaco\b",
            r"\bdisco (?:cheio|cheio|livre)\b", r"\bcapacidade do disco\b",
        ],
    },
    "rede": {
        "descricao": "Endereco IP, hostname e interfaces de rede ativas",
        "executar": _t_rede,
        "gatilhos": [
            r"\bmeu ip\b", r"\bqual (?:e )?o ip\b", r"\bendere[çc]o ip\b",
            r"\bendere[çc]o\s+(?:de\s+|do\s+)?ip\b",
            r"\bip\s+(?:local|publico|p[úu]blico|privado|externo)\b",
            r"\bqual\s+(?:e\s+)?o\s+(?:meu\s+)?(?:endere[çc]o\s+(?:de\s+)?)?ip\b",
            r"\bwi-?fi\b", r"\bconex[ãa]o\b", r"\binterface[s]? de rede\b",
        ],
    },
    "listar_arquivos": {
        "descricao": "Lista o conteudo de uma pasta",
        "executar": _t_listar_arquivos,
        "extrair": _arg_listar_arquivos,
        "gatilhos": [
            r"\b(?:arquivos|pastas|conteudo)\b.{0,25}\b(?:em|na|no|da|do)\b",
            r"\b(?:liste|listar|mostre|mostrar|ver|o que tem)\b.{0,20}\b(?:os |as )?(?:arquivos|pastas)\b",
            r"\bconteudo da pasta\b", r"\bquais arquivos\b",
        ],
    },
    "ler_arquivo": {
        "descricao": "Le o conteudo de um arquivo",
        "executar": _t_ler_arquivo,
        "extrair": _arg_ler_arquivo,
        "gatilhos": [
            r"\b(?:leia|ler|mostrar|ver)\b.{0,15}\b(?:o |a )?arquivo\b",
            r"\bconte[úu]do do arquivo\b",
        ],
    },
    "lembretes": {
        "descricao": "Lista os lembretes e avisos cadastrados",
        "executar": _t_lembretes,
        "gatilhos": [
            r"\blembretes?\b", r"\bavisos?\b", r"\bcompromissos?\b",
            r"\b(?:o que|quais)\b.{0,20}\b(?:tenho|devo|preciso) (?:lembrar|fazer)\b",
        ],
    },
    "tempo_atual": {
        "descricao": "Tempo atual de uma cidade (temperatura, chuva, umidade)",
        "executar": _t_tempo_atual,
        "extrair": _arg_cidade,
        "exige_arg": True,
        "gatilhos": [
            r"\btempo\s+(?:em|para|no|na)\s+[A-Za-zÀ-ÿ]",
            # "que tempo faz em Paris", "como esta o tempo em Lisboa"
            r"\btempo\s+\w{1,15}\s+(?:em|para|no|na)\s+[A-Za-zÀ-ÿ]",
            r"\bclima\s+(?:em|para|de|no|na)\s+[A-Za-zÀ-ÿ]",
            r"\btemperatura\s+(?:em|na|no)\s+(?!(?:cpu|processador|pc|computador|sistema|grafica|placa|notebook)\b)[A-Za-zÀ-ÿ]",
            r"\bchover\b.{0,25}\bem\s+[A-Za-zÀ-ÿ]",
            r"\bchuva\b.{0,25}\bem\s+[A-Za-zÀ-ÿ]",
            r"\bchovendo\b.{0,25}\bem\s+[A-Za-zÀ-ÿ]",
            r"\bprevis[ãa]o\s+(?:do\s+)?tempo\b",
            r"\bcomo est[áa] o tempo\b",
        ],
    },
    "pesquisar": {
        "descricao": "Busca informacao na internet (DuckDuckGo)",
        "executar": _t_pesquisar,
        "extrair": _arg_pesquisar,
        "exige_arg": True,
        "gatilhos": [
            r"\bpesquis\w*\b", r"\bbusc\w*\b", r"\bprocur\w*\b",
            r"\bna internet\b", r"\bonline\b", r"\bnot[íi]cias\b",
            r"\bclima\b", r"\btempo (?:em|hoje|agora|para)\b", r"\bpre[çc]o (?:d[oa]|atual)\b",
            r"\bvers[ãa]o atual\b", r"\bnota[s]? do dia\b",
            # Clima de uma cidade. O lookahead evita conflitar com
            # "temperatura no processador" (que e do computador).
            r"\btemperatura\s+(?:em|na|no)\s+(?!(?:cpu|processador|pc|computador|sistema|grafica|placa|notebook)\b)",
            r"\bprevis[ãa]o\s+(?:do\s+)?(?:tempo|chuva)\b",
            r"\bchuva\b", r"\bchover\b", r"\bchovendo\b", r"\bchove\b",
            r"\bcomo est[áa] o tempo\b",
            r"\bclima\s+(?:de|em|hoje)\b",
        ],
    },
    "ver_tela": {
        "descricao": "Descreve o que esta na tela do computador (visao)",
        "executar": _t_ver_tela,
        "gatilhos": [
            r"\b(?:veja|ver|olhe|olha|mostra|mostrar)\b.{0,15}\b(?:a\s+)?(?:tela|monitor|display|screen)\b",
        ],
    },
}


# Ferramentas que o modelo pode solicitar sozinho via [[FERRAMENTA: ...]].
# "ver_tela" exige API key, entao fica de fora do catalogo automatico.
FERRAMENTAS_PARA_LLM = [
    "data_hora", "monitorar_pc", "programas_abertos", "espaco_disco",
    "rede", "listar_arquivos", "ler_arquivo", "lembretes", "tempo_atual",
    "pesquisar",
]


def catalogo_texto() -> str:
    """Descricao das ferramentas para o prompt do modelo."""
    linhas = []
    for nome in FERRAMENTAS_PARA_LLM:
        spec = FERRAMENTAS[nome]
        if spec.get("exige_arg"):
            linhas.append(f"- {nome}: {spec['descricao']} -- precisa de argumento (caminho ou cidade)")
        else:
            linhas.append(f"- {nome}: {spec['descricao']} -- nao precisa de argumento")
    return "\n".join(linhas)


INSTRUCAO_FERRAMENTAS = """=== FERRAMENTAS (dados reais do sistema) ===
Se a pergunta do Senhor exigir um dado real que NAO esteja no CONTEXTO VERIFICADO,
voce pode pedir uma ferramenta. Escreva o pedido na sua resposta, neste formato exato:

[[FERRAMENTA: nome_da_ferramenta]]
[[FERRAMENTA: nome_da_ferramenta | argumento]]

Uma ferramenta por linha. Ferramentas disponiveis:
{catalogo}

Regras:
- Peca APENAS ferramentas que existam na lista acima.
- Se a ferramenta estiver marcada como "nao precisa de argumento", escreva so o nome.
  Exemplo correto para descobrir o IP: [[FERRAMENTA: rede]]
  Nao invente argumentos para ferramentas que nao pedem nenhum.
- Se estiver marcada como "precisa de argumento", o argumento e obrigatorio.
  Exemplo para o tempo de Lisboa: [[FERRAMENTA: tempo_atual | Lisboa]]
- Escreva o marcador sozinho na resposta, sem frase em volta.
- Apos receber os resultados, responda ao Senhor usando AQUELES dados reais.
- NUNCA invente o resultado de uma ferramenta. Se a ferramenta falhar, diga que falhou.
- Se a resposta estiver no CONTEXTO VERIFICADO, nao peca ferramenta: responda direto."""


# Codigos de cor ANSI (o monitor_pc usa para colorir o relatorio).
# Sem remover, o modelo recebe lixo invisivel no contexto.
_RE_ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


def _sem_ansi(texto: str) -> str:
    """Remove sequencias de escape ANSI de uma string."""
    if not texto:
        return texto
    return _RE_ANSI.sub("", texto)


def executar(nome: str, arg: str = None, api_key: str = None) -> str:
    """Executa uma ferramenta pelo nome e devolve o dado real (ou o erro)."""
    nome = (nome or "").strip().lower().replace(" ", "_").replace("-", "_")
    if nome not in FERRAMENTAS:
        disponiveis = ", ".join(FERRAMENTAS.keys())
        return f"ERRO: ferramenta '{nome}' nao existe. Ferramentas disponiveis: {disponiveis}"

    if nome == "ver_tela":
        return _sem_ansi(FERRAMENTAS[nome]["executar"](arg, api_key=api_key))
    return _sem_ansi(FERRAMENTAS[nome]["executar"](arg))


def coletar_por_texto(mensagem: str, api_key: str = None) -> dict:
    """Executa as ferramentas que casam com a mensagem. Retorna {nome: dados}."""
    if not mensagem:
        return {}

    texto = mensagem.lower()
    coletados = {}
    for nome, spec in FERRAMENTAS.items():
        if nome == "ver_tela" and not api_key:
            continue
        for padrao in spec["gatilhos"]:
            try:
                casou = re.search(padrao, texto, re.IGNORECASE)
            except re.error:
                casou = False
            if casou:
                # Extrai o argumento (caminho/consulta) da propria frase.
                arg = None
                extrator = spec.get("extrair")
                if extrator:
                    try:
                        arg = extrator(mensagem)
                    except Exception:
                        arg = None

                # Ferramenta que depende de argumento nao serve para nada
                # sem ele; melhor deixar a outra ferramenta cuidar do caso.
                if spec.get("exige_arg") and not (arg or "").strip():
                    break

                try:
                    saida = executar(nome, arg, api_key=api_key)
                except Exception as e:
                    saida = f"ERRO ao coletar '{nome}': {e}"
                coletados[nome] = saida
                break
    return coletados


def contexto_inicial(mensagem: str, api_key: str = None) -> str:
    """Monta o bloco de dados reais coletados por heuristica (vazio se nada casar)."""
    dados = coletar_por_texto(mensagem, api_key=api_key)
    if not dados:
        return ""
    partes = [f"[{nome}]\n{saida}" for nome, saida in dados.items()]
    return ("DADOS REAIS COLETADOS DO SISTEMA:\n" + "\n\n".join(partes))
