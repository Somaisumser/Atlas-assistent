import speech_recognition as sr
import pyttsx3
import edge_tts
import asyncio
import threading
import tempfile
import os
import pygame
import time

_engine = None
_lock = threading.Lock()
_recognizer = sr.Recognizer()
_mic_calibrada = False
_mixer_ready = False
VELOCIDADE = 1.0
_ouvindo = False
_parar_fala = threading.Event()

VOZES = {
    "Antonio": "pt-BR-AntonioNeural",
    "Francisca": "pt-BR-FranciscaNeural",
    "Thalita": "pt-BR-ThalitaMultilingualNeural",
    "Valerio": "pt-PT-DuarteNeural",
    "Giovanna": "pt-PT-RaquelNeural",
}

VOZ_PADRAO = "pt-BR-AntonioNeural"


def _get_engine():
    global _engine
    if _engine is None:
        _engine = pyttsx3.init()
        _engine.setProperty("rate", 160)
        _engine.setProperty("volume", 1.0)
        for voice in _engine.getProperty("voices"):
            if "brazil" in voice.name.lower() or "pt" in voice.id.lower():
                _engine.setProperty("voice", voice.id)
                break
    return _engine


def _calibrar_mic():
    """Calibra o microfone uma vez so."""
    global _mic_calibrada
    if _mic_calibrada:
        return
    try:
        with sr.Microphone(sample_rate=16000) as source:
            _recognizer.adjust_for_ambient_noise(source, duration=0.5)
        _mic_calibrada = True
    except Exception:
        pass


def listen(timeout=5, phrase_limit=10) -> str | None:
    """Escuta o microfone usando speech_recognition nativo."""
    _calibrar_mic()
    try:
        with sr.Microphone(sample_rate=16000) as source:
            audio = _recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_limit)
            return _recognizer.recognize_google(audio, language="pt-BR")
    except (sr.UnknownValueError, sr.RequestError, sr.WaitTimeoutError):
        return None
    except Exception:
        return None


class EscutaDinamica:
    """Escuta continua com deteccao de palavra de ativacao."""

    def __init__(self, callback, palavra_ativacao="jarvis"):
        self.callback = callback
        self.palavra_ativacao = palavra_ativacao.lower()
        self.ativo = False
        self._thread = None
        self._reconhecedor = sr.Recognizer()
        self._reconhecedor.energy_threshold = 300
        self._reconhecedor.dynamic_energy_threshold = True
        self._reconhecedor.pause_threshold = 0.8
        self._reconhecedor.phrase_threshold = 0.3

    def iniciar(self):
        if self.ativo:
            return
        self.ativo = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def parar(self):
        self.ativo = False

    def _loop(self):
        global _ouvindo
        print(f"[Escuta Dinamica] Pronta. Diga '{self.palavra_ativacao}'...")

        with sr.Microphone(sample_rate=16000) as source:
            self._reconhecedor.adjust_for_ambient_noise(source, duration=1)
            print(f"[Escuta Dinamica] Noise calibrado. Aguardando...")

            while self.ativo:
                try:
                    audio = self._reconhecedor.listen(source, timeout=1.5, phrase_time_limit=10)

                    try:
                        texto = self._reconhecedor.recognize_google(audio, language="pt-BR").lower()
                        print(f"[Escuta Dinamica] Ouvi: {texto}")
                    except sr.UnknownValueError:
                        continue
                    except sr.RequestError:
                        time.sleep(0.5)
                        continue

                    if self.palavra_ativacao not in texto:
                        continue

                    _ouvindo = True
                    comando = texto.split(self.palavra_ativacao, 1)
                    if len(comando) > 1 and comando[1].strip():
                        cmd = comando[1].strip()
                        print(f"[Escuta Dinamica] Comando: {cmd}")
                        threading.Thread(target=self.callback, args=(cmd,), daemon=True).start()
                    else:
                        print("[Escuta Dinamica] Diga seu comando...")
                        try:
                            audio2 = self._reconhecedor.listen(source, timeout=4, phrase_time_limit=10)
                            texto2 = self._reconhecedor.recognize_google(audio2, language="pt-BR").lower()
                            print(f"[Escuta Dinamica] Comando: {texto2}")
                            threading.Thread(target=self.callback, args=(texto2,), daemon=True).start()
                        except Exception:
                            print("[Escuta Dinamica] Nao entendi o comando.")
                    _ouvindo = False
                    print("[Escuta Dinamica] Aguardando...")

                except sr.WaitTimeoutError:
                    continue
                except Exception as e:
                    print(f"[Escuta Dinamica] Erro: {e}")
                    time.sleep(0.1)


async def _edge_speak(texto: str, voz: str, velocidade: float = 1.0):
    """Gera audio com edge-tts e toca com pygame."""
    global _mixer_ready

    rate = int((velocidade - 1.0) * 100)
    rate_str = f"+{rate}%" if rate >= 0 else f"{rate}%"

    communicate = edge_tts.Communicate(texto, voice=voz, rate=rate_str)

    fd, tmp_path = tempfile.mkstemp(suffix=".mp3")
    os.close(fd)

    try:
        await communicate.save(tmp_path)

        if not _mixer_ready:
            pygame.mixer.init()
            _mixer_ready = True

        pygame.mixer.music.load(tmp_path)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            if _parar_fala.is_set():
                pygame.mixer.music.stop()
                break
            pygame.time.wait(50)
        pygame.mixer.music.unload()
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass


def speak(texto: str, voz: str = "Antonio", velocidade: float = None):
    """Fala o texto em voz alta."""
    if not texto:
        return

    voz_id = VOZES.get(voz, VOZ_PADRAO)
    vel = velocidade if velocidade is not None else VELOCIDADE

    _parar_fala.clear()
    try:
        asyncio.run(_edge_speak(texto, voz_id, vel))
    except Exception:
        try:
            engine = _get_engine()
            engine.setProperty("rate", int(160 * vel))
            engine.say(texto)
            engine.runAndWait()
        except Exception:
            pass


def stop_speak():
    """Para a fala atual de forma segura."""
    _parar_fala.set()
    try:
        if _mixer_ready and pygame.mixer.get_init():
            pygame.mixer.music.stop()
    except Exception:
        pass
    try:
        engine = _get_engine()
        engine.stop()
    except Exception:
        pass


def listar_vozes() -> str:
    """Lista as vozes disponiveis."""
    linhas = []
    for nome, voz_id in VOZES.items():
        linhas.append(f"  - {nome}: {voz_id}")
    return "Vozes disponiveis:\n" + "\n".join(linhas)


def esta_ouvindo() -> bool:
    return _ouvindo
