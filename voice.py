import speech_recognition as sr
import pyttsx3
import edge_tts
import asyncio
import threading
import tempfile
import os
import pygame
import time
import json
import struct

_engine = None
_lock = threading.Lock()
_recognizer = sr.Recognizer()
_mic_calibrada = False
_mixer_ready = False
VELOCIDADE = 1.0
_ouvindo = False
_parar_fala = threading.Event()
_vosk_model = None
_vosk_model_path = None

VOZES = {
    "Antonio": "pt-BR-AntonioNeural",
    "Francisca": "pt-BR-FranciscaNeural",
    "Thalita": "pt-BR-ThalitaMultilingualNeural",
    "Valerio": "pt-PT-DuarteNeural",
    "Giovanna": "pt-PT-RaquelNeural",
}

VOZ_PADRAO = "pt-BR-AntonioNeural"

VOSK_MODELS = {
    "pt": "vosk-model-small-pt-0.3",
    "en": "vosk-model-small-en-us-0.15",
}

VOSK_MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models", "vosk")


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
    global _mic_calibrada
    if _mic_calibrada:
        return
    try:
        with sr.Microphone(sample_rate=16000) as source:
            _recognizer.adjust_for_ambient_noise(source, duration=0.5)
        _mic_calibrada = True
    except Exception:
        pass


def _carregar_vosk_model(modelo_idioma="pt"):
    """Carrega o modelo Vosk."""
    global _vosk_model, _vosk_model_path
    if _vosk_model is not None:
        return _vosk_model

    try:
        from vosk import Model, KaldiRecognizer
    except ImportError:
        print("[Vosk] Pacote vosk nao instalado. Use: pip install vosk")
        return None

    model_name = VOSK_MODELS.get(modelo_idioma, VOSK_MODELS["pt"])
    model_path = os.path.join(VOSK_MODEL_DIR, model_name)

    if not os.path.exists(model_path):
        print(f"[Vosk] Modelo nao encontrado em: {model_path}")
        print(f"[Vosk] Baixe em: https://alphacephei.com/vosk/models")
        print(f"[Vosk] Extraia para: {VOSK_MODEL_DIR}")
        return None

    try:
        _vosk_model = Model(model_path)
        _vosk_model_path = model_path
        print(f"[Vosk] Modelo carregado: {model_name}")
        return _vosk_model
    except Exception as e:
        print(f"[Vosk] Erro ao carregar modelo: {e}")
        return None


def listen_vosk(timeout=5, phrase_limit=10, modelo_idioma="pt"):
    """Escuta usando Vosk (offline)."""
    model = _carregar_vosk_model(modelo_idioma)
    if model is None:
        return listen(timeout, phrase_limit)

    try:
        from vosk import KaldiRecognizer
        import sounddevice as sd
        import queue

        q = queue.Queue()

        def callback(indata, frames, time_info, status):
            q.put(bytes(indata))

        with sd.RawInputStream(samplerate=16000, blocksize=8000, dtype="int16",
                               channels=1, callback=callback):
            rec = KaldiRecognizer(model, 16000)
            start_time = time.time()

            while True:
                if time.time() - start_time > timeout:
                    break
                data = q.get()
                if rec.AcceptWaveform(data):
                    result = json.loads(rec.Result())
                    texto = result.get("text", "").strip()
                    if texto:
                        return texto

            final = json.loads(rec.FinalResult())
            return final.get("text", "").strip() or None

    except Exception as e:
        print(f"[Vosk] Erro: {e}")
        return None


