import speech_recognition as sr
import pyttsx3
import edge_tts
import asyncio
import threading
import tempfile
import os
import pygame
import io
import wave
import base64
import requests

_engine = None
_lock = threading.Lock()
_recognizer = sr.Recognizer()
_mic_calibrada = False
_mixer_ready = False
VELOCIDADE = 1.15
_ouvindo = False
_parar_fala = threading.Event()
_motor_voz = "google"
_motor_tts = "edge"
_gemini_key = ""
_gemini_model = ""

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
    global _mic_calibrada
    if _mic_calibrada:
        return
    try:
        with sr.Microphone(sample_rate=16000) as source:
            _recognizer.adjust_for_ambient_noise(source, duration=1.5)
        _mic_calibrada = True
    except Exception:
        pass


def _audio_para_wav(audio: sr.AudioData) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(audio.sample_rate)
        wf.writeframes(audio.get_raw_data())
    return buf.getvalue()


def qualquer_signo_de_desculpa(tl: str) -> bool:
    return any(p in tl for p in (
        "desculpa", "peço", "peco", "lamenta", "infelizmente",
        "nao consegui", "não consegui", "erro", "falha", "impossivel",
    ))


def _reconhecer_google(audio: sr.AudioData) -> str | None:
    try:
        return _recognizer.recognize_google(audio, language="pt-BR")
    except (sr.UnknownValueError, sr.RequestError):
        return None


def _reconhecer_gemini(audio: sr.AudioData) -> str | None:
    if not _gemini_key:
        return _reconhecer_google(audio)
    try:
        from brain import transcrever_audio
        wav_data = _audio_para_wav(audio)
        audio_b64 = base64.b64encode(wav_data).decode("utf-8")
        texto = transcrever_audio(audio_b64, _gemini_key, _gemini_model)
        if texto and texto.strip():
            return texto.strip()
        return _reconhecer_google(audio)
    except Exception as e:
        print(f"[Gemini] Erro na transcricao: {e}")
        return _reconhecer_google(audio)


def _reconhecer_audio(audio: sr.AudioData) -> str | None:
    if _motor_voz == "gemini":
        return _reconhecer_gemini(audio)
    return _reconhecer_google(audio)


MOTORES_FALA = ("edge", "gemini")


def configurar_motor_voz(motor: str, gemini_key: str = "", gemini_model: str = "", motor_tts: str = "edge"):
    """Configura os motores de reconhecimento (motor) e de fala (motor_tts)."""
    global _motor_voz, _gemini_key, _gemini_model, _motor_tts
    _motor_voz = motor
    _gemini_key = gemini_key
    _gemini_model = gemini_model
    if motor_tts in MOTORES_FALA:
        _motor_tts = motor_tts


def listen(timeout=8, phrase_limit=15) -> str | None:
    _calibrar_mic()
    try:
        with sr.Microphone(sample_rate=16000) as source:
            audio = _recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_limit)
            return _reconhecer_audio(audio)
    except (sr.UnknownValueError, sr.RequestError, sr.WaitTimeoutError):
        return None
    except Exception:
        return None


class EscutaDinamica:
    def __init__(self, callback, palavra_ativacao="atlas"):
        self.callback = callback
        self.palavra_ativacao = palavra_ativacao.lower()
        self.ativo = False
        self._thread = None
        self._reconhecedor = sr.Recognizer()
        self._reconhecedor.energy_threshold = 300
        self._reconhecedor.dynamic_energy_threshold = True
        self._reconhecedor.pause_threshold = 1.2
        self._reconhecedor.phrase_threshold = 0.3
        self._reconhecedor.non_speaking_duration = 0.8

    def iniciar(self):
        if self.ativo:
            return
        self.ativo = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def parar(self):
        self.ativo = False

    def _reconhecer(self, audio):
        resultado = _reconhecer_audio(audio)
        return resultado.lower() if resultado else None

    def _loop(self):
        global _ouvindo
        motor_nome = "GEMINI" if _motor_voz == "gemini" else "GOOGLE"
        print(f"[Escuta Dinamica] Motor: {motor_nome}")
        print(f"[Escuta Dinamica] Pronta. Diga '{self.palavra_ativacao}'...")

        while self.ativo:
            try:
                with sr.Microphone(sample_rate=16000) as source:
                    self._reconhecedor.adjust_for_ambient_noise(source, duration=1.0)
                    print(f"[Escuta Dinamica] Noise calibrado. Aguardando...")

                    while self.ativo:
                        try:
                            audio = self._reconhecedor.listen(source, timeout=2.0, phrase_time_limit=15)

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
                                    audio2 = self._reconhecedor.listen(source, timeout=6, phrase_time_limit=15)
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
                            import time as _time
                            _time.sleep(0.3)

                        except sr.WaitTimeoutError:
                            continue
                        except Exception as e:
                            print(f"[Escuta Dinamica] Erro no loop: {e}")
                            import time as _time
                            _time.sleep(0.5)
            except Exception as e:
                print(f"[Escuta Dinamica] Erro ao abrir microfone: {e}")
                time.sleep(1)


