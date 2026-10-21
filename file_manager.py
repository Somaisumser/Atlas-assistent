import os
import re
import shutil
from pathlib import Path


HOME = Path.home()

# Atalhos para pastas comuns do Windows
PASTAS_COMUNS = {
    "downloads": HOME / "Downloads",
    "download": HOME / "Downloads",
    "documentos": HOME / "Documents",
    "documento": HOME / "Documents",
    "area de trabalho": HOME / "Desktop",
    "desktop": HOME / "Desktop",
    "imagens": HOME / "Pictures",
    "imagem": HOME / "Pictures",
    "videos": HOME / "Videos",
    "video": HOME / "Videos",
    "musicas": HOME / "Music",
    "musica": HOME / "Music",
    "music": HOME / "Music",
    "pasta inicial": HOME,
    "home": HOME,
    "perfil": HOME,
    "appdata": HOME / "AppData",
    "appdata local": HOME / "AppData" / "Local",
    "appdata roaming": HOME / "AppData" / "Roaming",
    "onedrive": HOME / "OneDrive",
    "meus documentos": HOME / "Documents",
    "minhas imagens": HOME / "Pictures",
    "meus videos": HOME / "Videos",
    "minhas musicas": HOME / "Music",
}

# Artigos/preposicoes que costumam preceder o caminho na fala ("na area de trabalho").
_ARTIGOS_INICIAIS = re.compile(
    r"^\s*(?:na|no|em|para|dentro\s+d[ae]|dentro\s+do|o|a)\s+", re.IGNORECASE
)

# Aliases do mais longo para o mais curto, para que "appdata local" venca "appdata".
_ALIAS_ORDENADOS = sorted(PASTAS_COMUNS.keys(), key=len, reverse=True)


def _resolver_caminho(caminho: str) -> str:
    """Resolve atalhos de pastas comuns para caminhos reais.

    Aceita, alem do alias exato ("desktop"):
      - alias como primeiro componente: "desktop/notas.txt", "area de trabalho\\a.txt"
      - alias separado por espaco:       "area de trabalho notas.txt"
      - artigo/preposicao inicial:       "na area de trabalho/notas.txt"

    Nao altera a caixa do caminho e nunca remove pedacos do nome do arquivo
    (a versao anterior removia "desktop" da string e quebrava o caminho).
    """
    if not caminho:
        return caminho

    bruto = caminho.strip()
    if not bruto:
        return bruto

    # 1) Remove artigos/preposicoes iniciais ("na ", "no ", "em ", "para o ", ...)
    limpo = bruto
    for _ in range(3):
        novo = _ARTIGOS_INICIAIS.sub("", limpo, count=1).strip()
        if novo == limpo:
            break
        limpo = novo

    chave = limpo.lower()

    # 2) Alias exato
    if chave in PASTAS_COMUNS:
        return str(PASTAS_COMUNS[chave])

    # 3) Alias como primeiro componente do caminho
    for alias in _ALIAS_ORDENADOS:
        if not chave.startswith(alias):
            continue
        resto = limpo[len(alias):]
        if resto[:1] in ("\\", "/"):
            return os.path.join(str(PASTAS_COMUNS[alias]), resto[1:])
        if resto[:1] == " ":
            return os.path.join(str(PASTAS_COMUNS[alias]), resto.strip())
        break

    return limpo


def _caminho_existente(caminho: str) -> str:
    """Devolve o caminho real de um arquivo/pasta existente.

    Se o caminho nao existir e for relativo, procura tambem na Area de
    Trabalho (e onde o arquivo foi criado por padrao).
    """
    alvo = Path(caminho)
    if alvo.exists():
        return caminho
    if not os.path.isabs(caminho):
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        alternativa = os.path.join(desktop, caminho)
        if Path(alternativa).exists():
            return alternativa
    return caminho


def list_dir(caminho: str = ".") -> str:
    """Lista arquivos e pastas de um diretorio."""
    try:
        caminho = _resolver_caminho(caminho)
        itens = list(Path(caminho).iterdir())
        if not itens:
            return "A pasta se encontra vazia, Senhor."
        pastas = sorted([i.name for i in itens if i.is_dir()])
        arquivos = sorted([i.name for i in itens if i.is_file()])
        partes = []
        if pastas:
            partes.append(f"Pastas ({len(pastas)}): {', '.join(pastas[:15])}")
        if arquivos:
            partes.append(f"Arquivos ({len(arquivos)}): {', '.join(arquivos[:15])}")
        return "\n".join(partes)
    except Exception as e:
        return f"Peço desculpas Senhor, mas ocorreu um erro: {e}"


def create_file(caminho: str, conteudo: str = "") -> str:
    """Cria um arquivo com conteudo."""
    try:
        caminho = _resolver_caminho(caminho)
        if not caminho or not caminho.strip():
            caminho = "mensagem.txt"

        # Caminho relativo sem pasta: vai para a Area de Trabalho.
        if not os.path.isabs(caminho):
            desktop = os.path.join(os.path.expanduser("~"), "Desktop")
            caminho = os.path.join(desktop, caminho)

        Path(caminho).parent.mkdir(parents=True, exist_ok=True)
        Path(caminho).write_text(conteudo, encoding="utf-8")
        return f"Arquivo criado com sucesso, Senhor: {caminho}"
    except Exception as e:
        return f"Peço desculpas Senhor, mas nao consegui criar o arquivo: {e}"


def read_file(caminho: str) -> str:
    """Le o conteudo de um arquivo."""
    try:
        caminho = _caminho_existente(_resolver_caminho(caminho))
        conteudo = Path(caminho).read_text(encoding="utf-8")
        if len(conteudo) > 2000:
            return conteudo[:2000] + "\n... (truncado)"
        return conteudo
    except Exception as e:
        return f"Peço desculpas Senhor, mas nao consegui ler o arquivo: {e}"


def delete_file(caminho: str) -> str:
    """Deleta um arquivo ou pasta."""
    try:
        caminho = _caminho_existente(_resolver_caminho(caminho))
        alvo = Path(caminho)
        if alvo.is_dir():
            shutil.rmtree(alvo)
            return f"Pasta removida, Senhor: {caminho}"
        alvo.unlink()
        return f"Arquivo removido, Senhor: {caminho}"
    except Exception as e:
        return f"Peço desculpas Senhor, mas nao consegui remover: {e}"


def move_file(origem: str, destino: str) -> str:
    """Move um arquivo."""
    try:
        origem = _resolver_caminho(origem)
        destino = _resolver_caminho(destino)
        Path(destino).parent.mkdir(parents=True, exist_ok=True)
        shutil.move(origem, destino)
        return f"Arquivo movido, Senhor. De {origem} para {destino}"
    except Exception as e:
        return f"Peço desculpas Senhor, mas nao consegui mover o arquivo: {e}"


def copy_file(origem: str, destino: str) -> str:
    """Copia um arquivo."""
    try:
        origem = _resolver_caminho(origem)
        destino = _resolver_caminho(destino)
        Path(destino).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(origem, destino)
        return f"Arquivo copiado, Senhor. Para {destino}"
    except Exception as e:
        return f"Peço desculpas Senhor, mas nao consegui copiar o arquivo: {e}"
