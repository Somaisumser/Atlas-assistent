import os
import platform
import subprocess
import psutil
import random
import time
import win32gui
import win32con
import glob as _glob
import re
import shutil

SYSTEM = platform.system()


def _listar_monitores():
    """Lista monitores disponiveis com suas posicoes."""
    monitores = []
    try:
        from screeninfo import get_monitors
        for i, m in enumerate(get_monitors(), 1):
            monitores.append({
                "numero": i,
                "x": m.x,
                "y": m.y,
                "largura": m.width,
                "altura": m.height,
                "nome": m.name if hasattr(m, 'name') else f"Monitor {i}",
            })
    except Exception:
        monitores.append({"numero": 1, "x": 0, "y": 0, "largura": 1920, "altura": 1080, "nome": "Monitor 1"})
    return monitores


def _mover_para_monitor(titulo_janela, num_monitor):
    """Move uma janela para o monitor especificado."""
    monitores = _listar_monitores()
    if num_monitor < 1 or num_monitor > len(monitores):
        return False

    alvo = monitores[num_monitor - 1]
    encontrado = [False]

    def callback(hwnd, _):
        if win32gui.IsWindowVisible(hwnd) and titulo_janela.lower() in win32gui.GetWindowText(hwnd).lower():
            try:
                win32gui.SetWindowPos(hwnd, None, alvo["x"] + 50, alvo["y"] + 50, 0, 0,
                                       win32con.SWP_NOSIZE | win32con.SWP_NOZORDER)
                encontrado[0] = True
                return False
            except Exception:
                pass
        return True

    for _ in range(10):
        try:
            win32gui.EnumWindows(callback, None)
        except Exception:
            pass
        if encontrado[0]:
            break
        time.sleep(0.3)
    return encontrado[0]


