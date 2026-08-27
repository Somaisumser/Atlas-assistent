import requests
import json
import base64

HOST = "http://localhost:11434"
MODEL = "llama3.2"

_session = requests.Session()

SYSTEM_PROMPT = """Voce e o Jarvis, um mordomo virtual pessoal extremamente educado, formal e prestativo. Fale SEMPRE como um mordomo britanico refinado, usando linguagem formal e cortes.

REGRAS DE FALA:
- Trate o usuario sempre por "Senhor" ou "Minha Senhoria" (se usuario feminino)
- Seja formal mas nao robótico — varie suas respostas
- Nunca repita a mesma frase duas vezes seguidas
- Use expressoes como: "Certamente", "Muito bem", "Como o Senhor desejar", "Com prazer", "Entendido", "Aos seus servicos", "Fico a disposicao"
- Respostas devem ter entre 2-4 frases, suficiente para explicar o que fez
- Emojis: NUNCA use

COMO RESPONDER A COMANDOS:
- Abrir programa: "Certamente Senhor. Abrindo {programa} agora. Encontrei instalado em [local]."
- Fechar programa: "Muito bem Senhor. Encerrando {programa}. O programa foi finalizado com sucesso."
- Monitorar PC: Responda com os dados de forma resumida e formal, comentando se esta bom ou ruim
- Pesquisar: "Permita-me buscar essa informacao, Senhor." (depois resuma em 3-4 frases)
- Criar codigo: "Como o Senhor desejar. Segue o codigo:"
- Lembrete: "Entendido. Eu lembrarei o Senhor de [texto] em [tempo]."
- Ver tela: Descreva em 3-4 frases o que ve na tela
- Nao entendeu: "Peço desculpas, Senhor, mas nao captei bem. Poderia repetir?"

VARIAÇÕES (varie entre essas, NUNCA repita a mesma):
- "Certamente Senhor."
- "Muito bem, Senhor."
- "Aos seus servicos, Senhor."
- "Com prazer, Senhor."
- "Como o Senhor desejar."
- "Entendido, Senhor."
- "Fico a disposicao."
- "Imediatamente, Senhor."
- "Seja feito conforme pedido, Senhor."
- "Tenho o prazer de atende-lo, Senhor."

Quando o usuario pedir algo geral (pergunta, conversa), responda como mordomo de forma util e curta.

NUNCA diga "Eu sou uma IA" ou "Sou um assistente". Voce e o JARVIS, mordomo pessoal do Senhor."""

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models"
GEMINI_MODELS = [
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.7-flash",
]


def _chat_ollama(mensagem, historico, modelo):
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if historico:
        messages.extend(historico[-10:])
    messages.append({"role": "user", "content": mensagem})

    resp = _session.post(
        f"{HOST}/api/chat",
        json={"model": modelo or MODEL, "messages": messages, "stream": False, "keep_alive": "30m"},
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json().get("message", {}).get("content", "Sem resposta.")


def _chat_gemini(mensagem, historico, modelo, api_key):
    url = f"{GEMINI_API_URL}/{modelo or GEMINI_MODELS[0]}:generateContent"

    contents = []
    if historico:
        for msg in historico[-10:]:
            role = "user" if msg["role"] == "user" else "model"
            contents.append({"role": role, "parts": [{"text": msg["content"]}]})
    contents.append({"role": "user", "parts": [{"text": mensagem}]})

    system_msg = {"role": "user", "parts": [{"text": SYSTEM_PROMPT}]}
    contents.insert(0, system_msg)

    resp = _session.post(
        url,
        headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
        json={"contents": contents, "generationConfig": {"temperature": 0.7, "maxOutputTokens": 8192}},
        timeout=120,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["candidates"][0]["content"]["parts"][0]["text"]


def chat(mensagem: str, historico: list = None, modelo: str = None,
         provider: str = "ollama", api_key: str = None) -> str:
    """Envia mensagem e retorna a resposta. Provider: ollama, gemini."""
    try:
        if provider == "gemini" and api_key:
            return _chat_gemini(mensagem, historico, modelo, api_key)
        else:
            return _chat_ollama(mensagem, historico, modelo)
    except requests.ConnectionError:
        return "Erro: Ollama nao esta rodando. Abra o terminal e digite: ollama serve"
    except Exception as e:
        return f"Erro ao falar com o Jarvis: {e}"


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
        resp = _session.post(
            url,
            headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
            json={
                "contents": [{
                    "parts": [
                        {"text": "Voce e Jarvis, um mordomo assistente. Descreva DETALHADAMENTE o que voce ve nesta tela de computador. Inclua: 1) Quais programas ou aplicativos estao abertos, 2) Quais websites estao visiveis no navegador, 3) Se ha pastas ou arquivos visiveis, 4) Qualquer outro detalhe relevante. Responda em portugues, em 3-4 frases completas. NAO use markdown, asteriscos ou formatacao."},
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


def criar_imagem(descricao: str, api_key: str, modelo: str = None, destino: str = None) -> str:
    """Gera uma imagem usando o Gemini Imagen. Retorna o caminho do arquivo."""
    if not api_key:
        return "Preciso de uma API key do Gemini para criar imagens, Senhor."
    try:
        from pathlib import Path
        
        # Modelo de imagem
        modelo_img = "imagen-3.0-generate-002"
        
        if destino is None:
            destino = str(Path.home() / "Desktop" / "imagem_gerada.png")
        
        url = f"{GEMINI_API_URL}/{modelo_img}:predict"
        resp = _session.post(
            url,
            headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
            json={
                "instances": [{"prompt": descricao}],
                "parameters": {
                    "sampleCount": 1,
                    "aspectRatio": "1:1",
                    "personGeneration": "allow_all",
                },
            },
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        
        b64 = data["predictions"][0]["bytesBase64Encoded"]
        import base64 as _b64
        img_bytes = _b64.b64decode(b64)
        
        Path(destino).write_bytes(img_bytes)
        return f"Imagem gerada com sucesso, Senhor. Salvei em: {destino}"
    except Exception as e:
        return f"Peço desculpas Senhor, mas nao consegui criar a imagem: {e}"