def listen(timeout=5, phrase_limit=10) -> str | None:
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
    def __init__(self, callback, palavra_ativacao="jarvis", motor="google"):
        self.callback = callback
        self.palavra_ativacao = palavra_ativacao.lower()
        self.ativo = False
        self._thread = None
        self._reconhecedor = sr.Recognizer()
        self._reconhecedor.energy_threshold = 300
        self._reconhecedor.dynamic_energy_threshold = True
        self._reconhecedor.pause_threshold = 0.8
        self._reconhecedor.phrase_threshold = 0.3
        self.motor = motor

    def iniciar(self):
        if self.ativo:
            return
        self.ativo = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def parar(self):
        self.ativo = False

    def _ouvir_vosk(self, source, timeout=5):
        """Escuta com Vosk usando o microfone do speech_recognition."""
        model = _carregar_vosk_model()
        if model is None:
            return None

        try:
            from vosk import KaldiRecognizer
            import queue

            q = queue.Queue()

            def callback(indata, frames, time_info, status):
                q.put(bytes(indata))

            with sd.RawInputStream(samplerate=16000, blocksize=8000, dtype="int16",
                                   channels=1, callback=callback):
                rec = KaldiRecognizer(model, 16000)
                start_time = time.time()

                while True:
                    if time.time() - start_time > timeout:
                        break
                    data = q.get()
                    if rec.AcceptWaveform(data):
                        result = json.loads(rec.Result())
                        texto = result.get("text", "").strip()
                        if texto:
                            return texto

                final = json.loads(rec.FinalResult())
                return final.get("text", "").strip() or None
        except Exception:
            return None

    def _reconhecer(self, audio):
        """Reconhece audio usando o motor selecionado."""
        if self.motor == "vosk":
            model = _carregar_vosk_model()
            if model:
                try:
                    from vosk import KaldiRecognizer

                    wav_data = audio.get_wav_data(rate=16000, width=2, channels=1)

                    pcm_data = wav_data[44:]

                    rec = KaldiRecognizer(model, 16000)

                    chunk_size = 4000
                    for i in range(0, len(pcm_data), chunk_size):
                        chunk = pcm_data[i:i+chunk_size]
                        rec.AcceptWaveform(chunk)

                    result = json.loads(rec.FinalResult())
                    texto = result.get("text", "").strip()
                    return texto.lower() if texto else None
                except Exception as e:
                    print(f"[Vosk] Erro reconhecimento: {e}")
                    return None

        try:
            return self._reconhecedor.recognize_google(audio, language="pt-BR").lower()
        except (sr.UnknownValueError, sr.RequestError):
            return None

    def _loop(self):
        global _ouvindo
        print(f"[Escuta Dinamica] Motor: {self.motor.upper()}")
        print(f"[Escuta Dinamica] Pronta. Diga '{self.palavra_ativacao}'...")

        while self.ativo:
            try:
                with sr.Microphone(sample_rate=16000) as source:
                    self._reconhecedor.adjust_for_ambient_noise(source, duration=0.5)
                    print(f"[Escuta Dinamica] Noise calibrado. Aguardando...")

                    while self.ativo:
                        try:
                            audio = self._reconhecedor.listen(source, timeout=1.5, phrase_time_limit=10)

                            texto = self._reconhecer(audio)
                            if texto:
                                print(f"[Escuta Dinamica] Ouvi: {texto}")
                            else:
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
                                    texto2 = self._reconhecer(audio2)
                                    if texto2:
                                        print(f"[Escuta Dinamica] Comando: {texto2}")
                                        threading.Thread(target=self.callback, args=(texto2,), daemon=True).start()
                                    else:
                                        print("[Escuta Dinamica] Nao entendi o comando.")
                                except Exception:
                                    print("[Escuta Dinamica] Nao entendi o comando.")
                            _ouvindo = False
                            print("[Escuta Dinamica] Aguardando...")

                        except sr.WaitTimeoutError:
                            continue
                        except Exception as e:
                            print(f"[Escuta Dinamica] Erro no loop: {e}")
                            time.sleep(0.1)
            except Exception as e:
                print(f"[Escuta Dinamica] Erro ao abrir microfone: {e}")
                time.sleep(1)


async def _edge_speak(texto: str, voz: str, velocidade: float = 1.0):
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
    linhas = []
    for nome, voz_id in VOZES.items():
        linhas.append(f"  - {nome}: {voz_id}")
    return "Vozes disponiveis:\n" + "\n".join(linhas)


def esta_ouvindo() -> bool:
    return _ouvindo