def _obter_janela_recente(nome):
    """Encontra a janela mais recente de um programa."""
    janelas = []
    def callback(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            texto = win32gui.GetWindowText(hwnd)
            if nome.lower() in texto.lower():
                janelas.append(hwnd)
        return True
    try:
        win32gui.EnumWindows(callback, None)
    except Exception:
        pass
    return janelas[-1] if janelas else None


def _mover_janela_para(hwnd, num_monitor):
    """Move uma janela especifica para o monitor."""
    monitores = _listar_monitores()
    if num_monitor < 1 or num_monitor > len(monitores):
        return False
    alvo = monitores[num_monitor - 1]
    try:
        # Primeiro remove maximizado
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        time.sleep(0.1)
        win32gui.SetWindowPos(hwnd, None, alvo["x"] + 50, alvo["y"] + 50, 0, 0,
                               win32con.SWP_NOSIZE | win32con.SWP_NOZORDER)
        return True
    except Exception:
        return False

_ABRIR_VARIAÇÕES = [
    "Certamente Senhor. Abrindo {nome} agora.",
    "Muito bem Senhor. Abrindo {nome} para o Senhor.",
    "Com prazer Senhor. Abrindo {nome}.",
    "Aos seus servicos Senhor. Abrindo {nome}.",
    "Imediatamente Senhor. Abrindo {nome}.",
    "Entendido Senhor. Abrindo {nome}.",
    "Como o Senhor desejar. Abrindo {nome}.",
]

_FECHAR_VARIAÇÕES = [
    "Muito bem Senhor. Encerrando {nome}.",
    "Certamente Senhor. Fechando {nome}.",
    "Entendido Senhor. Encerrando {nome}.",
    "Como o Senhor desejar. Fechando {nome}.",
    "Imediatamente Senhor. Encerrando {nome}.",
    "Com prazer Senhor. Fechando {nome}.",
]

_NAO_ENCONTRADO = [
    "Peço desculpas Senhor, mas nao encontrei {nome} instalado.",
    "Lamento Senhor, mas {nome} nao foi encontrado no sistema.",
    "Senhor, nao consegui localizar {nome}.",
]


def _tentar_caminhos(caminhos, nome_exibicao):
    """Tenta abrir um programa em varios caminhos possiveis."""
    import glob as _glob
    user = os.path.expanduser("~")
    for caminho in caminhos:
        caminho = caminho.replace("~", user)
        try:
            encontrados = _glob.glob(caminho)
            if encontrados:
                subprocess.Popen(f'start "" "{encontrados[0]}"', shell=True)
                return random.choice(_ABRIR_VARIAÇÕES).format(nome=nome_exibicao)
            if os.path.isfile(caminho):
                subprocess.Popen(f'start "" "{caminho}"', shell=True)
                return random.choice(_ABRIR_VARIAÇÕES).format(nome=nome_exibicao)
        except:
            continue
    return None


def _procurar_jogo_steam(nome: str) -> str | None:
    """Procura um jogo na pasta do Steam e retorna o caminho do executavel."""
    user = os.path.expanduser("~")
    steam_paths = [
        "C:/Program Files (x86)/Steam/steamapps/common",
        "C:/Program Files/Steam/steamapps/common",
        f"{user}/Steam/steamapps/common",
        f"{user}/AppData/Local/Steam/steamapps/common",
    ]
    # Verifica bibliotecas adicionais do Steam
    libraryfolders = [
        "C:/Program Files (x86)/Steam/steamapps/libraryfolders.vdf",
    ]
    for vf in libraryfolders:
        try:
            if os.path.isfile(vf):
                with open(vf, "r", encoding="utf-8", errors="ignore") as f:
                    for linha in f:
                        if '"path"' in linha:
                            import re as _re
                            m = _re.search(r'"path"\s+"([^"]+)"', linha)
                            if m:
                                caminho = m.group(1).replace("\\\\", "/").replace("\\", "/")
                                path_common = os.path.join(caminho, "steamapps/common").replace("\\", "/")
                                if path_common not in steam_paths:
                                    steam_paths.append(path_common)
        except Exception:
            continue

    # Extensoes de executaveis do Windows
    extensoes = (".exe",)

    for base_path in steam_paths:
        if not os.path.isdir(base_path):
            continue
        try:
            for pasta_jogo in os.listdir(base_path):
                if not os.path.isdir(os.path.join(base_path, pasta_jogo)):
                    continue
                nome_pasta = pasta_jogo.lower().replace(" ", "").replace("-", "").replace("_", "")
                nome_busca = nome.replace(" ", "").replace("-", "").replace("_", "")
                if nome_busca in nome_pasta or nome_pasta in nome_busca or nome_pasta.startswith(nome_busca[:4]):
                    pasta_completa = os.path.join(base_path, pasta_jogo)
                    # 1) Procura .exe na raiz da pasta do jogo
                    for arquivo in os.listdir(pasta_completa):
                        if arquivo.lower().endswith(extensoes):
                            caminho_exe = os.path.join(pasta_completa, arquivo)
                            nome_exe = arquivo.lower().replace(".exe", "").replace(" ", "").replace("-", "")
                            if nome_busca in nome_exe or nome_exe.startswith(nome_busca[:4]):
                                return caminho_exe
                    # 2) Pega primeiro .exe da raiz
                    for arquivo in os.listdir(pasta_completa):
                        if arquivo.lower().endswith(extensoes):
                            return os.path.join(pasta_completa, arquivo)
                    # 3) Busca em subpastas (1 nivel)
                    for sub in os.listdir(pasta_completa):
                        sub_path = os.path.join(pasta_completa, sub)
                        if os.path.isdir(sub_path):
                            for arquivo in os.listdir(sub_path):
                                if arquivo.lower().endswith(extensoes):
                                    caminho_exe = os.path.join(sub_path, arquivo)
                                    nome_exe = arquivo.lower().replace(".exe", "").replace(" ", "").replace("-", "")
                                    if nome_busca in nome_exe or nome_exe.startswith(nome_busca[:4]):
                                        return caminho_exe
                    # 4) Qualquer .exe em subpastas
                    for sub in os.listdir(pasta_completa):
                        sub_path = os.path.join(pasta_completa, sub)
                        if os.path.isdir(sub_path):
                            for arquivo in os.listdir(sub_path):
                                if arquivo.lower().endswith(extensoes):
                                    return os.path.join(sub_path, arquivo)
        except Exception:
            continue
    return None


def _prefixos_palavra(nome_limpo: str, min_len: int = 3):
    """Gera prefixos de palavras do nome para correspondencia parcial por prefixo."""
    partes = re.split(r'[\s\-_]+', nome_limpo)
    prefixos = set()
    for parte in partes:
        for i in range(min_len, len(parte) + 1):
            prefixos.add(parte[:i])
    return prefixos


def _resolver_app_paths(nome: str):
    """Resolve um nome de programa pelos App Paths do Windows (registro)."""
    if SYSTEM != "Windows" or not nome:
        return None
    try:
        import winreg
        keys = [r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths",
                r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\App Paths"]
        alvo = nome if nome.lower().endswith(".exe") else nome + ".exe"
        for k in keys:
            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, k + "\\" + alvo) as ch:
                    r = winreg.QueryValueEx(ch, None)[0]
                    caminho = r.split(",")[0].strip('"')
                    if os.path.isfile(caminho):
                        return caminho
            except Exception:
                continue
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, k + "\\" + alvo) as ch:
                    r = winreg.QueryValueEx(ch, None)[0]
                    caminho = r.split(",")[0].strip('"')
                    if os.path.isfile(caminho):
                        return caminho
            except Exception:
                continue
    except Exception:
        pass
    return None


