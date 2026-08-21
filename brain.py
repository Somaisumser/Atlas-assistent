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


def chat(mensagem: str, historico: list = None, modelo: str = None) -> str:
    """Envia mensagem pro Ollama e retorna a resposta."""
    modelo_usar = modelo or MODEL
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if historico:
        messages.extend(historico[-10:])
    messages.append({"role": "user", "content": mensagem})

    try:
        resp = _session.post(
            f"{HOST}/api/chat",
            json={
                "model": modelo_usar,
                "messages": messages,
                "stream": False,
                "keep_alive": "30m",
            },
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json().get("message", {}).get("content", "Sem resposta.")
    except requests.ConnectionError:
        return "Erro: Ollama nao esta rodando. Abra o terminal e digite: ollama serve"
    except Exception as e:
        return f"Erro ao falar com o Jarvis: {e}"


def chat_stream(mensagem: str, historico: list = None, modelo: str = None):
    """Envia mensagem pro Ollama e yield chunks (streaming)."""
    modelo_usar = modelo or MODEL
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if historico:
        messages.extend(historico[-10:])
    messages.append({"role": "user", "content": mensagem})

    try:
        resp = _session.post(
            f"{HOST}/api/chat",
            json={
                "model": modelo_usar,
                "messages": messages,
                "stream": True,
                "keep_alive": "30m",
            },
            timeout=120,
            stream=True,
        )
        resp.raise_for_status()
        for line in resp.iter_lines():
            if line:
                data = json.loads(line)
                chunk = data.get("message", {}).get("content", "")
                if chunk:
                    yield chunk
    except requests.ConnectionError:
        yield "Erro: Ollama nao esta rodando. Abra o terminal e digite: ollama serve"
    except Exception as e:
        yield f"Erro ao falar com o Jarvis: {e}"


def listar_modelos() -> list:
    """Lista modelos disponiveis no Ollama."""
    try:
        resp = _session.get(f"{HOST}/api/tags", timeout=3)
        resp.raise_for_status()
        return [m["name"] for m in resp.json().get("models", [])]
    except Exception:
        return []
