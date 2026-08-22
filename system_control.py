import os
import platform
import subprocess
import psutil
import random
import time
import win32gui
import win32con

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


def open_program(nome: str, monitor: int = None) -> str:
    """Abre um programa pelo nome, opcionalmente em um monitor especifico."""
    nome = nome.lower().strip()

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

        # Abre o programa
        try:
            if caminho:
                subprocess.Popen(f'start "" "{caminho}"', shell=True)
            else:
                if SYSTEM == "Windows":
                    subprocess.Popen(f'start "" "{apps_path.get(nome, nome)}"', shell=True)
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