def _buscar_programa_windows(nome: str):
    """Procura um programa instalado no Windows pelo Menu Iniciar, Area de Trabalho e registro."""
    if SYSTEM != "Windows":
        return None
    nome = nome.lower().strip()
    nome_limpo = nome.replace(" ", "").replace("-", "").replace("_", "")

    candidatos_exe = set()
    diretorios_atalhos = [
        os.path.join(os.environ.get("APPDATA", ""), "Microsoft", "Windows", "Start Menu", "Programs"),
        os.path.join(os.environ.get("PROGRAMDATA", "C:\\ProgramData"), "Microsoft", "Windows", "Start Menu", "Programs"),
        os.path.join(os.path.expanduser("~"), "Desktop"),
        os.path.join(os.environ.get("PUBLIC", "C:\\Users\\Public"), "Desktop"),
    ]

    for pasta in diretorios_atalhos:
        if not os.path.isdir(pasta):
            continue
        for raiz, _, arquivos in os.walk(pasta):
            for arq in arquivos:
                if not arq.lower().endswith((".lnk", ".url")):
                    continue
                base = os.path.splitext(arq)[0].lower()
                base_limpo = base.replace(" ", "").replace("-", "").replace("_", "")
                # Correspondencia estrita: nome contido, contem o nome, ou prefixo de palavra >= 3 letras
                nomes_nome = set(base.split()) | set(base_limpo.split())
                achou_nome = (nome in base or nome_limpo in base_limpo
                              or base_limpo in nome_limpo
                              or any(base_limpo.startswith(p) for p in _prefixos_palavra(nome_limpo)))
                if not achou_nome:
                    continue
                atalho = os.path.join(raiz, arq)
                caminho_exe = _resolver_atalho(atalho)
                if caminho_exe and os.path.isfile(caminho_exe) and caminho_exe.lower().endswith(".exe"):
                    nome_exe = os.path.basename(caminho_exe).lower().replace(" ", "").replace("-", "").replace(".exe", "").replace("_", "")
                    if nome_limpo in nome_exe:
                        return caminho_exe
                    candidatos_exe.add(caminho_exe)

    # Fallback: registro Uninstall do Windows (local e do usuario)
    import winreg
    chaves_reg = [
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
        r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
    ]
    for hkey in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
        for sub in chaves_reg:
            try:
                with winreg.OpenKey(hkey, sub) as chave:
                    for i in range(0, winreg.QueryInfoKey(chave)[0]):
                        try:
                            with winreg.OpenKey(chave, winreg.EnumKey(chave, i)) as sub_chave:
                                try:
                                    exe = winreg.QueryValueEx(sub_chave, "DisplayIcon")[0]
                                except Exception:
                                    exe = ""
                                if not exe:
                                    continue
                                caminho = exe.strip().strip('"')
                                if caminho.startswith("{"):
                                    continue
                                caminho = caminho.split(",")[0]
                                if not caminho.lower().endswith(".exe") or not os.path.isfile(caminho):
                                    continue
                                nome_exe = os.path.basename(caminho).lower().replace(" ", "").replace("-", "").replace(".exe", "").replace("_", "")
                                if nome_limpo in nome_exe:
                                    return caminho
                        except Exception:
                            continue
            except Exception:
                continue

    if candidatos_exe:
        return sorted(candidatos_exe)[0]
    return None


def _resolver_atalho(atalho: str):
    """Extrai o caminho alvo de um atalho .lnk (via WScript.Shell) ou URL (.url)."""
    try:
        if atalho.lower().endswith(".url"):
            with open(atalho, "r", encoding="utf-8", errors="ignore") as f:
                for linha in f:
                    if linha.strip().lower().startswith("url="):
                        return linha.split("=", 1)[1].strip()
            return None
        ps = ("$s=(New-Object -ComObject WScript.Shell).CreateShortcut('%s');Write-Output $s.TargetPath" % atalho)
        r = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True, timeout=8)
        if r.returncode == 0:
            alvo = r.stdout.strip()
            if os.path.isfile(alvo):
                return alvo
    except Exception:
        pass
    return None


