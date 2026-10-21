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
import hashlib
import json
import time

JARVIS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_URL = "https://github.com/Somaisumser/Atlas-assistent/archive/refs/heads/main.zip"

# Arquivos que nunca devem ser sobrescritos pela atualizacao automatica.
ARQUIVOS_PROTEGIDOS = (
    "config.json",
    "lembretes.json",
    ".last_update_hash",
    ".atlas_state.json",
)

# Extensoes que fazem parte do projeto e por isso sao monitoradas.
EXTENSOES_PROJETO = (".py", ".json", ".md", ".txt", ".bat", ".ps1", ".cfg", ".ini")

ESTADO_PATH = os.path.join(JARVIS_DIR, ".atlas_state.json")


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


def _hash_arquivo(caminho: str) -> str:
    """SHA256 de um arquivo (vazio se nao der para ler)."""
    try:
        digest = hashlib.sha256()
        with open(caminho, "rb") as f:
            for bloco in iter(lambda: f.read(65536), b""):
                digest.update(bloco)
        return digest.hexdigest()
    except Exception:
        return ""


def _manifesto_local() -> dict:
    """Mapa {arquivo: sha256} dos arquivos do projeto nesta pasta."""
    manifesto = {}
    try:
        nomes = sorted(os.listdir(JARVIS_DIR))
    except Exception:
        return manifesto
    for nome in nomes:
        caminho = os.path.join(JARVIS_DIR, nome)
        if not os.path.isfile(caminho):
            continue
        if nome in ARQUIVOS_PROTEGIDOS:
            continue
        if not nome.lower().endswith(EXTENSOES_PROJETO):
            continue
        manifesto[nome] = _hash_arquivo(caminho)
    return manifesto


