import json
import os
import time
import threading
from datetime import datetime

REMINDERS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lembretes.json")
_reminders = []
_running = True


def _load():
    global _reminders
    try:
        with open(REMINDERS_FILE, "r", encoding="utf-8") as f:
            _reminders = json.load(f)
    except Exception:
        _reminders = []


def _save():
    try:
        with open(REMINDERS_FILE, "w", encoding="utf-8") as f:
            json.dump(_reminders, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def add_reminder(texto: str, minutos: int) -> str:
    """Agenda um lembrete."""
    horario = datetime.now().timestamp() + (minutos * 60)
    reminder = {
        "texto": texto,
        "horario": horario,
        "minutos": minutos,
        "criado": datetime.now().strftime("%d/%m/%Y %H:%M"),
    }
    _reminders.append(reminder)
    _save()
    return f"Entendido, Senhor. Lembrete agendado para daqui {minutos} minutos: {texto}"


def list_reminders() -> str:
    """Lista lembretes ativos."""
    if not _reminders:
        return "Senhor, nao ha lembretes ativos no momento."
    partes = []
    for i, r in enumerate(_reminders, 1):
        restante = r["horario"] - datetime.now().timestamp()
        if restante > 0:
            mins = int(restante // 60)
            partes.append(f"{i}. {r['texto']} (daqui {mins} min)")
    return "\n".join(partes) if partes else "Senhor, nao ha lembretes ativos."


def remove_reminder(index: int) -> str:
    """Remove um lembrete pelo indice."""
    if 0 <= index < len(_reminders):
        removido = _reminders.pop(index)
        _save()
        return f"Lembrete removido, Senhor: {removido['texto']}"
    return "Peço desculpas, Senhor, mas o indice informado e invalido."


def check_reminders(callback) -> None:
    """Verifica lembretes em background e chama callback quando vence."""
    _load()

    def _loop():
        while _running:
            agora = datetime.now().timestamp()
            for r in _reminders[:]:
                if r["horario"] <= agora:
                    callback(r["texto"])
                    _reminders.remove(r)
                    _save()
            time.sleep(10)

    t = threading.Thread(target=_loop, daemon=True)
    t.start()


def stop():
    global _running
    _running = False