def open_program(nome: str, monitor: int = None) -> str:
    """Abre um programa pelo nome, opcionalmente em um monitor especifico."""
    nome = nome.lower().strip()

    # Pastas comuns do Windows (atalhos)
    user = os.path.expanduser("~")
    pastas_comuns = {
        "downloads": os.path.join(user, "Downloads"),
        "download": os.path.join(user, "Downloads"),
        "documentos": os.path.join(user, "Documents"),
        "documento": os.path.join(user, "Documents"),
        "documentos recentes": os.path.join(user, "Documents"),
        "area de trabalho": os.path.join(user, "Desktop"),
        "desktop": os.path.join(user, "Desktop"),
        "imagens": os.path.join(user, "Pictures"),
        "imagem": os.path.join(user, "Pictures"),
        "videos": os.path.join(user, "Videos"),
        "video": os.path.join(user, "Videos"),
        "musicas": os.path.join(user, "Music"),
        "musica": os.path.join(user, "Music"),
        "music": os.path.join(user, "Music"),
        "pasta inicial": user,
        "home": user,
        "perfil": user,
        "appdata": os.path.join(user, "AppData"),
        "appdata local": os.path.join(user, "AppData", "Local"),
        "appdata roaming": os.path.join(user, "AppData", "Roaming"),
        " OneDrive": os.path.join(user, "OneDrive"),
        "onedrive": os.path.join(user, "OneDrive"),
        "documentos do usuario": user,
        "meus documentos": os.path.join(user, "Documents"),
        "minhas imagens": os.path.join(user, "Pictures"),
        "meus videos": os.path.join(user, "Videos"),
        "minhas musicas": os.path.join(user, "Music"),
    }

    if nome in pastas_comuns:
        caminho = pastas_comuns[nome]
        if os.path.isdir(caminho):
            try:
                subprocess.Popen(f'start "" "{caminho}"', shell=True)
                return random.choice(_ABRIR_VARIAÇÕES).format(nome=nome)
            except Exception as e:
                return f"Peço desculpas Senhor, mas nao consegui abrir a pasta {nome}. Erro: {e}"

    # Mapeamento de nomes para janelas (titulo da janela)
    nomes_janela = {
        "discord": "Discord",
        "spotify": "Spotify",
        "steam": "Steam",
        "minecraft": "Minecraft",
        "vs code": "Visual Studio Code",
        "code": "Visual Studio Code",
        "chrome": "Chrome",
        "firefox": "Firefox",
        "edge": "Edge",
        "word": "Word",
        "excel": "Excel",
        "powerpoint": "PowerPoint",
        "notepad": "Bloco de Notas",
        "explorer": "Explorador de Arquivos",
        "opera": "Opera",
        "whatsapp": "WhatsApp",
    }

    # Programas que estao no PATH do Windows (start resolve direto)
    apps_path = {
        "navegador": "chrome",
        "chrome": "chrome",
        "firefox": "firefox",
        "edge": "msedge",
        "opera": "opera",
        "explorador": "explorer",
        "gerenciador": "explorer",
        "bloc de notas": "notepad",
        "notepad": "notepad",
        "calculadora": "calc",
        "terminal": "cmd",
        "cmd": "cmd",
        "powershell": "powershell",
        "vs code": "code",
        "code": "code",
        "word": "winword",
        "excel": "excel",
        "powerpoint": "powerpnt",
    }

    # Programas que precisam de caminho completo (nao estao no PATH)
    apps_caminho = {
        "discord": [
            "~/AppData/Local/Discord/Update.exe --processStart Discord.exe",
            "~/AppData/Local/Discord/app-*/Discord.exe",
            "C:/Program Files/Discord/Discord.exe",
        ],
        "spotify": [
            "~/AppData/Local/Spotify/Spotify.exe",
            "C:/Users/*/AppData/Local/Spotify/Spotify.exe",
        ],
        "steam": [
            "C:/Program Files (x86)/Steam/steam.exe",
            "C:/Program Files/Steam/steam.exe",
        ],
        "minecraft": [
            "~/AppData/Local/Programs/Minecraft Launcher/MinecraftLauncher.exe",
            "C:/Program Files (x86)/Minecraft Launcher/MinecraftLauncher.exe",
            "C:/Program Files/Minecraft Launcher/MinecraftLauncher.exe",
        ],
        "java": [
            "C:/Program Files/Java/*/bin/javaw.exe",
        ],
        "opera": [
            "~/AppData/Local/Programs/Opera/launcher.exe",
            "C:/Program Files/Opera/launcher.exe",
            "C:/Program Files (x86)/Opera/launcher.exe",
        ],
        "whatsapp": [
            "~/AppData/Local/WhatsApp/WhatsApp.exe",
            "C:/Program Files/WhatsApp/WhatsApp.exe",
            "C:/Program Files (x86)/WhatsApp/WhatsApp.exe",
        ],
    }

    # Funcao auxiliar para abrir e mover
    def _abrir_e_mover(caminho=None):
        nonlocal nome
        # Tenta fechar janela existente se for mover para monitor especifico
        if monitor and SYSTEM == "Windows":
            titulo = nomes_janela.get(nome, nome)
            hwnd = _obter_janela_recente(titulo)
            if hwnd:
                _mover_janela_para(hwnd, monitor)
                monitores = _listar_monitores()
                m = monitores[monitor - 1] if monitor <= len(monitores) else None
                return random.choice(_ABRIR_VARIAÇÕES).format(nome=nome) + (f" no monitor {monitor}." if m else ".")

        # Abre o programa (sem travar / sem janela extra)
        try:
            if caminho:
                if os.path.isfile(caminho):
                    subprocess.Popen([caminho], creationflags=subprocess.CREATE_NO_WINDOW)
                else:
                    subprocess.Popen(["cmd", "/c", "start", "", caminho], creationflags=subprocess.CREATE_NO_WINDOW)
            else:
                if SYSTEM == "Windows":
                    alvo = apps_path.get(nome, nome)
                    if nome not in apps_path:
                        # Nome desconhecido: confirma que existe antes de abrir (evita 'abri' falso)
                        exe_existente = shutil.which(alvo) or shutil.which(_resolver_app_paths(alvo))
                        if not exe_existente:
                            return f"Nao consegui encontrar '{nome}' neste computador."
                    # 'start' resolve App Paths do Windows e retorna imediatamente (nao trava)
                    subprocess.Popen(["cmd", "/c", "start", "", alvo], creationflags=subprocess.CREATE_NO_WINDOW)
                elif SYSTEM == "Darwin":
                    subprocess.Popen(["open", "-a", nome])
                else:
                    subprocess.Popen([nome])
        except Exception as e:
            return f"Peço desculpas Senhor, mas nao consegui abrir {nome}. Erro: {e}"

        # Se pediu monitor especifico, move a janela
        if monitor and SYSTEM == "Windows":
            titulo = nomes_janela.get(nome, nome)
            time.sleep(1.5)
            resultado = _mover_para_monitor(titulo, monitor)
            if resultado:
                return random.choice(_ABRIR_VARIAÇÕES).format(nome=nome) + f" no monitor {monitor}."

        return random.choice(_ABRIR_VARIAÇÕES).format(nome=nome)

    # Tenta pelo PATH primeiro
    if nome in apps_path:
        return _abrir_e_mover()

    # Tenta varios caminhos
    if nome in apps_caminho:
        import glob as _glob
        user = os.path.expanduser("~")
        for caminho in apps_caminho[nome]:
            caminho_real = caminho.replace("~", user)
            try:
                encontrados = _glob.glob(caminho_real)
                if encontrados:
                    return _abrir_e_mover(encontrados[0])
                if os.path.isfile(caminho_real):
                    return _abrir_e_mover(caminho_real)
            except:
                continue
        # Fallback: tenta como se estivesse no PATH
        return _abrir_e_mover()

    # Qualquer outro programa: tenta direto
    resultado = _abrir_e_mover()

    # Se deu certo (nao e erro), retorna
    if "Nao consegui" not in resultado and "desculpas" not in resultado.lower():
        return resultado

    # Busca automatica pelo programa instalado (Menu Iniciar / area de trabalho / registro)
    caminho_encontrado = _buscar_programa_windows(nome)
    if caminho_encontrado:
        try:
            subprocess.Popen(f'start "" "{caminho_encontrado}"', shell=True)
            return f"Achei {nome} instalado neste computador e o abri, Senhor. (" + caminho_encontrado + ")"
        except Exception as e:
            return f"Peço desculpas Senhor, mas nao consegui abrir {nome}. Erro: {e}"

    # Procura na pasta do Steam (abaixo: _abrir_e_mover ja esta definido)
    resultado_steam = _procurar_jogo_steam(nome)
    if resultado_steam:
        return _abrir_e_mover(resultado_steam)

    # Programa nao encontrado - da sugestoes
    programas_conhecidos = list(apps_path.keys()) + list(apps_caminho.keys())
    # Procura por nomes parecidos
    sugestoes = []
    for p in programas_conhecidos:
        if nome in p or p in nome:
            sugestoes.append(p)
        elif len(nome) >= 3 and (p.startswith(nome[:3]) or nome.startswith(p[:3])):
            sugestoes.append(p)

    if sugestoes:
        lista = ", ".join(sugestoes[:5])
        return (f"Peço desculpas Senhor, mas nao encontrei '{nome}' no sistema. "
                f"Talvez o Senhor quis dizer: {lista}? "
                f"Ou o programa pode nao estar instalado neste computador.")
    else:
        return (f"Peço desculpas Senhor, mas nao encontrei '{nome}' no sistema. "
                f"Verifique se o nome esta correto e se o programa esta instalado. "
                f"Caso queira, posso pesquisar na internet por Download de {nome}.")


