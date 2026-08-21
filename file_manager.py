import os
import shutil
from pathlib import Path


HOME = Path.home()


def list_dir(caminho: str = ".") -> str:
    """Lista arquivos e pastas de um diretorio."""
    try:
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
        Path(caminho).parent.mkdir(parents=True, exist_ok=True)
        Path(caminho).write_text(conteudo, encoding="utf-8")
        return f"Arquivo criado com sucesso, Senhor: {caminho}"
    except Exception as e:
        return f"Peço desculpas Senhor, mas nao consegui criar o arquivo: {e}"


def read_file(caminho: str) -> str:
    """Le o conteudo de um arquivo."""
    try:
        conteudo = Path(caminho).read_text(encoding="utf-8")
        if len(conteudo) > 2000:
            return conteudo[:2000] + "\n... (truncado)"
        return conteudo
    except Exception as e:
        return f"Peço desculpas Senhor, mas nao consegui ler o arquivo: {e}"


def delete_file(caminho: str) -> str:
    """Deleta um arquivo ou pasta."""
    try:
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
        shutil.move(origem, destino)
        return f"Arquivo movido, Senhor. De {origem} para {destino}"
    except Exception as e:
        return f"Peço desculpas Senhor, mas nao consegui mover o arquivo: {e}"


def copy_file(origem: str, destino: str) -> str:
    """Copia um arquivo."""
    try:
        shutil.copy2(origem, destino)
        return f"Arquivo copiado, Senhor. Para {destino}"
    except Exception as e:
        return f"Peço desculpas Senhor, mas nao consegui copiar o arquivo: {e}"
