import requests
import json
import base64
import re

HOST = "http://localhost:11434"
MODEL = "llama3.2"

_session = requests.Session()

SYSTEM_PROMPT = """Voce e o Atlas, um mordomo virtual pessoal educado, formal e prestativo. Fale como um mordomo britanico refinado, em portugues do Brasil.

=== REGRA SUPREMA: VERACIDADE (prioridade maxima) ===
Voce NAO tem acesso a internet, a arquivos, a programas, a tela do computador nem a sensores, a menos que esses dados aparecam EXPLICITAMENTE no bloco "CONTEXTO VERIFICADO" desta conversa.

Regras inegociaveis:
1. NUNCA invente fatos, numeros, datas, horarios, precos, nomes, caminhos de arquivo, URLs, versoes, programas instalados ou resultados de acoes.
2. NUNCA afirme que executou uma acao (abrir, fechar, criar, apagar, instalar, pesquisar, ver a tela, rodar codigo) a menos que o RESULTADO REAL dessa acao esteja no CONTEXTO VERIFICADO. Se nao estiver, diga que ainda nao executou ou que nao tem confirmacao de sucesso.
3. NUNCA preencha lacunas com o que "deveria ser" ou com o que "normalmente e". Exemplos proibidos: inventar um caminho de instalacao, inventar um link, inventar o resultado de um comando, inventar o que a tela mostra.
4. Se a resposta nao estiver no CONTEXTO VERIFICADO e voce nao tiver certeza: responda honestamente. Exemplo: "Nao tenho essa informacao confirmada, Senhor. Posso pesquisa-la se o Senhor quiser." NUNCA invente para parecer prestativo.
5. Se houver um CONTEXTO VERIFICADO, use-o como fonte da verdade. Se ele contradizer o que voce "sabia", o CONTEXTO VENCE.
6. Se um resultado de busca nao contiver a resposta, diga que nao encontrou informacao confiavel. Nao complete com conhecimento proprio.
7. Distinga fato de estimativa. Se for estimativa, diga "estimativa". Nao apresente palpite como certeza.
8. Mensagens anteriores do assistente neste historico PODEM conter erros. Nao as trate como fatos verificados; baseie-se no CONTEXTO VERIFICADO.
9. Prefira "nao tenho certeza" a uma resposta errada. Mentir educadamente ainda e mentir.

=== ESTILO ===
- Trate o usuario por "Senhor" ou "Minha Senhoria" (se usuario feminino).
- Formal e cordial, mas nunca roboitico. Varie as respostas.
- 2 a 4 frases. NUNCA use emojis. NUNCA use markdown, asteriscos ou hashtags.
- Expressoes usuais (use com parcimonia): "Certamente", "Muito bem", "Como o Senhor desejar", "Com prazer", "Entendido", "Aos seus servicos", "Fico a disposicao", "Peço desculpas".

=== RESPOSTAS POR TIPO DE PEDIDO ===
- Factual ("que horas sao", "qual a temperatura", "qual a versao"): responda apenas com o que consta no CONTEXTO VERIFICADO. Se nao constar, diga que nao tem essa informacao confirmada.
- Acao (abrir/fechar/criar): mencione somente o que o sistema confirmou ter feito. Se o sistema nao trouxe resultado, diga que a acao nao foi confirmada.
- Pesquisa: resuma usando apenas os resultados fornecidos e cite a origem.
- Codigo: entregue o codigo pedido. NUNCA afirme que rodou ou que funcionou sem o resultado real da execucao.
- Nao entendeu: "Peço desculpas, Senhor, mas nao captei bem. Poderia repetir?"

NUNCA diga "Eu sou uma IA" ou "Sou um assistente". Voce e o ATLAS, mordomo pessoal do Senhor."""