def close_program(nome: str) -> str:
    """Fecha um programa pelo nome."""
    nome = nome.lower().strip()
    fechou = False

    # Mapeamento de nomes para processos
    nomes_processo = {
        "opera": ["opera", "opera.exe", "opera browser"],
        "chrome": ["chrome", "chrome.exe"],
        "firefox": ["firefox", "firefox.exe"],
        "edge": ["msedge", "msedge.exe"],
        "discord": ["discord", "discord.exe"],
        "spotify": ["spotify", "spotify.exe"],
        "steam": ["steam", "steam.exe"],
        "vs code": ["code", "code.exe"],
        "code": ["code", "code.exe"],
    }

    nomes_para_buscar = nomes_processo.get(nome, [nome])

    for proc in psutil.process_iter(["name"]):
        try:
            pname = proc.info["name"].lower().replace(".exe", "")
            for n in nomes_para_buscar:
                if n in pname or pname in n:
                    proc.terminate()
                    fechou = True
                    break
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    if fechou:
        return random.choice(_FECHAR_VARIAÇÕES).format(nome=nome)
    return f"Senhor, nao encontrei {nome} em execucao."


def _barra(porcentagem, tamanho=15):
    """Gera uma barra de progresso visual."""
    cheio = int(porcentagem / 100 * tamanho)
    vazia = tamanho - cheio
    if porcentagem < 50:
        cor = "\033[92m"
    elif porcentagem < 80:
        cor = "\033[93m"
    else:
        cor = "\033[91m"
    reset = "\033[0m"
    return f"{cor}[{'#' * cheio}{'-' * vazia}]{reset} {porcentagem:.0f}%"


