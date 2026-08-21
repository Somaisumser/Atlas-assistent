"""
Jarver - Verificador de Atualizacoes
Verifica se ha atualizacoes no GitHub ao iniciar.
"""
import subprocess
import os
import sys
import threading

JARVIS_DIR = os.path.dirname(os.path.abspath(__file__))


def _run_git(args):
    """Roda um comando git e retorna o resultado."""
    try:
        resultado = subprocess.run(
            ["git"] + args,
            cwd=JARVIS_DIR,
            capture_output=True,
            text=True,
            timeout=15,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        )
        return resultado.stdout.strip(), resultado.returncode
    except FileNotFoundError:
        return None, -1
    except Exception:
        return None, -2


def tem_git():
    """Verifica se o Git esta instalado."""
    stdout, code = _run_git(["--version"])
    return code == 0


def tem_repo():
    """Verifica se a pasta e um repositorio Git."""
    stdout, code = _run_git(["rev-parse", "--is-inside-work-tree"])
    return code == 0 and stdout == "true"


def verificar_atualizacoes():
    """Verifica se ha atualizacoes pendentes no GitHub."""
    if not tem_git() or not tem_repo():
        return False, "Git nao configurado."

    # Busca atualizacoes remotas
    _run_git(["fetch", "origin"])

    # Compara local com remoto
    stdout, code = _run_git(["rev-list", "--count", "HEAD..origin/main"])
    if code != 0:
        return False, "Erro ao verificar atualizacoes."

    try:
        count = int(stdout)
    except ValueError:
        return False, "Erro ao interpretar resultado."

    if count > 0:
        return True, f"{count} atualizacao(oes) disponivel(is)."
    else:
        return False, "Ja esta atualizado."


def aplicar_atualizacao(callback_status=None):
    """Baixa e aplica as atualizacoes."""
    if callback_status:
        callback_status("Baixando atualizacoes...")

    stdout, code = _run_git(["pull", "origin", "main"])

    if code == 0:
        if "Already up to date" in stdout or "nao ha nada para" in stdout.lower():
            return True, "Ja esta atualizado."
        else:
            return True, "Atualizado com sucesso! Reinicie o Jarvis."
    else:
        return False, f"Erro ao atualizar: {stdout}"


def reiniciar():
    """Reinicia o Jarvis."""
    python = sys.executable
    os.execl(python, python, *sys.argv)