async def _edge_speak(texto: str, voz: str, velocidade: float = 1.0):
    global _mixer_ready

    rate = int((velocidade - 1.0) * 100)
    rate_str = f"+{rate}%" if rate >= 0 else f"{rate}%"

    # Entonacao mais humana: ajusta pitch e volume conforme o tipo de fala
    pitch_base = 0
    volume_str = "+0%"
    tl = texto.lower()

    if "?" in texto or tl.startswith(("o que", "como", "quando", "onde", "quem", "por que", "pode")):
        pitch_base = 2
        volume_str = "+5%"
    elif "!" in texto or tl.startswith(("excelente", "otimo", "perfeito", "claro", "pronto", "senhor")):
        pitch_base = -2
        volume_str = "+8%"
    elif qualquer_signo_de_desculpa(tl):
        pitch_base = -4
        volume_str = "+0%"

    pitch_str = f"+{pitch_base}Hz" if pitch_base >= 0 else f"{pitch_base}Hz"

    communicate = edge_tts.Communicate(texto, voice=voz, rate=rate_str, volume=volume_str, pitch=pitch_str)

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


def _gemini_speak(texto: str, velocidade: float = 1.0):
    """Usa o TTS nativo do Gemini (voz de conversa natural) com streaming p/ reduzir lag."""
    global _mixer_ready
    if not _gemini_key:
        raise RuntimeError("sem chave Gemini")

    model = "gemini-2.5-flash-preview-tts"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:streamGenerateContent?alt=sse"

    # Coleta todos os chunks SSE de audio
    pcm_chunks = []
    resp = requests.post(
        url,
        headers={"x-goog-api-key": _gemini_key, "Content-Type": "application/json"},
        json={
            "contents": [{"parts": [{"text": f"Fale com naturalidade, como numa conversa humana: {texto}"}]}],
            "generationConfig": {
                "responseModalities": ["AUDIO"],
                "speechConfig": {
                    "voiceConfig": {
                        "prebuiltVoiceConfig": {"voiceName": "Kore"}
                    }
                },
            },
        },
        stream=True,
        timeout=150,
    )
    resp.raise_for_status()

    import json as _json
    for line in resp.iter_lines():
        if _parar_fala.is_set():
            resp.close()
            return
        if line and line.startswith(b"data:"):
            payload = line[5:].strip()
            if not payload:
                continue
            try:
                chunk = _json.loads(payload)
            except _json.JSONDecodeError:
                continue
            for part in chunk.get("candidates", [{}])[0].get("content", {}).get("parts", []):
                if "inlineData" in part and part["inlineData"].get("data"):
                    pcm_chunks.append(base64.b64decode(part["inlineData"]["data"]))

    if not pcm_chunks:
        raise RuntimeError("sem audio retornado pelo Gemini")

    raw = b"".join(pcm_chunks)

    # Gemini TTS retorna PCM signed 16-bit, 24000 Hz, mono -> empacotar em WAV
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(24000)
        wf.writeframes(raw)
    audio_bytes = buf.getvalue()

    fd, tmp_path = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    try:
        with open(tmp_path, "wb") as f:
            f.write(audio_bytes)

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

    # Motor de fala "gemini" = o mais humano (TTS nativo do Gemini), com fallback p/ Edge
    if _motor_tts == "gemini" and _gemini_key:
        try:
            _gemini_speak(texto, vel)
            return
        except Exception:
            # Gemini TTS falhou (503/latencia): usa Edge, que ainda e natural
            try:
                asyncio.run(_edge_speak(texto, voz_id, vel))
                return
            except Exception:
                pass
    else:
        # Motor padrao = Edge TTS (natural, sem depender de API)
        try:
            asyncio.run(_edge_speak(texto, voz_id, vel))
            return
        except Exception:
            pass

    # Ultimo recurso: voz local do Windows (pyttsx3)
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


def listar_motores_fala() -> str:
    return ("Motores de fala disponiveis:\n"
            "  - padrao: Edge TTS (natural, sem necessidade de API)\n"
            "  - humano: Gemini TTS (conversa humana, usa sua API key)")


def trocar_motor_fala(motor_tts: str) -> bool:
    """Troca o motor de fala em tempo de execucao. Retorna True se o valor foi valido."""
    global _motor_tts
    if motor_tts in MOTORES_FALA:
        _motor_tts = motor_tts
        return True
    return False


def motor_fala_atual() -> str:
    return _motor_tts


def esta_ouvindo() -> bool:
    return _ouvindo
