"""
Jarver - Verificador de Atualizacoes
Verifica se ha atualizacoes no GitHub ao iniciar.
"""
import subprocess
import os
import sys
import threading
import urllib.request
import zipfile
import tempfile
import shutil

JARVIS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_URL = "https://github.com/Somaisumser/jarvis-assistent/archive/refs/heads/main.zip"


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


_ultima_verificacao = 0
_INTERVALO_CACHE = 3600  # 1 hora


def verificar_atualizacoes():
    """Verifica se ha atualizacoes pendentes no GitHub com cache de 1h."""
    import time
    agora = time.time()
    if (agora - _ultima_verificacao) < _INTERVALO_CACHE:
        return False, "Ja verificado recentemente."

    # Metodo 1: Git
    if tem_git() and tem_repo():
        _run_git(["fetch", "origin"])
        stdout, code = _run_git(["rev-list", "--count", "HEAD..origin/main"])
        if code == 0:
            try:
                count = int(stdout)
                if count > 0:
                    _ultima_verificacao = agora
                    return True, f"{count} atualizacao(oes) disponivel(is)."
                else:
                    _ultima_verificacao = agora
                    return False, "Ja esta atualizado."
            except ValueError:
                pass

    # Metodo 2: Compara commit local com remoto via GitHub API
    try:
        import json

        # Pega ultimo commit remoto
        req = urllib.request.Request(
            "https://api.github.com/repos/Somaisumser/jarvis-assistent/commits?sha=main&per_page=1",
            headers={"User-Agent": "Jarvis-Updater"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            dados = json.loads(resp.read())
            if not dados:
                _ultima_verificacao = agora
                return False, "Nao foi possivel verificar."

            commit_remoto = dados[0]["sha"]
            msg_commit = dados[0]["commit"]["message"].split("\n")[0]

            # Salva/le hash do ultimo commit conhecido
            hash_file = os.path.join(JARVIS_DIR, ".last_update_hash")
            hash_local = ""
            if os.path.exists(hash_file):
                with open(hash_file, "r") as f:
                    hash_local = f.read().strip()

            # Se nao tem hash salvo, salva o atual e nao avisa
            if not hash_local:
                with open(hash_file, "w") as f:
                    f.write(commit_remoto)
                _ultima_verificacao = agora
                return False, "Primeira verificacao."

            # Compara
            if hash_local != commit_remoto:
                with open(hash_file, "w") as f:
                    f.write(commit_remoto)
                _ultima_verificacao = agora
                return True, f"Novidade: {msg_commit}"
            else:
                _ultima_verificacao = agora
                return False, "Ja esta atualizado."

    except Exception:
        pass

    _ultima_verificacao = agora
    return False, "Nao foi possivel verificar atualizacoes."


def aplicar_atualizacao_git():
    """Baixa e aplica as atualizacoes via Git."""
    stdout, code = _run_git(["pull", "origin", "main"])
    if code == 0:
        if "Already up to date" in stdout or "nao ha nada para" in stdout.lower():
            return True, "Ja esta atualizado."
        return True, "Atualizado com sucesso! Reinicie o Jarvis."
    return False, f"Erro ao atualizar: {stdout}"


def aplicar_atualizacao_zip():
    """Baixa e aplica as atualizacoes via ZIP."""
    try:
        # Salva lembretes
        lembretes_path = os.path.join(JARVIS_DIR, "lembretes.json")
        tem_lembretes = os.path.exists(lembretes_path)
        if tem_lembretes:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as tmp:
                shutil.copy2(lembretes_path, tmp.name)
                tmp_lembretes = tmp.name

        # Baixa ZIP
        tmp_zip = os.path.join(tempfile.gettempdir(), "jarvis-update.zip")
        urllib.request.urlretrieve(REPO_URL, tmp_zip)

        # Extrai
        tmp_extract = os.path.join(tempfile.gettempdir(), "jarvis-update")
        with zipfile.ZipFile(tmp_zip, 'r') as z:
            z.extractall(tmp_extract)

        # Copia arquivos (preserva venv, backups, lembretes)
        preserve = ["venv", "backups", "__pycache__", "lembretes.json"]
        src = os.path.join(tmp_extract, "jarvis-assistent-main")

        for item in os.listdir(src):
            if item in preserve:
                continue
            src_path = os.path.join(src, item)
            dst_path = os.path.join(JARVIS_DIR, item)
            if os.path.isdir(src_path):
                if os.path.exists(dst_path):
                    shutil.rmtree(dst_path)
                shutil.copytree(src_path, dst_path)
            else:
                shutil.copy2(src_path, dst_path)

        # Restaura lembretes
        if tem_lembretes:
            shutil.copy2(tmp_lembretes, lembretes_path)
            os.remove(tmp_lembretes)

        # Limpa
        shutil.rmtree(tmp_extract, ignore_errors=True)
        os.remove(tmp_zip)

        # Atualiza dependencias
        venv_pip = os.path.join(JARVIS_DIR, "venv", "Scripts", "pip.exe")
        venv_python = os.path.join(JARVIS_DIR, "venv", "Scripts", "python.exe")
        req_path = os.path.join(JARVIS_DIR, "requirements.txt")
        if os.path.exists(venv_pip) and os.path.exists(req_path):
            subprocess.run([venv_pip, "install", "-r", req_path, "--quiet"],
                         capture_output=True, timeout=120)

        return True, "Atualizado com sucesso! Reinicie o Jarvis."
    except Exception as e:
        return False, f"Erro ao atualizar: {e}"


def aplicar_atualizacao():
    """Aplica atualizacao pelo metodo disponivel."""
    if tem_git() and tem_repo():
        return aplicar_atualizacao_git()
    return aplicar_atualizacao_zip()


def reiniciar():
    """Reinicia o Jarvis."""
    python = sys.executable
    os.execl(python, python, *sys.argv)