PERFIL_TECNICO = """Voce e o Atlas em MODO TECNICO. Voce e um assistente de programacao preciso e direto.

REGRAS DE VERACIDADE (prioridade maxima):
1. NUNCA invente APIs, funcoes, classes, bibliotecas, argumentos, versoes, nomes de arquivo ou trechos de codigo que nao estejam no material fornecido.
2. Use SOMENTE o codigo e as informacoes presentes no CONTEXTO VERIFICADO.
3. Se a tarefa exigir algo que nao foi fornecido, NAO invente: entregue o que da para fazer com o material recebido.
4. NUNCA afirme que o codigo foi executado, testado ou que funciona. Voce nao tem acesso a um ambiente de execucao a menos que o resultado real esteja no CONTEXTO VERIFICADO.
5. Entregue o codigo COMPLETO, exatamente no formato solicitado pelo usuario, sem comentarios extras, sem markdown desnecessario e sem resumir partes com "...".

Tom: direto e tecnico. Sem persona de mordomo, sem emojis, sem cortesias."""

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models"
GEMINI_MODELS = [
    "gemini-3.5-flash-lite",
    "gemini-3.6-flash",
    "gemini-3.5-flash",
]


def contexto_sistema() -> str:
    """Monta o bloco CONTEXTO VERIFICADO com dados REAIS do momento.

    Isso impede o modelo de inventar data, hora, sistema e caminho de instalacao,
    que sao as alucinacoes mais comuns em um assistente de desktop.
    """
    import os
    import platform
    from datetime import datetime

    agora = datetime.now()
    dias = ["segunda-feira", "terca-feira", "quarta-feira", "quinta-feira",
            "sexta-feira", "sabado", "domingo"]
    meses = ["janeiro", "fevereiro", "marco", "abril", "maio", "junho", "julho",
             "agosto", "setembro", "outubro", "novembro", "dezembro"]

    linhas = [
        f"Data atual: {agora.day} de {meses[agora.month - 1]} de {agora.year} ({dias[agora.weekday()]})",
        f"Hora atual: {agora.strftime('%H:%M')}",
        f"Sistema operacional: {platform.system()} {platform.release()}",
        f"Usuario logado: {os.environ.get('USERNAME', 'desconhecido')}",
    ]
    try:
        pasta_atlas = os.path.dirname(os.path.abspath(__file__))
        linhas.append(f"Pasta do Atlas: {pasta_atlas}")
    except Exception:
        pass

    return "\n".join(linhas)


def _montar_system_prompt(contexto_extra: str = None, perfil: str = "mordomo",
                          sistema_extra: str = None) -> str:
    """Junta o prompt base com o CONTEXTO VERIFICADO.

    `contexto_extra` sao os dados reais coletados (ferramentas, busca).
    `sistema_extra` sao instrucoes adicionais (ex: catalogo de ferramentas).
    """
    base = PERFIL_TECNICO if perfil == "tecnico" else SYSTEM_PROMPT
    blocos = [base]

    # O contexto do sistema (data/hora) e SEMPRE incluido, mesmo quando ha
    # contexto extra. Sem isso, o Atlas perdia a hora ao usar ferramentas.
    try:
        contexto_base = contexto_sistema()
    except Exception:
        contexto_base = ""

    contexto_extra = (contexto_extra or "").strip()
    contexto_real = "\n\n".join(p for p in (contexto_base, contexto_extra) if p)

    if contexto_real:
        blocos.append(
            "=== CONTEXTO VERIFICADO (dados reais confirmados pelo sistema) ===\n"
            "Use EXCLUSIVAMENTE estes dados para fatos. Se o que foi perguntado nao estiver aqui, "
            "diga honestamente que nao tem a informacao confirmada.\n\n"
            f"{contexto_real}"
        )

    if sistema_extra:
        blocos.append(sistema_extra)

    return "\n\n".join(blocos)


