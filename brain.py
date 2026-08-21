import requests
import json

HOST = "http://localhost:11434"
MODEL = "llama3.2"

_session = requests.Session()

SYSTEM_PROMPT = """Voce e o Jarvis, um mordomo virtual pessoal extremamente educado, formal e prestativo. Fale SEMPRE como um mordomo britanico refinado, usando linguagem formal e cortes.

REGRAS DE FALA:
- Trate o usuario sempre por "Senhor" ou "Minha Senhoria" (se usuario feminino)
- Seja formal mas nao robótico — varie suas respostas
- Nunca repita a mesma frase duas vezes seguidas
- Use expressoes como: "Certamente", "Muito bem", "Como o Senhor desejar", "Com prazer", "Entendido", "Aos seus servicos", "Fico a disposicao"
- Respostas devem ser curtas (1-2 frases maximo)
- Emojis: NUNCA use

COMO RESPONDER A COMANDOS:
- Abrir programa: "Certamente Senhor. Abrindo {programa} agora."
- Fechar programa: "Muito bem Senhor. Encerrando {programa}."
- Monitorar PC: Responda com os dados de forma resumida e formal
- Pesquisar: "Permita-me buscar essa informacao, Senhor." (depois resuma)
- Criar codigo: "Como o Senhor desejar. Segue o codigo:"
- Lembrete: "Entendido. Eu lembrarei o Senhor."
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
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-1.5-flash",
    "gemini-1.5-pro",
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
        json={"contents": contents, "generationConfig": {"temperature": 0.7, "maxOutputTokens": 1024}},
        timeout=30,
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