def _ler_estado() -> dict:
    """Le o estado salvo da ultima verificacao."""
    try:
        if os.path.exists(ESTADO_PATH):
            with open(ESTADO_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def _salvar_estado(manifesto: dict = None, commit_remoto: str = "") -> None:
    """Guarda o estado atual dos arquivos para detectar alteracoes futuras."""
    try:
        if manifesto is None:
            manifesto = _manifesto_local()
        with open(ESTADO_PATH, "w", encoding="utf-8") as f:
            json.dump({"arquivos": manifesto, "commit": commit_remoto}, f, indent=2)
    except Exception:
        pass


def _garantir_estado(commit_remoto: str = "") -> None:
    """Estabelece a linha de base dos arquivos apenas na primeira verificacao.

    A linha de base so pode ser mudada depois de uma atualizacao aplicada,
    senao as alteracoes do usuario deixariam de ser detectadas.
    """
    if _ler_estado().get("arquivos"):
        return
    _salvar_estado(commit_remoto=commit_remoto)


def alteracoes_locais() -> list:
    """Lista de arquivos que o usuario alterou localmente.

    Compara o estado atual com o estado salvo na ultima verificacao.
    """
    salvo = _ler_estado().get("arquivos", {})
    if not salvo:
        return []
    atual = _manifesto_local()
    alterados = [n for n, h in atual.items() if salvo.get(n) and salvo[n] != h]
    removidos = [n for n in salvo if n not in atual]
    return sorted(alterados + removidos)


def _backup_arquivos_locais(arquivos, destino: str = None) -> str:
    """Copia os arquivos informados para uma pasta de backup. Devolve o caminho."""
    if not arquivos:
        return ""
    try:
        if not destino:
            destino = os.path.join(
                JARVIS_DIR, "backup_local_" + time.strftime("%Y%m%d_%H%M%S")
            )
        os.makedirs(destino, exist_ok=True)
        for nome in arquivos:
            origem = os.path.join(JARVIS_DIR, nome)
            if os.path.isfile(origem):
                shutil.copy2(origem, os.path.join(destino, nome))
        return destino
    except Exception:
        return ""


_ultima_verificacao = 0
_INTERVALO_CACHE = 3600  # 1 hora


def verificar_atualizacoes():
    """Verifica se ha atualizacoes pendentes no GitHub com cache de 1h."""
    global _ultima_verificacao
    agora = time.time()
    if (agora - _ultima_verificacao) < _INTERVALO_CACHE:
        return False, "Ja verificado recentemente."

    alterados = alteracoes_locais()

    # Metodo 1: Git (compara o HEAD local com o origin/main)
    if tem_git() and tem_repo():
        _run_git(["fetch", "origin"])
        stdout, code = _run_git(["rev-list", "--count", "HEAD..origin/main"])
        if code == 0:
            try:
                count = int(stdout)
                _ultima_verificacao = agora
                _garantir_estado()
                if count > 0:
                    if alterados:
                        return True, (
                            f"{count} atualizacao(oes) disponivel(is), mas voce tem "
                            f"{len(alterados)} arquivo(s) alterado(s) localmente. "
                            "Faca commit ou stash antes de atualizar."
                        )
                    return True, f"{count} atualizacao(oes) disponivel(is)."
                return False, "Ja esta atualizado."
            except ValueError:
                pass

    # Metodo 2: Compara commit local com remoto via GitHub API
    try:
        # Pega ultimo commit remoto
        req = urllib.request.Request(
            "https://api.github.com/repos/Somaisumser/Atlas-assistent/commits?sha=main&per_page=1",
            headers={"User-Agent": "Atlas-Updater"}
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
                _garantir_estado(commit_remoto=commit_remoto)
                return False, "Primeira verificacao."

            # Compara
            if hash_local != commit_remoto:
                with open(hash_file, "w") as f:
                    f.write(commit_remoto)
                _ultima_verificacao = agora
                _garantir_estado(commit_remoto=commit_remoto)
                if alterados:
                    return True, (
                        f"Novidade: {msg_commit} | Mas voce tem "
                        f"{len(alterados)} arquivo(s) alterado(s) localmente. "
                        "Eles serao preservados."
                    )
                return True, f"Novidade: {msg_commit}"
            else:
                _ultima_verificacao = agora
                _garantir_estado(commit_remoto=commit_remoto)
                if alterados:
                    return False, (
                        f"Ha {len(alterados)} arquivo(s) alterado(s) localmente: "
                        + ", ".join(alterados[:5])
                    )
                return False, "Ja esta atualizado."

    except Exception:
        pass

    _ultima_verificacao = agora
    return False, "Nao foi possivel verificar atualizacoes."


def aplicar_atualizacao_git():
    """Atualiza via Git (git pull)."""
    alterados = alteracoes_locais()
    stdout, code = _run_git(["pull", "origin", "main"])
    if code == 0:
        _salvar_estado()
        if "Already up to date" in stdout or "already up-to-date" in stdout.lower():
            return True, "Ja esta atualizado."
        return True, "Atualizado com sucesso! Reinicie o Atlas."
    # Falhou: normalmente e por alteracoes locais em conflito
    if alterados:
        return False, (
            "Erro ao atualizar: voce tem alteracoes locais em "
            + ", ".join(alterados[:5])
            + ". Faca commit ou stash antes de atualizar."
        )
    return False, f"Erro ao atualizar: {stdout}"


def aplicar_atualizacao_zip():
    """Atualiza baixando o ZIP, sem sobrescrever alteracoes locais."""
    try:
        # Salva lembretes
        lembretes_path = os.path.join(JARVIS_DIR, "lembretes.json")
        tem_lembretes = os.path.exists(lembretes_path)
        if tem_lembretes:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as tmp:
                shutil.copy2(lembretes_path, tmp.name)
                tmp_lembretes = tmp.name

        # Arquivos alterados localmente: sao salvos em backup e preservados
        alterados = alteracoes_locais()
        backup = _backup_arquivos_locais(alterados)

        # Baixa ZIP
        tmp_zip = os.path.join(tempfile.gettempdir(), "atlas-update.zip")
        urllib.request.urlretrieve(REPO_URL, tmp_zip)

        # Extrai
        tmp_extract = os.path.join(tempfile.gettempdir(), "atlas-update")
        with zipfile.ZipFile(tmp_zip, 'r') as z:
            z.extractall(tmp_extract)

        # Copia arquivos (preserva venv, backups, lembretes)
        preserve = ["venv", "backups", "__pycache__", "codigos", "lembretes.json",
                    "config.json", ".git", ".atlas_state.json", ".last_update_hash"]
        src = os.path.join(tmp_extract, "Atlas-assistent-main")

        for item in os.listdir(src):
            if item in preserve or item.startswith("backup_"):
                continue
            src_path = os.path.join(src, item)
            dst_path = os.path.join(JARVIS_DIR, item)
            # Nao sobrescreve o que o usuario alterou localmente
            if item in alterados:
                continue
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

        _salvar_estado()

        if backup:
            return True, (
                "Atualizado com sucesso! Reinicie o Atlas. "
                f"Seus {len(alterados)} arquivo(s) alterado(s) foram preservados em: {backup}"
            )
        return True, "Atualizado com sucesso! Reinicie o Atlas."
    except Exception as e:
        return False, f"Erro ao atualizar: {e}"


def aplicar_atualizacao():
    """Aplica atualizacao pelo metodo disponivel."""
    if tem_git() and tem_repo():
        return aplicar_atualizacao_git()
    return aplicar_atualizacao_zip()


def reiniciar():
    """Reinicia o Atlas."""
    python = sys.executable
    os.execl(python, python, *sys.argv)