def _post_com_retry(url, headers, json, timeout, tentativas=3, espera_base=2.0):
    """Faz um POST re-testando em caso de erro de quota/taxa (429) ou servico (5xx).

    Usa espera progressiva (backoff) para nao estourar a cota de novo.
    Se a resposta indicar cota FREE bloqueada (limit: 0), abandona na hora.
    """
    import time as _time
    ultimo = None
    for i in range(tentativas):
        try:
            r = _session.post(url, headers=headers, json=json, timeout=timeout)
            if r.status_code == 429 or (500 <= r.status_code < 600):
                # Cota free-tier bloqueada (limit: 0) => retry nao adianta, falha logo
                try:
                    corpo = r.text.lower()
                except Exception:
                    corpo = ""
                if "free_tier" in corpo and "limit: 0" in corpo:
                    r.raise_for_status()
                espera = espera_base * (i + 1)
                late = r.headers.get("Retry-After")
                try:
                    if late:
                        espera = max(espera, float(late))
                except ValueError:
                    pass
                ultimo = r
                if i < tentativas - 1:
                    _time.sleep(espera)
                    continue
            r.raise_for_status()
            return r
        except requests.exceptions.RequestException as e:
            ultimo = e
            if i < tentativas - 1:
                _time.sleep(espera_base * (i + 1))
                continue
            raise
    if isinstance(ultimo, requests.exceptions.RequestException):
        raise ultimo
    if ultimo is not None:
        ultimo.raise_for_status()
    raise RuntimeError("Falha no POST apos retries")


