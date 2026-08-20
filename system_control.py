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

    def callback(hwnd, _):
        if win32gui.IsWindowVisible(hwnd) and titulo_janela.lower() in win32gui.GetWindowText(hwnd).lower():
            try:
                win32gui.SetWindowPos(hwnd, None, alvo["x"] + 50, alvo["y"] + 50, 0, 0,
                                       win32con.SWP_NOSIZE | win32con.SWP_NOZORDER)
                return False
            except Exception:
                pass
        return True

    # Tenta encontrar a janela varias vezes (a janela pode demorar pra abrir)
    for _ in range(10):
        try:
            win32gui.EnumWindows(callback, None)
        except Exception:
            pass
        time.sleep(0.3)
    return True


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
    }

    # Programas que estao no PATH do Windows (start resolve direto)
    apps_path = {
        "navegador": "chrome",
        "chrome": "chrome",
        "firefox": "firefox",
        "edge": "msedge",
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
    return _abrir_e_mover()


def close_program(nome: str) -> str:
    """Fecha um programa pelo nome."""
    nome = nome.lower().strip()
    fechou = False

    for proc in psutil.process_iter(["name"]):
        try:
            pname = proc.info["name"].lower().replace(".exe", "")
            if nome in pname or pname in nome:
                proc.terminate()
                fechou = True
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


def _pegar_temperatura():
    """Tenta obter a temperatura do CPU."""
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
        # WMI via CIM
        'Get-CimInstance MSAcpi_ThermalZoneTemperature -Namespace "root/wmi" -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty CurrentTemperature',
        # WMI classico
        'Get-WmiObject MSAcpi_ThermalZoneTemperature -Namespace "root/wmi" -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty CurrentTemperature',
        # OpenHardwareMonitor (se instalado)
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
                # WMI retorna em decimos de Kelvin
                if temp_raw > 200:
                    temp_c = (temp_raw / 10) - 273.15
                else:
                    temp_c = temp_raw
                if 0 < temp_c < 150:
                    return f"{temp_c:.0f} C"
        except Exception:
            continue
    return None


def monitor_pc() -> str:
    """Retorna informacoes do PC formatadas."""
    cpu = psutil.cpu_percent(interval=1)
    ram = psutil.virtual_memory()
    disco = psutil.disk_usage("C:\\" if SYSTEM == "Windows" else "/")

    temp = _pegar_temperatura()
    temp_str = temp if temp else "Nao disponivel (instale OpenHardwareMonitor)"

    bateria = "Nao disponivel"
    try:
        bat = psutil.sensors_battery()
        if bat:
            bateria = f"{bat.percent}% ({'Carregando' if bat.power_plugged else 'Bateria'})"
    except Exception:
        pass

    nucleos = psutil.cpu_count(logical=True)
    freq = psutil.cpu_freq()
    freq_str = f"{freq.current:.0f} MHz" if freq else "N/A"

    return (
        f"+--------------------------------------+\n"
        f"|      RELATORIO DO PC, SENHOR         |\n"
        f"+--------------------------------------+\n"
        f"|  CPU:   {_barra(cpu)}\n"
        f"|         Nucleos: {nucleos} | Freq: {freq_str}\n"
        f"|                                       \n"
        f"|  RAM:   {_barra(ram.percent)}\n"
        f"|         {ram.used // (1024**3)}GB / {ram.total // (1024**3)}GB\n"
        f"|                                       \n"
        f"|  DISCO: {_barra(disco.percent)}\n"
        f"|         {disco.used // (1024**3)}GB / {disco.total // (1024**3)}GB\n"
        f"|                                       \n"
        f"|  TEMP:  {temp_str}\n"
        f"|  BATERIA: {bateria}\n"
        f"+--------------------------------------+"
    )


def list_running() -> str:
    """Lista programas em execucao."""
    procs = set()
    for proc in psutil.process_iter(["name"]):
        try:
            name = proc.info["name"]
            if name and not name.startswith("svchost") and not name.startswith("System"):
                procs.add(name)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    lista = sorted(procs)[:20]
    return f"Programas em execucao, Senhor ({len(lista)}): {', '.join(lista)}"
