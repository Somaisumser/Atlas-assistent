import requests

TIMEOUT = 10
MAX_RESULTS = 5


def search(query: str) -> str:
    """Pesquisa na internet usando DuckDuckGo."""
    try:
        from ddgs import DDGS
        with DDGS(timeout=TIMEOUT) as ddgs:
            results = list(ddgs.text(query, region="br-pt", max_results=MAX_RESULTS))
    except ImportError:
        return "Erro: instale ddgs com: pip install ddgs"
    except Exception as e:
        return f"Erro ao pesquisar: {e}"

    if not results:
        return "Nenhum resultado encontrado."

    partes = []
    for i, r in enumerate(results, 1):
        titulo = r.get("title", "")
        corpo = r.get("body", "")
        partes.append(f"{i}. {titulo}\n{corpo}")
    return "\n\n".join(partes)