_temp_cache = {"valor": None, "tempo": 0}


def _pegar_temperatura():
    """Tenta obter a temperatura do CPU com cache de 30s."""
    import time
    agora = time.time()
    if _temp_cache["valor"] is not None and (agora - _temp_cache["tempo"]) < 30:
        return _temp_cache["valor"]

    resultado = _pegar_temperatura_raw()
    _temp_cache["valor"] = resultado
    _temp_cache["tempo"] = agora
    return resultado


def _pegar_temperatura_raw():
    """Busca temperatura sem cache."""
    if SYSTEM != "Windows":
        try:
            temps = psutil.sensors_temperatures()
            if temps:
                for entries in temps.values():
                    if entries:
                        return f"{entries[0].current} C"
        except Exception:
            pass
        return None

    metodos = [
        'Get-CimInstance MSAcpi_ThermalZoneTemperature -Namespace "root/wmi" -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty CurrentTemperature',
        'Get-WmiObject MSAcpi_ThermalZoneTemperature -Namespace "root/wmi" -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty CurrentTemperature',
        'Get-CimInstance -Namespace "root/OpenHardwareMonitor" -ClassName Sensor -ErrorAction SilentlyContinue | Where-Object {$_.SensorType -eq "Temperature"} | Select-Object -First 1 -ExpandProperty Value',
    ]
    for cmd in metodos:
        try:
            resultado = subprocess.run(
                ["powershell", "-NoProfile", "-Command", cmd],
                capture_output=True, text=True, timeout=8, creationflags=subprocess.CREATE_NO_WINDOW
            )
            if resultado.returncode == 0 and resultado.stdout.strip():
                temp_raw = float(resultado.stdout.strip())
                if temp_raw > 200:
                    temp_c = (temp_raw / 10) - 273.15
                else:
                    temp_c = temp_raw
                if 0 < temp_c < 150:
                    return f"{temp_c:.0f} C"
        except Exception:
            continue
    return None


def _coletar_dados_pc():
    """Coleta todos os dados do PC uma unica vez."""
    cpu = psutil.cpu_percent(interval=None)
    ram = psutil.virtual_memory()
    disco = psutil.disk_usage("C:\\" if SYSTEM == "Windows" else "/")
    temp = _pegar_temperatura()
    bateria = None
    try:
        bat = psutil.sensors_battery()
        if bat:
            bateria = {"percent": bat.percent, "carregando": bat.power_plugged}
    except Exception:
        pass
    nucleos = psutil.cpu_count(logical=True)
    freq = psutil.cpu_freq()
    return {
        "cpu": cpu, "ram": ram, "disco": disco, "temp": temp,
        "bateria": bateria, "nucleos": nucleos, "freq": freq,
    }