def _chat_ollama(mensagem, historico, modelo, contexto=None, temperature=0.2, perfil="mordomo",
                 sistema_extra=None):
    messages = [{"role": "system", "content": _montar_system_prompt(contexto, perfil, sistema_extra)}]
    if historico:
        messages.extend(historico[-8:])
    if mensagem:
        messages.append({"role": "user", "content": mensagem})

    resp = _session.post(
        f"{HOST}/api/chat",
        json={
            "model": modelo or MODEL,
            "messages": messages,
            "stream": False,
            "keep_alive": "30m",
            # Temperatura baixa: o Atlas responde como mordomo, nao como gerador criativo.
            # Valores altos (0.7+) aumentam a taxa de invencao de fatos.
            "options": {"temperature": temperature, "top_p": 0.9},
        },
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json().get("message", {}).get("content", "Sem resposta.")


def _chat_gemini(mensagem, historico, modelo, api_key, contexto=None, temperature=0.2, perfil="mordomo",
                 sistema_extra=None):
    url = f"{GEMINI_API_URL}/{modelo or GEMINI_MODELS[0]}:generateContent"

    contents = []
    if historico:
        for msg in historico[-8:]:
            role = "user" if msg["role"] == "user" else "model"
            contents.append({"role": role, "parts": [{"text": msg["content"]}]})
    if mensagem:
        contents.append({"role": "user", "parts": [{"text": mensagem}]})

    resp = _session.post(
        url,
        headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
        json={
            # systemInstruction real: o Gemini aplica as regras com muito mais peso
            # do que quando o prompt de sistema vira um turno de usuario.
            "systemInstruction": {"parts": [{"text": _montar_system_prompt(contexto, perfil, sistema_extra)}]},
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "topP": 0.9,
                "maxOutputTokens": 2048,
            },
        },
        timeout=120,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["candidates"][0]["content"]["parts"][0]["text"]


def chat(mensagem: str, historico: list = None, modelo: str = None,
         provider: str = "ollama", api_key: str = None,
         contexto: str = None, temperature: float = 0.2,
         perfil: str = "mordomo") -> str:
    """Envia mensagem e retorna a resposta. Provider: ollama, gemini.

    `contexto` opcional: dados REAIS (ex: resultados de busca) que o modelo deve
    usar como unica fonte para os fatos. Sem ele, o modelo usa apenas o
    CONTEXTO VERIFICADO com data/hora/sistema, e diz que nao sabe caso falte algo.

    `perfil`: "mordomo" (conversa normal) ou "tecnico" (codigo, sem persona).
    """
    try:
        if provider == "gemini" and api_key:
            return _chat_gemini(mensagem, historico, modelo, api_key,
                                contexto=contexto, temperature=temperature, perfil=perfil)
        else:
            return _chat_ollama(mensagem, historico, modelo,
                                 contexto=contexto, temperature=temperature, perfil=perfil)
    except requests.ConnectionError:
        return "Erro: Ollama nao esta rodando. Abra o terminal e digite: ollama serve"
    except Exception as e:
        return f"Erro ao falar com o Atlas: {e}"


def responder_com_fontes(pergunta: str, resultados: str, historico: list = None,
                         modelo: str = None, provider: str = "ollama",
                         api_key: str = None) -> str:
    """Responde uma pergunta usando SOMENTE os resultados de busca fornecidos.

    Substitui o "Resuma de forma curta" solto, que era a principal fonte de
    alucinacao: o modelo preenchia lacunas com conhecimento proprio e
    apresentava como se fosse o resultado da busca.
    """
    contexto = (
        "RESULTADOS DE BUSCA (fonte: DuckDuckGo) para a pergunta:\n"
        f"{pergunta}\n\n"
        "--- RESULTADOS ---\n"
        f"{resultados}"
    )
    mensagem = (
        f"Pergunta do Senhor: {pergunta}\n\n"
        "Responda usando EXCLUSIVAMENTE os RESULTADOS DE BUSCA fornecidos no CONTEXTO VERIFICADO. "
        "Regras: 1) nao use conhecimento proprio para completar a resposta; "
        "2) se os resultados nao contiverem a resposta, diga que nao encontrou informacao confiavel; "
        "3) nao invente numeros, datas, precos, URLs ou nomes de pessoas; "
        "4) cite de onde veio cada informacao; "
        "5) seja breve, 2 a 4 frases."
    )
    return chat(mensagem, historico, modelo=modelo, provider=provider,
                api_key=api_key, contexto=contexto, temperature=0.1)


# ---------------------------------------------------------------------------
# Camada de ferramentas (tool calling)
# ---------------------------------------------------------------------------

# Formato do pedido de ferramenta: [[FERRAMENTA: nome | argumento]]
_PADRAO_PEDIDO = re.compile(
    r"\[\[\s*FERRAMENTA\s*:\s*([^|\]\n]+?)\s*(?:\|\s*([^\]\n]*?)\s*)?\]\]",
    re.IGNORECASE,
)


def _parse_pedidos_ferramenta(texto: str) -> list:
    """Extrai os pedidos de ferramenta do texto, na ordem em que aparecem."""
    pedidos = []
    for m in _PADRAO_PEDIDO.finditer(texto or ""):
        nome = (m.group(1) or "").strip().lower().replace(" ", "_").replace("-", "_")
        arg = (m.group(2) or "").strip()
        if nome:
            pedidos.append((nome, arg))
    return pedidos


def _limpar_marcadores(texto: str) -> str:
    """Substitui marcadores de ferramenta que sobraram na resposta final.

    Troca o marcador pelo nome da ferramenta em vez de apagar, para a frase
    continuar gramatical ("dos resultados da ferramenta rede").
    """
    if not texto:
        return texto
    limpo = _PADRAO_PEDIDO.sub(lambda m: (m.group(1) or "").strip(), texto)
    limpo = re.sub(r"\n{3,}", "\n\n", limpo)
    return limpo.strip()


def chat_com_ferramentas(mensagem: str, historico: list = None, modelo: str = None,
                          provider: str = "ollama", api_key: str = None,
                          contexto: str = None, temperature: float = 0.2,
                          max_iteracoes: int = 3, ao_usar_ferramenta=None) -> str:
    """Responde permitindo que o modelo consulte ferramentas com dados reais.

    Fluxo:
      1. O modelo recebe a pergunta + CONTEXTO VERIFICADO + catalogo de ferramentas.
      2. Se ele responder [[FERRAMENTA: nome | arg]], a ferramenta e executada
         e o resultado real volta para o modelo.
      3. O modelo entao responde usando o dado real.

    Se o modelo nunca pedir ferramenta, a resposta volta normalmente.

    `ao_usar_ferramenta`: callback opcional receives o nome da ferramenta,
    usado pela GUI para mostrar o que esta acontecendo.
    """
    from tools import executar, catalogo_texto, INSTRUCAO_FERRAMENTAS

    # Usa replace (e nao format) para o template poder conter chaves literais.
    try:
        instrucao = INSTRUCAO_FERRAMENTAS.replace("{catalogo}", catalogo_texto())
    except Exception:
        instrucao = ""

    hist = list(historico or [])
    hist.append({"role": "user", "content": mensagem})
    contexto_acum = contexto or ""
    ja_executadas = set()

    def _gerar():
        if provider == "gemini" and api_key:
            return _chat_gemini(None, hist, modelo, api_key, contexto=contexto_acum,
                                temperature=temperature, perfil="mordomo",
                                sistema_extra=instrucao)
        return _chat_ollama(None, hist, modelo, contexto=contexto_acum,
                            temperature=temperature, perfil="mordomo",
                            sistema_extra=instrucao)

    try:
        for _ in range(max_iteracoes):
            resposta = _gerar()
            pedidos = _parse_pedidos_ferramenta(resposta)

            if not pedidos:
                return _limpar_marcadores(resposta) or resposta

            blocos = []
            for nome, arg in pedidos:
                chave = (nome, arg.lower())
                if chave in ja_executadas:
                    blocos.append(f"[{nome}] (repetido, resultado anterior vale)")
                    continue
                ja_executadas.add(chave)
                if ao_usar_ferramenta:
                    try:
                        ao_usar_ferramenta(nome)
                    except Exception:
                        pass
                try:
                    saida = executar(nome, arg, api_key=api_key)
                except Exception as e:
                    saida = f"ERRO ao executar a ferramenta '{nome}': {e}"
                blocos.append(f"[{nome}] argumento: {arg or '(nenhum)'}\n{saida}")

            if not blocos:
                return _limpar_marcadores(resposta) or resposta

            bloco = ("RESULTADOS REAIS DAS FERRAMENTAS (dados confirmados do sistema):\n"
                     + "\n\n".join(blocos))
            contexto_acum = (contexto_acum + "\n\n" + bloco).strip()
            hist.append({"role": "assistant", "content": resposta})
            hist.append({"role": "user", "content": bloco + "\n\n"
                                                  "Agora responda ao Senhor usando estes dados reais."})

        # Esgotou as iteracoes: devolve a ultima resposta limpando marcadores.
        return _limpar_marcadores(resposta) or resposta

    except requests.ConnectionError:
        return "Erro: Ollama nao esta rodando. Abra o terminal e digite: ollama serve"
    except Exception as e:
        return f"Erro ao falar com o Atlas: {e}"


def listar_modelos_ollama() -> list:
    """Lista modelos disponiveis no Ollama."""
    try:
        resp = _session.get(f"{HOST}/api/tags", timeout=3)
        resp.raise_for_status()
        return [m["name"] for m in resp.json().get("models", [])]
    except Exception:
        return []


def transcrever_audio(audio_b64: str, api_key: str, modelo: str = None) -> str | None:
    """Transcreve audio usando Gemini multimodal. Retorna texto ou None."""
    if not api_key:
        return None
    try:
        url = f"{GEMINI_API_URL}/{modelo or GEMINI_MODELS[0]}:generateContent"
        resp = _session.post(
            url,
            headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
            json={
                "contents": [{
                    "parts": [
                        {"text": "Transcreva exatamente o que esta sendo falado neste audio. Responda APENAS com o texto transcrito, sem aspas, sem explicacoes, sem pontuacao extra. Se nao houver fala, responda com vazio."},
                        {"inline_data": {"mime_type": "audio/wav", "data": audio_b64}},
                    ]
                }],
                "generationConfig": {"temperature": 0.1, "maxOutputTokens": 256},
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        texto = data["candidates"][0]["content"]["parts"][0]["text"].strip()
        return texto if texto else None
    except Exception:
        return None


def ver_tela(api_key: str, modelo: str = None) -> str:
    """Tira um screenshot e descreve o que ve usando Gemini vision."""
    if not api_key:
        return "Preciso de uma API key do Gemini para ver a tela, Senhor."
    try:
        import pyautogui
        from io import BytesIO
        
        # Tira screenshot
        screenshot = pyautogui.screenshot()
        buffer = BytesIO()
        screenshot.save(buffer, format="PNG")
        img_b64 = base64.b64encode(buffer.getvalue()).decode()
        
        # Envia pra Gemini com visao
        url = f"{GEMINI_API_URL}/{modelo or GEMINI_MODELS[0]}:generateContent"
        resp = _post_com_retry(
            url,
            headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
            json={
                "contents": [{
                    "parts": [
                        {"text": "Voce e Atlas, um mordomo assistente. Descreva DETALHADAMENTE o que voce ve nesta tela de computador. Inclua: 1) Quais programas ou aplicativos estao abertos, 2) Quais websites estao visiveis no navegador, 3) Se ha pastas ou arquivos visiveis, 4) Qualquer outro detalhe relevante. Responda em portugues, em 3-4 frases completas. NAO use markdown, asteriscos ou formatacao."},
                        {"inline_data": {"mime_type": "image/png", "data": img_b64}},
                    ]
                }],
                "generationConfig": {"temperature": 0.3, "maxOutputTokens": 512},
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        texto = data["candidates"][0]["content"]["parts"][0]["text"]
        # Remove formatacao markdown
        texto = texto.replace("**", "").replace("*", "").replace("#", "").strip()
        return texto
    except Exception as e:
        return f"Peço desculpas Senhor, mas nao consegui ver a tela: {e}"


def _criar_imagem_pollinations(descricao: str, destino: str) -> str:
    """Gera uma imagem gratuita usando a API Pollinations (sem chave, sem custo)."""
    from pathlib import Path
    from urllib.parse import quote
    import random as _random

    prompt = f"{descricao}, alta qualidade, detalhado"
    url = ("https://image.pollinations.ai/prompt/"
           f"{quote(prompt)}?width=512&height=512&nologo=true&seed={_random.randint(1, 99999)}")
    resp = _session.get(url, timeout=90)
    resp.raise_for_status()
    img_bytes = resp.content
    if not img_bytes:
        return "Peço desculpas Senhor, mas nao consegui gerar a imagem no momento."

    Path(destino).write_bytes(img_bytes)
    return f"Imagem gerada com sucesso, Senhor. Salvei em: {destino}"


def criar_imagem(descricao: str, api_key: str, modelo: str = None, destino: str = None) -> str:
    """Gera uma imagem. Tenta Gemini (pago) e, se a cota free bloquear, usa o Pollinations (gratuito)."""
    from pathlib import Path

    if destino is None:
        destino = str(Path.home() / "Desktop" / "imagem_gerada.png")

    # Se houver chave Gemini, tenta primeiro (qualidade maxima quando disponivel)
    if api_key:
        try:
            import base64 as _b64

            modelo_img = modelo if modelo and "image" in modelo else "gemini-3.1-flash-lite-image"

            url = f"{GEMINI_API_URL}/{modelo_img}:generateContent"
            resp = _post_com_retry(
                url,
                headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
                json={
                    "contents": [{"parts": [{"text": f"Crie uma imagem de: {descricao}"}]}],
                    "generationConfig": {"temperature": 1.0, "maxOutputTokens": 8192},
                },
                timeout=90,
            )
            resp.raise_for_status()
            data = resp.json()
            img_bytes = None
            for part in data["candidates"][0]["content"]["parts"]:
                if "inlineData" in part:
                    img_bytes = _b64.b64decode(part["inlineData"]["data"])
                    break
            if img_bytes is not None:
                Path(destino).write_bytes(img_bytes)
                return f"Imagem gerada com sucesso, Senhor. Salvei em: {destino}"
        except Exception:
            # Gemini indisponivel/limitado (free tier, 429, etc) -> cai para o gratuito
            pass

    # Fallback gratuito (Pollinations) - nao precisa de chave nem pagar
    try:
        return _criar_imagem_pollinations(descricao, destino)
    except Exception as e:
        return f"Peço desculpas Senhor, mas nao consegui criar a imagem: {e}"