def open_folder(caminho: str) -> str:
    """Abre uma pasta pelo caminho."""
    from file_manager import _resolver_caminho, PASTAS_COMUNS
    
    # Tenta resolver o caminho diretamente
    caminho_resolvido = _resolver_caminho(caminho)
    if os.path.isdir(caminho_resolvido):
        try:
            subprocess.Popen(f'start "" "{caminho_resolvido}"', shell=True)
            nome_pasta = os.path.basename(caminho_resolvido) or caminho_resolvido
            return f"Abrindo a pasta {nome_pasta}, Senhor."
        except Exception as e:
            return f"Peço desculpas Senhor, mas nao consegui abrir a pasta: {e}"
    
    # Se nao encontrou, procura em locais comuns
    user = os.path.expanduser("~")
    locais_comuns = [
        os.path.join(user, "Desktop"),
        os.path.join(user, "Documents"),
        os.path.join(user, "Downloads"),
        os.path.join(user, "Pictures"),
        os.path.join(user, "Videos"),
        os.path.join(user, "Music"),
    ]
    
    for local in locais_comuns:
        pasta_teste = os.path.join(local, caminho)
        if os.path.isdir(pasta_teste):
            try:
                subprocess.Popen(f'start "" "{pasta_teste}"', shell=True)
                return f"Abrindo a pasta {caminho}, Senhor."
            except Exception as e:
                return f"Peço desculpas Senhor, mas nao consegui abrir a pasta: {e}"
    
    # Ultima tentativa: procura em todo o sistema
    try:
        for root, dirs, files in os.walk(user):
            if caminho.lower() in [d.lower() for d in dirs]:
                pasta_encontrada = os.path.join(root, caminho)
                try:
                    subprocess.Popen(f'start "" "{pasta_encontrada}"', shell=True)
                    return f"Abrindo a pasta {caminho}, Senhor."
                except Exception as e:
                    return f"Peço desculpas Senhor, mas nao consegui abrir a pasta: {e}"
            # Limita a busca para nao demorar muito
            if root.count(os.sep) - user.count(os.sep) > 3:
                break
    except Exception:
        pass
    
    return f"Peço desculpas Senhor, mas nao encontrei a pasta: {caminho}"


def open_file(caminho: str) -> str:
    """Abre um arquivo pelo caminho."""
    # Tenta resolver o caminho diretamente
    caminho_resolvido = os.path.expanduser(caminho)
    if os.path.isfile(caminho_resolvido):
        try:
            subprocess.Popen(f'start "" "{caminho_resolvido}"', shell=True)
            return f"Abrindo o arquivo, Senhor: {os.path.basename(caminho_resolvido)}"
        except Exception as e:
            return f"Peço desculpas Senhor, mas nao consegui abrir o arquivo: {e}"
    
    # Se nao encontrou, procura em locais comuns
    user = os.path.expanduser("~")
    locais_comuns = [
        os.path.join(user, "Desktop"),
        os.path.join(user, "Documents"),
        os.path.join(user, "Downloads"),
        os.path.join(user, "Pictures"),
        os.path.join(user, "Videos"),
    ]
    
    for local in locais_comuns:
        arquivo_teste = os.path.join(local, caminho)
        if os.path.isfile(arquivo_teste):
            try:
                subprocess.Popen(f'start "" "{arquivo_teste}"', shell=True)
                return f"Abrindo o arquivo, Senhor: {os.path.basename(arquivo_teste)}"
            except Exception as e:
                return f"Peço desculpas Senhor, mas nao consegui abrir o arquivo: {e}"
    
    return f"Peço desculpas Senhor, mas nao encontrei o arquivo: {caminho}"


def desligar_computador() -> str:
    """Desliga o computador."""
    subprocess.run(["shutdown", "/s", "/t", "10"], creationflags=subprocess.CREATE_NO_WINDOW)
    return "Desligando o computador em 10 segundos, Senhor. Adeus."


def reiniciar_computador() -> str:
    """Reinicia o computador."""
    subprocess.run(["shutdown", "/r", "/t", "10"], creationflags=subprocess.CREATE_NO_WINDOW)
    return "Reiniciando o computador em 10 segundos, Senhor."


def suspender_computador() -> str:
    """Coloca o computador em modo suspensao."""
    subprocess.run(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"], creationflags=subprocess.CREATE_NO_WINDOW)
    return "Colocando o computador em modo suspensao, Senhor."


def monitor_pc() -> str:
    """Retorna informacoes do PC formatadas."""
    d = _coletar_dados_pc()

    temp_str = d["temp"] if d["temp"] else "Nao disponivel"
    bateria_str = "Nao disponivel"
    if d["bateria"]:
        bateria_str = f"{d['bateria']['percent']}% ({'Carregando' if d['bateria']['carregando'] else 'Bateria'})"
    freq_str = f"{d['freq'].current:.0f} MHz" if d["freq"] else "N/A"

    return (
        f"+--------------------------------------+\n"
        f"|      RELATORIO DO PC, SENHOR         |\n"
        f"+--------------------------------------+\n"
        f"|  CPU:   {_barra(d['cpu'])}\n"
        f"|         Nucleos: {d['nucleos']} | Freq: {freq_str}\n"
        f"|                                       \n"
        f"|  RAM:   {_barra(d['ram'].percent)}\n"
        f"|         {d['ram'].used // (1024**3)}GB / {d['ram'].total // (1024**3)}GB\n"
        f"|                                       \n"
        f"|  DISCO: {_barra(d['disco'].percent)}\n"
        f"|         {d['disco'].used // (1024**3)}GB / {d['disco'].total // (1024**3)}GB\n"
        f"|                                       \n"
        f"|  TEMP:  {temp_str}\n"
        f"|  BATERIA: {bateria_str}\n"
        f"+--------------------------------------+"
    )


def monitor_pc_fala() -> str:
    """Retorna resumo falado do PC."""
    d = _coletar_dados_pc()

    partes = [
        f"CPU em {d['cpu']:.0f} por cento",
        f"RAM em {d['ram'].percent:.0f} por cento, {d['ram'].used // (1024**3)} de {d['ram'].total // (1024**3)} gigabytes",
        f"Disco em {d['disco'].percent:.0f} por cento",
    ]

    if d["temp"]:
        partes.append(f"Temperatura {d['temp']}")

    if d["bateria"]:
        status = "carregando" if d["bateria"]["carregando"] else "na bateria"
        partes.append(f"Bateria {d['bateria']['percent']} por cento, {status}")

    return ", ".join(partes) + "."


_procs_cache = {"lista": None, "tempo": 0}


def _listar_processos():
    """Lista processos com cache de 2s."""
    import time
    agora = time.time()
    if _procs_cache["lista"] is not None and (agora - _procs_cache["tempo"]) < 2:
        return _procs_cache["lista"]

    procs = set()
    for proc in psutil.process_iter(["name"]):
        try:
            name = proc.info["name"]
            if name and not name.startswith("svchost") and not name.startswith("System"):
                procs.add(name)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    lista = sorted(procs)
    _procs_cache["lista"] = lista
    _procs_cache["tempo"] = agora
    return lista


def list_running() -> str:
    """Lista programas em execucao."""
    lista = _listar_processos()[:20]
    return (
        f"+--------------------------------------+\n"
        f"|      PROGRAMAS ABERTOS, SENHOR       |\n"
        f"+--------------------------------------+\n"
        f"|  Total: {len(lista)} programas\n"
        f"|                                       \n"
        + "\n".join(f"|  - {p}" for p in lista) +
        f"\n+--------------------------------------+"
    )


def list_running_fala() -> str:
    """Retorna resumo falado dos programas abertos."""
    lista = _listar_processos()[:10]
    total = len(lista)

    if total == 0:
        return "Nenhum programa aberto, Senhor."

    principais = []
    nomes_populares = {
        "chrome": "Chrome", "firefox": "Firefox", "msedge": "Edge",
        "discord": "Discord", "spotify": "Spotify", "steam": "Steam",
        "code": "VS Code", "explorer": "Explorador", "notepad": "Bloco de Notas",
        "word": "Word", "excel": "Excel", "powerpnt": "PowerPoint",
        "OBS": "OBS", "vlc": "VLC", "7zip": "7-Zip",
    }

    for p in lista:
        nome_base = p.lower().replace(".exe", "")
        if nome_base in nomes_populares:
            principais.append(nomes_populares[nome_base])
        elif len(nome_base) > 2:
            principais.append(nome_base.capitalize())

    if principais:
        texto = f"Tenho {total} programas abertos. Os principais sao: {', '.join(principais[:6])}"
    else:
        texto = f"Tenho {total} programas abertos"

    return texto + "."
