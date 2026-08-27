import customtkinter as ctk
from tkinter import colorchooser
import threading
import re
import os
import sys
import requests
import json

try:
    import pystray
    from PIL import Image, ImageDraw
    HAS_TRAY = True
except ImportError:
    HAS_TRAY = False


def _strip_ansi(texto):
    """Remove codigos ANSI de cores para exibicao na GUI."""
    return re.sub(r'\033\[[0-9;]*m', '', texto)

from brain import chat, ver_tela, criar_imagem, GEMINI_MODELS
from voice import listen, speak, stop_speak, VOZES, EscutaDinamica, configurar_motor_voz
from system_control import open_program, close_program, monitor_pc, monitor_pc_fala, list_running, list_running_fala, desligar_computador, reiniciar_computador, suspender_computador, open_folder, open_file
from file_manager import list_dir, read_file, create_file, delete_file
from web_search import search
from code_runner import run_code
from reminders import add_reminder, list_reminders, check_reminders
from developer import (
    listar_arquivos_codigo, aplicar_modificacao, salvar_arquivo,
    listar_backups, restaurar_backup, criar_backup
)

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

OLLAMA_HOST = "http://localhost:11434"


def obter_modelos_ollama():
    """Busca modelos instalados no Ollama com detalhes."""
    try:
        r = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=5)
        if r.status_code == 200:
            modelos = []
            for m in r.json().get("models", []):
                nome = m.get("name", "")
                tamanho = m.get("size", 0)
                tamanho_gb = round(tamanho / (1024**3), 1)
                detalhes = m.get("details", {})
                params = detalhes.get("parameter_size", "?")
                quant = detalhes.get("quantization_level", "?")
                familias = detalhes.get("family", "?")
                modelos.append({
                    "nome": nome,
                    "tamanho_gb": tamanho_gb,
                    "parametros": params,
                    "quantizacao": quant,
                    "familia": familias,
                    "display": f"{nome}  ({tamanho_gb}GB, {params}, {quant})"
                })
            return modelos
    except:
        pass
    return []

BG = "#0a0a1a"
PANEL = "#12122a"
ACCENT = "#00d4ff"
ACCENT_DIM = "#0090b0"
TEXT = "#e0e0f0"
MUTED = "#707090"
GREEN = "#00ff88"
RED = "#ff4444"
ORANGE = "#ffaa00"

BG_PADRAO = BG
PANEL_PADRAO = PANEL
ACCENT_PADRAO = ACCENT
TEXT_PADRAO = TEXT


class JarvisApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Jarvis - Assistente Pessoal")
        self.geometry("750x900")
        self.minsize(600, 750)
        self.configure(fg_color=BG)
        self.historico = []
        self.ouvindo = False
        self.pensando = False
        self.vozelecionada = "Antonio"
        self.velocidade_voz = 1.0
        self.modelo_ollama = "llama3.2"
        self.escuta_dinamica = None
        self._provider = "ollama"
        self._gemini_key = ""
        self._gemini_model = "gemini-3.6-flash"
        self._motor_voz = "google"
        self._tema = {}
        self._tray_icon = None
        self._config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
        self._load_config()
        configurar_motor_voz(self._motor_voz, self._gemini_key, self._gemini_model)
        self._aplicar_tema()
        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.bind("<Unmap>", self._on_minimize)
        self.after(100, self._iniciar_reminders)
        self.log("Jarvis", "Aos seus servicos, Senhor. Como posso ajuda-lo?")

    def _build_ui(self):
        header = ctk.CTkFrame(self, fg_color=PANEL, corner_radius=12)
        header.pack(fill="x", padx=15, pady=(15, 10))
        title_box = ctk.CTkFrame(header, fg_color="transparent")
        title_box.pack(side="left", padx=5, pady=10)
        ctk.CTkLabel(title_box, text="JARVIS", font=ctk.CTkFont(size=32, weight="bold"), text_color=ACCENT).pack(anchor="w")
        ctk.CTkLabel(title_box, text="assistente pessoal", font=ctk.CTkFont(size=12), text_color=MUTED).pack(anchor="w")
        btn_frame = ctk.CTkFrame(header, fg_color="transparent")
        btn_frame.pack(side="right", padx=5, pady=10)
        self._topmost = False
        self._topmost_btn = ctk.CTkButton(btn_frame, text="\U0001f512", width=38, height=34, corner_radius=10, fg_color="#1a1a3a", hover_color=ACCENT_DIM, text_color=TEXT, font=ctk.CTkFont(size=16), command=self._toggle_topmost)
        self._topmost_btn.pack(side="right", padx=(4, 0))
        ctk.CTkButton(btn_frame, text="?", width=38, height=34, corner_radius=10, fg_color="#1a1a3a", hover_color=ACCENT_DIM, text_color=TEXT, font=ctk.CTkFont(size=16, weight="bold"), command=self._open_help).pack(side="right", padx=(4, 0))
        ctk.CTkButton(btn_frame, text="\u2699", width=38, height=34, corner_radius=10, fg_color="#1a1a3a", hover_color=ACCENT_DIM, text_color=TEXT, font=ctk.CTkFont(size=16), command=self._open_settings).pack(side="right")

        self.status = ctk.CTkLabel(self, text="Pronto", font=ctk.CTkFont(size=12), text_color=MUTED)
        self.status.pack(anchor="w", padx=20, pady=(5, 0))

        self.chat = ctk.CTkTextbox(self, fg_color=PANEL, text_color=TEXT, font=ctk.CTkFont(size=13), wrap="word", border_width=1, border_color="#1a1a3a", corner_radius=12)
        self.chat.pack(padx=15, pady=10, fill="both", expand=True)
        self.chat.configure(state="disabled")

        input_card = ctk.CTkFrame(self, fg_color=PANEL, corner_radius=12)
        input_card.pack(fill="x", padx=15, pady=(0, 10))
        input_frame = ctk.CTkFrame(input_card, fg_color="transparent")
        input_frame.pack(fill="x", padx=10, pady=10)
        self.entry = ctk.CTkEntry(input_frame, placeholder_text="Digite seu comando...", height=42, corner_radius=10, fg_color="#1a1a3a", border_color="#2a2a4a", text_color=TEXT, font=ctk.CTkFont(size=13))
        self.entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.entry.bind("<Return>", lambda e: self._send())
        ctk.CTkButton(input_frame, text="Enviar", width=72, height=42, corner_radius=10, fg_color=ACCENT_DIM, hover_color=ACCENT, text_color=BG, font=ctk.CTkFont(size=13, weight="bold"), command=self._send).pack(side="left", padx=(0, 6))
        self.mic_btn = ctk.CTkButton(input_frame, text="Mic", width=50, height=42, corner_radius=10, fg_color="#2a2a4a", hover_color="#3a3a5a", text_color=TEXT, font=ctk.CTkFont(size=12), command=self._toggle_mic)
        self.mic_btn.pack(side="left", padx=(0, 6))
        self.stop_btn = ctk.CTkButton(input_frame, text="Parar", width=60, height=42, corner_radius=10, fg_color=RED, hover_color="#cc3333", text_color=TEXT, font=ctk.CTkFont(size=12, weight="bold"), command=self._stop_all)
        self.stop_btn.pack(side="left", padx=(0, 6))
        self.listen_btn = ctk.CTkButton(input_frame, text="Escuta: OFF", width=90, height=42, corner_radius=10, fg_color="#1a1a3a", hover_color="#2a2a4a", text_color=MUTED, font=ctk.CTkFont(size=11), command=self._toggle_escuta_dinamica)
        self.listen_btn.pack(side="left")

        quick_card = ctk.CTkFrame(self, fg_color=PANEL, corner_radius=12)
        quick_card.pack(fill="x", padx=15, pady=(0, 5))
        quick_title = ctk.CTkLabel(quick_card, text="  Acesso Rapido", font=ctk.CTkFont(size=12, weight="bold"), text_color=MUTED, anchor="w")
        quick_title.pack(anchor="w", padx=10, pady=(8, 4))
        quick = ctk.CTkFrame(quick_card, fg_color="transparent")
        quick.pack(fill="x", padx=10, pady=(0, 4))
        for texto, cmd in [("Monitorar PC", lambda: self._cmd_direct("monitorar pc")), ("Programas", lambda: self._cmd_direct("programas abertos")), ("Lembretes", lambda: self._cmd_direct("lembretes"))]:
            ctk.CTkButton(quick, text=texto, height=32, corner_radius=8, fg_color="#1a1a3a", hover_color=ACCENT_DIM, text_color=TEXT, font=ctk.CTkFont(size=12), command=cmd).pack(side="left", padx=(0, 4), expand=True, fill="x")
        quick2 = ctk.CTkFrame(quick_card, fg_color="transparent")
        quick2.pack(fill="x", padx=10, pady=(0, 10))
        for texto, cmd in [("Pesquisar", self._abrir_pesquisa), ("Codigo", self._abrir_codigo), ("Arquivos", self._abrir_arquivos), ("Dev", self._abrir_dev)]:
            ctk.CTkButton(quick2, text=texto, height=32, corner_radius=8, fg_color="#1a1a3a", hover_color=ACCENT_DIM, text_color=TEXT, font=ctk.CTkFont(size=12), command=cmd).pack(side="left", padx=(0, 4), expand=True, fill="x")

    def _open_settings(self):
        win = ctk.CTkToplevel(self)
        win.title("Configuracoes")
        win.geometry("480x560")
        win.configure(fg_color=BG)
        win.grab_set()
        tab = ctk.CTkTabview(win, fg_color=PANEL, segmented_button_fg_color=BG, segmented_button_selected_color=ACCENT, segmented_button_unselected_color=PANEL, text_color=TEXT, corner_radius=10)
        tab.pack(padx=15, pady=15, fill="both", expand=True)

        aba_voz = tab.add("Voz")
        scroll_voz = ctk.CTkScrollableFrame(aba_voz, fg_color="transparent")
        scroll_voz.pack(fill="both", expand=True)

        box_voz = ctk.CTkFrame(scroll_voz, fg_color="#1a1a3a", corner_radius=8)
        box_voz.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(box_voz, text="Voz do Jarvis", font=ctk.CTkFont(size=14, weight="bold"), text_color=ACCENT, anchor="w").pack(anchor="w", pady=(10, 8), padx=(12, 0))
        self._voice_var = ctk.StringVar(value=self.vozelecionada)
        for nome, voz_id in VOZES.items():
            ctk.CTkRadioButton(box_voz, text=f"{nome}  ({voz_id})", variable=self._voice_var, value=nome, text_color=TEXT, fg_color=ACCENT, hover_color=ACCENT_DIM, font=ctk.CTkFont(size=13)).pack(anchor="w", pady=3, padx=(20, 0))
        ctk.CTkFrame(box_voz, fg_color="transparent", height=8).pack()

        box_motor = ctk.CTkFrame(scroll_voz, fg_color="#1a1a3a", corner_radius=8)
        box_motor.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(box_motor, text="Reconhecimento de Voz", font=ctk.CTkFont(size=14, weight="bold"), text_color=ACCENT, anchor="w").pack(anchor="w", pady=(10, 8), padx=(12, 0))
        self._motor_var = ctk.StringVar(value=self._motor_voz)
        for motor, label in [("google", "Google (Online, mais rapido)"), ("gemini", "Gemini (Mais preciso, usa sua API key)")]:
            ctk.CTkRadioButton(box_motor, text=label, variable=self._motor_var, value=motor, text_color=TEXT, fg_color=ACCENT, hover_color=ACCENT_DIM, font=ctk.CTkFont(size=13)).pack(anchor="w", pady=3, padx=(20, 0))
        ctk.CTkLabel(box_motor, text="Gemini usa a mesma API key do cerebro", text_color=MUTED, font=ctk.CTkFont(size=11)).pack(anchor="w", padx=(20, 0), pady=(4, 10))

        box_vel = ctk.CTkFrame(scroll_voz, fg_color="#1a1a3a", corner_radius=8)
        box_vel.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(box_vel, text="Velocidade da voz", font=ctk.CTkFont(size=14, weight="bold"), text_color=ACCENT, anchor="w").pack(anchor="w", pady=(10, 8), padx=(12, 0))
        self._speed_slider = ctk.CTkSlider(box_vel, from_=0.5, to=2.0, number_of_steps=15, width=380, fg_color=PANEL, progress_color=ACCENT, button_color=ACCENT, button_hover_color=ACCENT_DIM)
        self._speed_slider.set(self.velocidade_voz)
        self._speed_slider.pack(anchor="w", padx=(20, 0))
        self._speed_label = ctk.CTkLabel(box_vel, text=f"Velocidade: {self.velocidade_voz:.1f}x", text_color=TEXT, font=ctk.CTkFont(size=13))
        self._speed_label.pack(anchor="w", padx=(20, 0), pady=(5, 0))
        self._speed_slider.configure(command=lambda v: self._speed_label.configure(text=f"Velocidade: {v:.1f}x"))
        ctk.CTkButton(box_vel, text="Testar voz", fg_color="#2a2a4a", hover_color="#3a3a5a", text_color=TEXT, font=ctk.CTkFont(size=12), command=lambda: threading.Thread(target=speak, args=("Teste de voz.", self._voice_var.get(), self._speed_slider.get()), daemon=True).start()).pack(pady=(10, 12), padx=(20, 0), anchor="w")

        aba_config = tab.add("Cerebro")
        scroll_config = ctk.CTkScrollableFrame(aba_config, fg_color="transparent")
        scroll_config.pack(fill="both", expand=True)

        box_provider = ctk.CTkFrame(scroll_config, fg_color="#1a1a3a", corner_radius=8)
        box_provider.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(box_provider, text="Cerebro do Jarvis", font=ctk.CTkFont(size=14, weight="bold"), text_color=ACCENT, anchor="w").pack(anchor="w", pady=(10, 8), padx=(12, 0))
        self._provider_var = ctk.StringVar(value=self._provider)
        for prov, label in [("ollama", "Ollama (Local, Gratis)"), ("gemini", "Google Gemini (Nuvem, Gratis)")]:
            ctk.CTkRadioButton(box_provider, text=label, variable=self._provider_var, value=prov, text_color=TEXT, fg_color=ACCENT, hover_color=ACCENT_DIM, font=ctk.CTkFont(size=13), command=self._on_provider_change).pack(anchor="w", pady=3, padx=(20, 0))
        ctk.CTkFrame(box_provider, fg_color="transparent", height=8).pack()

        self._box_ollama = ctk.CTkFrame(scroll_config, fg_color="#1a1a3a", corner_radius=8)
        self._box_ollama.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(self._box_ollama, text="Modelo Ollama", font=ctk.CTkFont(size=14, weight="bold"), text_color=ACCENT, anchor="w").pack(anchor="w", pady=(10, 8), padx=(12, 0))

        self._model_var = ctk.StringVar(value="llama3.2")
        self._modelos_info = {}

        model_frame = ctk.CTkFrame(self._box_ollama, fg_color="transparent")
        model_frame.pack(fill="x", padx=(20, 12), pady=(0, 8))

        self._model_combo = ctk.CTkOptionMenu(
            model_frame, values=["Carregando..."], variable=self._model_var,
            fg_color=PANEL, button_color="#1a1a3a", button_hover_color=ACCENT, text_color=TEXT,
            width=280, font=ctk.CTkFont(size=12)
        )
        self._model_combo.pack(side="left", fill="x", expand=True)

        ctk.CTkButton(
            model_frame, text="\U0001f504", width=32, height=30, corner_radius=6,
            fg_color="#2a2a4a", hover_color="#3a3a5a", text_color=TEXT,
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._atualizar_modelos
        ).pack(side="left", padx=(8, 0))

        self._model_info_label = ctk.CTkLabel(
            self._box_ollama, text="", text_color=MUTED, font=ctk.CTkFont(size=11), justify="left"
        )
        self._model_info_label.pack(anchor="w", padx=(20, 12), pady=(0, 10))

        self._model_combo.configure(command=lambda v: self._atualizar_info_modelo(v))

        box_host = ctk.CTkFrame(self._box_ollama, fg_color="transparent")
        box_host.pack(fill="x", padx=(0, 0), pady=(0, 8))
        ctk.CTkLabel(box_host, text="Host Ollama", font=ctk.CTkFont(size=12, weight="bold"), text_color=TEXT, anchor="w").pack(anchor="w", padx=(20, 0), pady=(0, 4))
        self._host_entry = ctk.CTkEntry(box_host, fg_color=PANEL, border_color="#1a1a3a", text_color=TEXT, placeholder_text="http://localhost:11434", height=32, font=ctk.CTkFont(size=12))
        self._host_entry.pack(fill="x", padx=(20, 12), pady=(0, 0))

        self._box_gemini = ctk.CTkFrame(scroll_config, fg_color="#1a1a3a", corner_radius=8)
        self._box_gemini.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(self._box_gemini, text="Google Gemini", font=ctk.CTkFont(size=14, weight="bold"), text_color=ACCENT, anchor="w").pack(anchor="w", pady=(10, 8), padx=(12, 0))

        box_key = ctk.CTkFrame(self._box_gemini, fg_color="transparent")
        box_key.pack(fill="x")
        ctk.CTkLabel(box_key, text="API Key", font=ctk.CTkFont(size=12, weight="bold"), text_color=TEXT, anchor="w").pack(anchor="w", padx=(20, 0), pady=(0, 4))
        self._gemini_key_entry = ctk.CTkEntry(box_key, fg_color=PANEL, border_color="#1a1a3a", text_color=TEXT, placeholder_text="AIza...", height=32, font=ctk.CTkFont(size=12), show="*")
        self._gemini_key_entry.pack(fill="x", padx=(20, 12), pady=(0, 2))
        self._gemini_key_entry.insert(0, self._gemini_key)
        ctk.CTkLabel(box_key, text="Gratis: 15 req/min - aistudio.google.com/apikey", text_color=MUTED, font=ctk.CTkFont(size=11)).pack(anchor="w", padx=(20, 0), pady=(0, 8))

        box_gmodel = ctk.CTkFrame(self._box_gemini, fg_color="transparent")
        box_gmodel.pack(fill="x")
        ctk.CTkLabel(box_gmodel, text="Modelo", font=ctk.CTkFont(size=12, weight="bold"), text_color=TEXT, anchor="w").pack(anchor="w", padx=(20, 0), pady=(0, 4))
        self._gemini_model_var = ctk.StringVar(value=self._gemini_model)
        ctk.CTkOptionMenu(box_gmodel, values=GEMINI_MODELS, variable=self._gemini_model_var, fg_color=PANEL, button_color="#1a1a3a", button_hover_color=ACCENT, text_color=TEXT, width=350, font=ctk.CTkFont(size=12)).pack(padx=(20, 12), pady=(0, 12))

        self.after(100, self._atualizar_modelos)
        self.after(200, self._on_provider_change)

        aba_sobre = tab.add("Sobre")
        scroll_sobre = ctk.CTkScrollableFrame(aba_sobre, fg_color="transparent")
        scroll_sobre.pack(fill="both", expand=True)

        box_sobre = ctk.CTkFrame(scroll_sobre, fg_color="#1a1a3a", corner_radius=8)
        box_sobre.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(box_sobre, text="Jarvis - Assistente Pessoal", font=ctk.CTkFont(size=18, weight="bold"), text_color=ACCENT).pack(pady=(20, 10))
        ctk.CTkLabel(box_sobre, text="Assistente virtual local e gratuito.\nUsa Ollama como cerebro.\nVozes neurais da Microsoft.", text_color=TEXT, font=ctk.CTkFont(size=13), justify="center").pack(padx=20)

        box_func = ctk.CTkFrame(scroll_sobre, fg_color="#1a1a3a", corner_radius=8)
        box_func.pack(fill="x", pady=(8, 0))
        ctk.CTkLabel(box_func, text="Funcionalidades", font=ctk.CTkFont(size=14, weight="bold"), text_color=ACCENT, anchor="w").pack(anchor="w", pady=(10, 8), padx=(12, 0))
        funcionalidades = [
            "Abrir/fechar programas pela voz",
            "Criar e rodar codigo",
            "Pesquisar na internet",
            "Monitorar o PC em tempo real",
            "Gerenciar arquivos",
            "Lembretes e avisos",
            "Escuta dinamica continua",
            "Modo desenvolvedor",
            "Atualizacoes automaticas",
            "Ollama local + Gemini gratuito",
        ]
        for func in funcionalidades:
            ctk.CTkLabel(box_func, text=f"\u2713  {func}", font=ctk.CTkFont(size=13), text_color=TEXT, anchor="w").pack(anchor="w", padx=(20, 0), pady=2)
        ctk.CTkFrame(box_func, fg_color="transparent", height=10).pack()

        aba_tema = tab.add("Tema")
        scroll_tema = ctk.CTkScrollableFrame(aba_tema, fg_color="transparent")
        scroll_tema.pack(fill="both", expand=True)

        self._tema_cores = {
            "accent": ctk.StringVar(value=self._tema.get("accent", ACCENT_PADRAO)),
            "bg": ctk.StringVar(value=self._tema.get("bg", BG_PADRAO)),
            "panel": ctk.StringVar(value=self._tema.get("panel", PANEL_PADRAO)),
            "text": ctk.StringVar(value=self._tema.get("text", TEXT_PADRAO)),
        }

        box_tema_cor = ctk.CTkFrame(scroll_tema, fg_color="#1a1a3a", corner_radius=8)
        box_tema_cor.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(box_tema_cor, text="Cores do Jarvis", font=ctk.CTkFont(size=14, weight="bold"), text_color=ACCENT, anchor="w").pack(anchor="w", pady=(10, 8), padx=(12, 0))

        self._tema_preview = ctk.CTkFrame(box_tema_cor, fg_color=self._tema_cores["bg"].get(), corner_radius=8, border_width=2, border_color=self._tema_cores["accent"].get())
        self._tema_preview.pack(fill="x", padx=(20, 20), pady=(0, 10))
        ctk.CTkLabel(self._tema_preview, text="Preview", font=ctk.CTkFont(size=13, weight="bold"), text_color=self._tema_cores["accent"].get()).pack(pady=(8, 4))
        ctk.CTkLabel(self._tema_preview, text="Texto de exemplo", font=ctk.CTkFont(size=12), text_color=self._tema_cores["text"].get()).pack(pady=(0, 8))

        def _escolher_cor(key, label_widget):
            atual = self._tema_cores[key].get()
            cor = colorchooser.askcolor(initialcolor=atual, title="Escolha uma cor")
            if cor and cor[1]:
                self._tema_cores[key].set(cor[1])
                label_widget.configure(text=cor[1], text_color=cor[1])
                _atualizar_preview()

        def _atualizar_preview():
            try:
                self._tema_preview.configure(
                    fg_color=self._tema_cores["bg"].get(),
                    border_color=self._tema_cores["accent"].get()
                )
                for w in self._tema_preview.winfo_children():
                    if isinstance(w, ctk.CTkLabel):
                        txt = w.cget("text")
                        if txt == "Preview":
                            w.configure(text_color=self._tema_cores["accent"].get())
                        else:
                            w.configure(text_color=self._tema_cores["text"].get())
            except Exception:
                pass

        cores_config = [
            ("accent", "Cor de Destaque", "Botoes, titulos, destaques"),
            ("bg", "Cor de Fundo", "Fundo principal da janela"),
            ("panel", "Cor dos Painéis", "Caixas e cards"),
            ("text", "Cor do Texto", "Texto principal"),
        ]
        self._tema_color_labels = {}
        for key, titulo, desc in cores_config:
            row = ctk.CTkFrame(box_tema_cor, fg_color="transparent")
            row.pack(fill="x", padx=(20, 12), pady=4)
            ctk.CTkLabel(row, text=titulo, font=ctk.CTkFont(size=12, weight="bold"), text_color=TEXT, width=140, anchor="w").pack(side="left")
            color_lbl = ctk.CTkLabel(row, text=self._tema_cores[key].get(), text_color=self._tema_cores[key].get(), font=ctk.CTkFont(size=12), width=80)
            color_lbl.pack(side="left", padx=(0, 8))
            self._tema_color_labels[key] = color_lbl
            ctk.CTkButton(row, text="Escolher", width=80, height=28, corner_radius=6, fg_color="#2a2a4a", hover_color="#3a3a5a", text_color=TEXT, font=ctk.CTkFont(size=11), command=lambda k=key, l=color_lbl: _escolher_cor(k, l)).pack(side="left")
            ctk.CTkLabel(row, text=desc, text_color=MUTED, font=ctk.CTkFont(size=10)).pack(side="left", padx=(8, 0))

        ctk.CTkFrame(box_tema_cor, fg_color="transparent", height=8).pack()

        box_intensidade = ctk.CTkFrame(scroll_tema, fg_color="#1a1a3a", corner_radius=8)
        box_intensidade.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(box_intensidade, text="Intensidade", font=ctk.CTkFont(size=14, weight="bold"), text_color=ACCENT, anchor="w").pack(anchor="w", pady=(10, 8), padx=(12, 0))
        ctk.CTkLabel(box_intensidade, text="Brilho do tema (aplica ao reiniciar)", text_color=MUTED, font=ctk.CTkFont(size=11)).pack(anchor="w", padx=(20, 0))

        self._intensidade_slider = ctk.CTkSlider(box_intensidade, from_=0.3, to=1.5, number_of_steps=12, width=380, fg_color=PANEL, progress_color=ACCENT, button_color=ACCENT, button_hover_color=ACCENT_DIM)
        self._intensidade_slider.set(self._tema.get("intensidade", 1.0))
        self._intensidade_slider.pack(anchor="w", padx=(20, 0), pady=(5, 0))
        self._intensidade_label = ctk.CTkLabel(box_intensidade, text=f"Intensidade: {self._tema.get('intensidade', 1.0):.1f}x", text_color=TEXT, font=ctk.CTkFont(size=13))
        self._intensidade_label.pack(anchor="w", padx=(20, 0), pady=(5, 0))
        self._intensidade_slider.configure(command=lambda v: self._intensidade_label.configure(text=f"Intensidade: {v:.1f}x"))
        ctk.CTkFrame(box_intensidade, fg_color="transparent", height=10).pack()

        box_reset = ctk.CTkFrame(scroll_tema, fg_color="#1a1a3a", corner_radius=8)
        box_reset.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(box_reset, text="Restaurar Padrao", font=ctk.CTkFont(size=14, weight="bold"), text_color=ACCENT, anchor="w").pack(anchor="w", pady=(10, 8), padx=(12, 0))
        def _resetar_tema():
            self._tema_cores["accent"].set(ACCENT_PADRAO)
            self._tema_cores["bg"].set(BG_PADRAO)
            self._tema_cores["panel"].set(PANEL_PADRAO)
            self._tema_cores["text"].set(TEXT_PADRAO)
            self._intensidade_slider.set(1.0)
            self._intensidade_label.configure(text="Intensidade: 1.0x")
            for key, lbl in self._tema_color_labels.items():
                cor = self._tema_cores[key].get()
                lbl.configure(text=cor, text_color=cor)
            _atualizar_preview()
        ctk.CTkButton(box_reset, text="Restaurar cores padrao", fg_color="#2a2a4a", hover_color=RED, text_color=TEXT, font=ctk.CTkFont(size=12), command=_resetar_tema).pack(pady=(0, 12), padx=(20, 0), anchor="w")
        ctk.CTkFrame(box_reset, fg_color="transparent", height=5).pack()

        def salvar():
            self.vozelecionada = self._voice_var.get()
            self.velocidade_voz = self._speed_slider.get()
            display = self._model_var.get()
            info = self._modelos_info.get(display, {})
            self.modelo_ollama = info.get("nome", "llama3.2")
            self._provider = self._provider_var.get()
            self._gemini_key = self._gemini_key_entry.get().strip()
            self._gemini_model = self._gemini_model_var.get()
            self._motor_voz = self._motor_var.get()
            configurar_motor_voz(self._motor_voz, self._gemini_key, self._gemini_model)
            self._atualizar_host_ollama()
            win.destroy()
        ctk.CTkButton(win, text="Salvar", fg_color=ACCENT_DIM, hover_color=ACCENT, text_color=BG, font=ctk.CTkFont(size=14, weight="bold"), height=40, corner_radius=10, command=salvar).pack(pady=(0, 15), padx=15, fill="x")

    def _open_help(self):
        win = ctk.CTkToplevel(self)
        win.title("Comandos do Jarvis")
        win.geometry("480x560")
        win.configure(fg_color=BG)
        win.grab_set()

        tab = ctk.CTkTabview(win, fg_color=PANEL, segmented_button_fg_color=BG, segmented_button_selected_color=ACCENT, segmented_button_unselected_color=PANEL, text_color=TEXT, corner_radius=10)
        tab.pack(padx=15, pady=15, fill="both", expand=True)

        def _add_comandos(aba, comandos):
            scroll = ctk.CTkScrollableFrame(aba, fg_color="transparent")
            scroll.pack(fill="both", expand=True)
            for titulo, exemplos in comandos:
                box = ctk.CTkFrame(scroll, fg_color="#1a1a3a", corner_radius=8)
                box.pack(fill="x", pady=(0, 8), padx=(0, 5))
                ctk.CTkLabel(box, text=titulo, font=ctk.CTkFont(size=14, weight="bold"), text_color=ACCENT, anchor="w").pack(anchor="w", pady=(8, 4), padx=(12, 0))
                for ex in exemplos:
                    ctk.CTkLabel(box, text=f"\u2022  {ex}", font=ctk.CTkFont(size=13), text_color=TEXT, anchor="w").pack(anchor="w", padx=(20, 0), pady=1)
                ctk.CTkFrame(box, fg_color="transparent", height=6).pack()

        aba_sistema = tab.add("Sistema")
        _add_comandos(aba_sistema, [
            ("Monitorar PC", [
                "qual o status do pc",
                "como esta o desempenho",
                "monitorar pc",
                "verificar computador",
            ]),
            ("Programas abertos", [
                "quais programas estao abertos",
                "o que esta rodando",
                "lista de programas",
            ]),
            ("Abrir programa", [
                "abra o discord",
                "abrir spotify",
                "iniciar steam",
                "quero abrir o chrome",
            ]),
            ("Fechar programa", [
                "feche o discord",
                "fechar spotify",
                "encerrar steam",
            ]),
            ("Abrir em monitor", [
                "abra o discord no monitor 2",
                "abrir spotify no segundo monitor",
            ]),
        ])

        aba_lembretes = tab.add("Lembretes")
        _add_comandos(aba_lembretes, [
            ("Criar lembrete", [
                "me avise em 5 minutos",
                "lembra de beber agua em 1 hora",
                "avisar em 30 min",
            ]),
            ("Ver lembretes", [
                "meus lembretes",
                "lembretes",
                "compromissos",
            ]),
        ])

        aba_arquivos = tab.add("Arquivos")
        _add_comandos(aba_arquivos, [
            ("Listar arquivos", [
                "liste os arquivos em C:\\",
                "mostrar pastas em Documentos",
                "ver conteudo de Downloads",
            ]),
            ("Criar arquivo", [
                "crie um arquivo notas.txt com conteudo",
                "novo arquivo lista.md com itens",
            ]),
            ("Deletar arquivo", [
                "delete notas.txt",
                "apague lixo.txt",
                "remover arquivo antigo",
            ]),
        ])

        aba_pesquisa = tab.add("Pesquisa")
        _add_comandos(aba_pesquisa, [
            ("Pesquisar na internet", [
                "pesquise na internet",
                "procure sobre python",
                "busque noticias",
            ]),
            ("Criar codigo", [
                "crie um codigo em python para",
                "crie um programa em java que",
            ]),
        ])

        aba_voz = tab.add("Voz")
        _add_comandos(aba_voz, [
            ("Trocar voz", [
                "trocar voz para Antonio",
                "mudar voz para Francisca",
            ]),
            ("Velocidade", [
                "velocidade da voz 1.5",
                "voz rapida",
                "voz devagar",
            ]),
            ("Listar vozes", [
                "quais sao as vozes",
                "listar vozes",
            ]),
        ])

        aba_dev = tab.add("Dev")
        _add_comandos(aba_dev, [
            ("Modificar codigo", [
                "Use a aba Dev na GUI para modificar arquivos do Jarvis",
            ]),
        ])

    def _abrir_pesquisa(self):
        win = ctk.CTkToplevel(self)
        win.title("Pesquisar na internet")
        win.geometry("400x180")
        win.configure(fg_color=BG)
        win.grab_set()
        ctk.CTkLabel(win, text="O que quer pesquisar?", font=ctk.CTkFont(size=14, weight="bold"), text_color=TEXT).pack(pady=(20, 10))
        entry = ctk.CTkEntry(win, fg_color=PANEL, border_color="#1a1a3a", text_color=TEXT, placeholder_text="Digite sua busca...", height=38, corner_radius=10)
        entry.pack(fill="x", padx=20, pady=(0, 15))
        entry.focus()
        def enviar():
            texto = entry.get().strip()
            if texto:
                win.destroy()
                self._cmd_direct(f"pesquise na internet por {texto}")
        entry.bind("<Return>", lambda e: enviar())
        ctk.CTkButton(win, text="Pesquisar", fg_color=ACCENT_DIM, hover_color=ACCENT, text_color=BG, command=enviar).pack(padx=20, fill="x")

    def _abrir_codigo(self):
        win = ctk.CTkToplevel(self)
        win.title("Criar codigo")
        win.geometry("450x280")
        win.configure(fg_color=BG)
        win.grab_set()
        ctk.CTkLabel(win, text="Criar e rodar codigo", font=ctk.CTkFont(size=14, weight="bold"), text_color=TEXT).pack(pady=(20, 10))
        lang_frame = ctk.CTkFrame(win, fg_color="transparent")
        lang_frame.pack(fill="x", padx=20, pady=(0, 10))
        ctk.CTkLabel(lang_frame, text="Linguagem:", text_color=MUTED, font=ctk.CTkFont(size=11)).pack(side="left")
        lang_var = ctk.StringVar(value="Python")
        ctk.CTkOptionMenu(lang_frame, values=["Python", "Java", "C"], variable=lang_var, width=120, fg_color=PANEL, button_color="#1a1a3a", button_hover_color=ACCENT, text_color=TEXT).pack(side="right")
        entry = ctk.CTkTextbox(win, fg_color=PANEL, border_color="#1a1a3a", text_color=TEXT, height=100, corner_radius=10, font=ctk.CTkFont(size=12))
        entry.pack(fill="x", padx=20, pady=(0, 15))
        def enviar():
            desc = entry.get("1.0", "end").strip()
            if desc:
                lang = lang_var.get().lower()
                win.destroy()
                self._cmd_direct(f"crie um codigo em {lang} para {desc}")
        ctk.CTkButton(win, text="Criar e rodar", fg_color=ACCENT_DIM, hover_color=ACCENT, text_color=BG, command=enviar).pack(padx=20, fill="x")

    def _abrir_arquivos(self):
        win = ctk.CTkToplevel(self)
        win.title("Gerenciar arquivos")
        win.geometry("420x300")
        win.configure(fg_color=BG)
        win.grab_set()
        ctk.CTkLabel(win, text="Gerenciar arquivos", font=ctk.CTkFont(size=14, weight="bold"), text_color=TEXT).pack(pady=(20, 10))
        ctk.CTkLabel(win, text="Listar pasta:", text_color=MUTED, font=ctk.CTkFont(size=11)).pack(anchor="w", padx=20)
        listar_entry = ctk.CTkEntry(win, fg_color=PANEL, border_color="#1a1a3a", text_color=TEXT, placeholder_text="Caminho da pasta...", height=35, corner_radius=8)
        listar_entry.pack(fill="x", padx=20, pady=(0, 10))
        def listar():
            path = listar_entry.get().strip()
            if path:
                win.destroy()
                self._cmd_direct(f"liste os arquivos em {path}")
        ctk.CTkButton(win, text="Listar", fg_color="#2a2a4a", hover_color="#3a3a5a", text_color=TEXT, command=listar).pack(fill="x", padx=20, pady=(0, 15))
        ctk.CTkLabel(win, text="Criar arquivo:", text_color=MUTED, font=ctk.CTkFont(size=11)).pack(anchor="w", padx=20)
        criar_frame = ctk.CTkFrame(win, fg_color="transparent")
        criar_frame.pack(fill="x", padx=20, pady=(0, 10))
        criar_nome = ctk.CTkEntry(criar_frame, fg_color=PANEL, border_color="#1a1a3a", text_color=TEXT, placeholder_text="nome.txt", width=150, height=35, corner_radius=8)
        criar_nome.pack(side="left", padx=(0, 5))
        criar_conteudo = ctk.CTkEntry(criar_frame, fg_color=PANEL, border_color="#1a1a3a", text_color=TEXT, placeholder_text="conteudo...", height=35, corner_radius=8)
        criar_conteudo.pack(side="left", fill="x", expand=True)
        def criar():
            nome = criar_nome.get().strip()
            conteudo = criar_conteudo.get().strip()
            if nome:
                win.destroy()
                self._cmd_direct(f"crie um arquivo {nome} com {conteudo or 'vazio'}")
        ctk.CTkButton(win, text="Criar arquivo", fg_color="#2a2a4a", hover_color="#3a3a5a", text_color=TEXT, command=criar).pack(fill="x", padx=20)

    def _abrir_dev(self):
        win = ctk.CTkToplevel(self)
        win.title("Modo Desenvolvedor")
        win.geometry("560x520")
        win.configure(fg_color=BG)
        win.grab_set()

        tab = ctk.CTkTabview(win, fg_color=PANEL, segmented_button_fg_color=BG, segmented_button_selected_color=ORANGE, segmented_button_unselected_color=PANEL, text_color=TEXT, corner_radius=10)
        tab.pack(padx=15, pady=15, fill="both", expand=True)

        aba_mod = tab.add("Modificar")
        ctk.CTkLabel(aba_mod, text="Modificar Codigo Fonte", font=ctk.CTkFont(size=14, weight="bold"), text_color=ORANGE).pack(anchor="w", pady=(5, 10))
        ctk.CTkLabel(aba_mod, text="Arquivo:", text_color=TEXT, font=ctk.CTkFont(size=12)).pack(anchor="w")
        arquivos = listar_arquivos_codigo()
        arquivo_var = ctk.StringVar(value=arquivos[0] if arquivos else "")
        ctk.CTkOptionMenu(aba_mod, values=arquivos, variable=arquivo_var, width=300, fg_color=PANEL, button_color="#1a1a3a", button_hover_color=ACCENT, text_color=TEXT).pack(pady=(5, 10))
        ctk.CTkLabel(aba_mod, text="O que mudar:", text_color=TEXT, font=ctk.CTkFont(size=12)).pack(anchor="w")
        desc_entry = ctk.CTkTextbox(aba_mod, fg_color=PANEL, border_color="#1a1a3a", text_color=TEXT, height=60, corner_radius=10, font=ctk.CTkFont(size=12))
        desc_entry.pack(fill="x", pady=(5, 10))
        resultado_text = ctk.CTkTextbox(aba_mod, fg_color=PANEL, border_color="#1a1a3a", text_color=GREEN, height=80, corner_radius=10, font=ctk.CTkFont(size=10))
        resultado_text.pack(fill="x", pady=(0, 10))
        resultado_text.configure(state="disabled")
        btn_frame = ctk.CTkFrame(aba_mod, fg_color="transparent")
        btn_frame.pack(fill="x")

        def gerar():
            desc = desc_entry.get("1.0", "end").strip()
            arquivo = arquivo_var.get()
            if not desc:
                return
            resultado_text.configure(state="normal")
            resultado_text.delete("1.0", "end")
            resultado_text.insert("1.0", "Gerando modificacao... Backup sendo criado...")
            resultado_text.configure(state="disabled")
            def tarefa():
                novo, diff, original = aplicar_modificacao(arquivo, desc, provider=self._provider, api_key=self._get_api_key(), modelo=self._get_modelo())
                if novo and diff:
                    self.after(0, lambda: _mostrar_resultado(diff, novo, arquivo))
                else:
                    erro = diff if diff else f"Nao consegui gerar a modificacao.\nVerifique se o {self._provider.upper()} esta rodando."
                    self.after(0, lambda: _mostrar_erro(erro))
            threading.Thread(target=tarefa, daemon=True).start()

        def _mostrar_resultado(diff, novo_conteudo, arquivo):
            resultado_text.configure(state="normal")
            resultado_text.delete("1.0", "end")
            resultado_text.insert("1.0", diff)
            resultado_text.configure(state="disabled")
            for w in btn_frame.winfo_children():
                w.destroy()
            def aprovar():
                msg = salvar_arquivo(arquivo, novo_conteudo)
                resultado_text.configure(state="normal")
                resultado_text.delete("1.0", "end")
                resultado_text.insert("1.0", msg)
                resultado_text.configure(state="disabled")
                for w in btn_frame.winfo_children():
                    w.destroy()
                ctk.CTkButton(btn_frame, text="Gerar Modificacao", fg_color=ACCENT_DIM, hover_color=ACCENT, text_color=BG, font=ctk.CTkFont(size=13, weight="bold"), command=gerar).pack(fill="x")
            ctk.CTkButton(btn_frame, text="Aprovar e Salvar", fg_color=GREEN, hover_color="#00cc66", text_color=BG, font=ctk.CTkFont(size=12, weight="bold"), command=aprovar).pack(side="left", expand=True, fill="x", padx=(0, 4))
            ctk.CTkButton(btn_frame, text="Cancelar", fg_color=RED, hover_color="#cc3333", text_color=TEXT, font=ctk.CTkFont(size=12), command=_limpar).pack(side="left", expand=True, fill="x")

        def _mostrar_erro(msg):
            resultado_text.configure(state="normal")
            resultado_text.delete("1.0", "end")
            resultado_text.insert("1.0", msg)
            resultado_text.configure(state="disabled")

        def _limpar():
            resultado_text.configure(state="normal")
            resultado_text.delete("1.0", "end")
            resultado_text.configure(state="disabled")
            for w in btn_frame.winfo_children():
                w.destroy()
            ctk.CTkButton(btn_frame, text="Gerar Modificacao", fg_color=ACCENT_DIM, hover_color=ACCENT, text_color=BG, font=ctk.CTkFont(size=13, weight="bold"), command=gerar).pack(fill="x")

        ctk.CTkButton(btn_frame, text="Gerar Modificacao", fg_color=ACCENT_DIM, hover_color=ACCENT, text_color=BG, font=ctk.CTkFont(size=13, weight="bold"), command=gerar).pack(fill="x")

        aba_bak = tab.add("Backups")
        ctk.CTkLabel(aba_bak, text="Restaurar Backup", font=ctk.CTkFont(size=14, weight="bold"), text_color=ORANGE).pack(anchor="w", pady=(5, 10))
        backups = listar_backups()
        if backups:
            bak_var = ctk.StringVar(value=backups[0])
            ctk.CTkOptionMenu(aba_bak, values=backups, variable=bak_var, width=400, fg_color=PANEL, button_color="#1a1a3a", button_hover_color=ACCENT, text_color=TEXT).pack(pady=(5, 10))
            bak_status = ctk.CTkLabel(aba_bak, text="", text_color=MUTED, font=ctk.CTkFont(size=11))
            bak_status.pack(anchor="w")
            def restaurar():
                msg = restaurar_backup(bak_var.get())
                bak_status.configure(text=msg, text_color=GREEN if "sucesso" in msg else RED)
            ctk.CTkButton(aba_bak, text="Restaurar Backup", fg_color=ORANGE, hover_color="#cc8800", text_color=BG, font=ctk.CTkFont(size=12, weight="bold"), command=restaurar).pack(pady=(10, 0))
        else:
            ctk.CTkLabel(aba_bak, text="Nenhum backup disponivel.\nBackups sao criados automaticamente\nao salvar modificacoes.", text_color=MUTED, font=ctk.CTkFont(size=12), justify="center").pack(pady=30)

    def log(self, sender, text):
        def _inserir():
            self.chat.configure(state="normal")
            prefix = "Voce" if sender == "user" else "Jarvis"
            text_limpo = _strip_ansi(text)
            self.chat.insert("end", f"{prefix}: {text_limpo}\n\n")
            self.chat.configure(state="disabled")
            self.chat.see("end")
        self.after(0, _inserir)

    def _set_status(self, text, color=None):
        self.after(0, lambda: self.status.configure(text=text, text_color=color or MUTED))

    def _send(self):
        text = self.entry.get().strip()
        if not text:
            return
        self.entry.delete(0, "end")
        self.log("user", text)
        threading.Thread(target=self._process, args=(text,), daemon=True).start()

    def _cmd_direct(self, text):
        self.log("user", text)
        threading.Thread(target=self._process, args=(text,), daemon=True).start()

    def _toggle_mic(self):
        if self.ouvindo:
            return
        self.ouvindo = True
        self.mic_btn.configure(fg_color=RED)
        self._set_status("Ouvindo...", GREEN)
        threading.Thread(target=self._listen_flow, daemon=True).start()

    def _stop_all(self):
        self.pensando = False
        threading.Thread(target=stop_speak, daemon=True).start()
        self.after(0, lambda: self.stop_btn.configure(fg_color=RED))
        self._set_status("Interrompido", RED)
        self.after(2000, lambda: self._set_status("Pronto"))

    def _listen_flow(self):
        texto = listen()
        self.ouvindo = False
        self.after(0, lambda: self.mic_btn.configure(fg_color="#2a2a4a"))
        if texto:
            self.log("user", texto)
            self._process(texto)
        else:
            self._set_status("Nao entendi")
            self.after(2000, lambda: self._set_status("Pronto"))

    def _on_dynamic_voice(self, texto):
        self.after(0, lambda: self._handle_dynamic(texto))

    def _handle_dynamic(self, texto):
        self.log("user", texto)
        self._set_status("Ouvindo via voz...", GREEN)
        threading.Thread(target=self._process, args=(texto,), daemon=True).start()

    def _toggle_escuta_dinamica(self):
        if self.escuta_dinamica and self.escuta_dinamica.ativo:
            self.escuta_dinamica.parar()
            self.escuta_dinamica = None
            self.listen_btn.configure(text="Escuta: OFF", fg_color="#1a1a3a", text_color=MUTED)
            self._set_status("Escuta dinamica desligada")
        else:
            self.escuta_dinamica = EscutaDinamica(callback=self._on_dynamic_voice)
            self.escuta_dinamica.iniciar()
            self.listen_btn.configure(text="Escuta: ON", fg_color=GREEN, text_color=BG)
            self._set_status("Diga 'Jarvis' para ativar", GREEN)

    def _process(self, text):
        self.pensando = True
        self.after(0, lambda: self.stop_btn.configure(fg_color=ORANGE))
        self._set_status("Pensando...", ORANGE)
        text_low = text.lower().strip()
        resp = self._check_system_commands(text_low)
        if resp:
            self._finish(text, resp)
            return
        if not self.pensando:
            return
        code_match = re.match(r"(?:cria|crie|escreva|faca)\s+(?:um\s+)?(?:codigo|programa|script)\s+(?:em\s+)?(python|java|c)\s+(?:para|pra|que)\s+(.+)", text_low)
        if code_match:
            lang = code_match.group(1)
            task = code_match.group(2)
            self._set_status(f"Criando codigo em {lang}...")
            resp = self._handle_code(lang, task)
            self._finish(text, resp)
            return
        if not self.pensando:
            return
        search_match = re.match(r"(?:pesquisa|pesquise|procure|busque|procurar|buscar)\s+(?:na\s+internet\s+)?(?:por\s+|sobre\s+)?(.+)", text_low)
        if search_match:
            self._set_status("Pesquisando na internet...")
            query = search_match.group(1)
            resultados = search(query)
            resp = chat(f"Resuma de forma curta:\n{resultados}", modelo=self._get_modelo(), provider=self._provider, api_key=self._get_api_key())
            self._finish(text, resp)
            return
        if not self.pensando:
            return
        self._set_status("Pensando...")
        resp = chat(text, self.historico, modelo=self._get_modelo(), provider=self._provider, api_key=self._get_api_key())
        self._finish(text, resp)

    def _limpar_artigo(self, texto):
        """Remove artigos e conectivos comuns do inicio do comando."""
        texto = texto.strip()
        artigos = ["o ", "a ", "os ", "as ", "um ", "uma ", "uns ", "umas ",
                    "do ", "da ", "dos ", "das ", "no ", "na ", "nos ", "nas ",
                    "ao ", "aos ", "pela ", "pelo "]
        for artigo in artigos:
            if texto.startswith(artigo):
                texto = texto[len(artigo):]
                break
        return texto.strip()

    def _parse_monitor(self, texto):
        """Extrai numero do monitor de um texto. Ex: 'no segundo monitor' -> 2."""
        texto = texto.lower()
        # "no monitor 2", "no segundo monitor", "no terceiro monitor", etc.
        mapa_numeros = {
            "primeiro": 1, "um": 1, "1": 1, "1o": 1,
            "segundo": 2, "dois": 2, "2": 2, "2o": 2,
            "terceiro": 3, "tres": 3, "3": 3, "3o": 3,
            "quarto": 4, "quatro": 4, "4": 4, "4o": 4,
            "quinto": 5, "cinco": 5, "5": 5, "5o": 5,
        }
        # Procura "monitor X" ou "monitor Y"
        m = re.search(r"monitor\s+(\d+)", texto)
        if m:
            return int(m.group(1))
        # Procura "no segundo monitor", "no terceiro monitor", etc.
        for palavra, num in mapa_numeros.items():
            if f"monitor" in texto and palavra in texto:
                return num
            if f"{palavra} monitor" in texto:
                return num
        # Procura "monitor" sozinho (assume monitor 2 se tiver mais de um)
        return None

    def _check_system_commands(self, text):
        # Abrir pasta
        m = re.match(r"(?:abra|abrir|abre)\s+(?:a\s+)?(?:pasta|diretorio)\s+(.+)", text)
        if m:
            return open_folder(m.group(1).strip())

        # Abrir arquivo por caminho
        m = re.match(r"(?:abra|abrir|abre)\s+(?:o\s+)?arquivo\s+(.+)", text)
        if m:
            return open_file(m.group(1).strip())

        # Ver tela
        if re.search(r"(?:veja|ver|olhe|olha|mostra|mostrar)\s+(?:a\s+)?(?:tela|monitor|display|screen)", text):
            return "Permita-me observar a tela, Senhor.\n" + ver_tela(api_key=self._get_api_key(), modelo=self._get_modelo())

        # Criar imagem
        m = re.match(r"(?:crie|cria|gerar|gere|crie uma|cria uma|fazer|faça)\s+(?:uma\s+)?imagem\s+(?:de\s+|sobre\s+)?(.+)", text)
        if m:
            return criar_imagem(m.group(1).strip(), api_key=self._get_api_key(), modelo=self._get_modelo())

        # Ajuda / Comandos
        if text in ("?", "ajuda", "comandos", "help", "o que voce faz", "o que voce sabe fazer"):
            return """Aqui estao meus comandos, Senhor:

ABRIR/FECHAR:
- "abra [programa]" - abre um programa
- "abra pasta [nome]" - abre uma pasta
- "abra arquivo [caminho]" - abre um arquivo
- "feche [programa]" - fecha um programa

SISTEMA:
- "monitorar pc" - ver desempenho do PC
- "programas abertos" - lista de programas
- "desligar computador" - desliga o PC
- "reiniciar computador" - reinicia o PC
- "suspender" - modo suspensao

ARQUIVOS:
- "liste arquivos em [pasta]" - ver conteudo
- "crie arquivo [nome] com [conteudo]" - criar arquivo
- "delete [arquivo]" - remover arquivo

OUTROS:
- "veja a tela" - descrever tela
- "pesquise [assunto] na internet" - buscar info
- "crie codigo em [linguagem] para [tarefa]"
- "lembrete [texto] em [tempo]"
- "trocar voz [nome]" - mudar voz
- "velocidade voz [0.5-2.0]" - ajustar velocidade"""

        # Abrir programa (com opcao de monitor)
        m = re.match(r"(?:abra|abrir|abre|iniciar|inicia|quero|preciso|pode|pode me)\s+(.+)", text)
        if m:
            resto = m.group(1)
            monitor = self._parse_monitor(resto)
            # Remove a parte do monitor do nome do programa
            nome_limpo = re.sub(r"\s*(?:no|na)\s+(?:\w+\s+)?monitor\s*\d*", "", resto, flags=re.IGNORECASE)
            nome_limpo = re.sub(r"\s*(?:\w+\s+)?monitor\s*\d*", "", nome_limpo, flags=re.IGNORECASE)
            # Remove conectivos comuns no inicio
            nome_limpo = re.sub(r"^(?:o|a|os|as|um|uma|o\s+|a\s+)", "", nome_limpo, flags=re.IGNORECASE)
            return open_program(self._limpar_artigo(nome_limpo.strip()), monitor=monitor)
        m = re.match(r"(?:feche|fechar|fecha|mate|matar|encerrar|encerre|fechar o|fechar a)\s+(.+)", text)
        if m:
            return close_program(self._limpar_artigo(m.group(1)))

        # Desligar/Reiniciar/Suspender
        if re.search(r"(?:desligue|desligar|desliga)", text) and re.search(r"(?:computador|pc|maquina|sistema)", text):
            return desligar_computador()
        if re.search(r"(?:reinicie|reiniciar|reinicia|reboot)", text) and re.search(r"(?:computador|pc|maquina|sistema)", text):
            return reiniciar_computador()
        if re.search(r"(?:suspenda|suspender|hibernar|suspenso|modo\s+suspens)", text):
            return suspender_computador()

        # Monitorar PC - varias formas
        if re.search(r"(?:monitorar|monitora|verificar\s+(?:o\s+)?pc|como\s+(?:esta|estao)\s+(?:o\s+)?(?:pc|computador|desempenho|sistema)|qual\s+(?:o|a|as|os)\s+(?:status|desempenho|situacao|estado)\s+(?:do\s+)?(?:pc|computador)|status\s+(?:do\s+)?pc|desempenho\s+(?:do\s+)?pc)", text):
            return "Permita-me verificar o PC, Senhor.\n" + monitor_pc() + "\n\n" + monitor_pc_fala()

        # Programas abertos - varias formas
        if re.search(r"(?:programas?\s+(?:abertos?|rodando|em\s+execucao|em\s+uso)|quais?\s+(?:os|estao)\s+(?:abertos?|rodando)|o\s+que\s+(?:esta|estao)\s+(?:aberto|rodando|rodando)|lista\s+de\s+programas?|mostrar?\s+programas?)", text):
            return "Aqui esta a lista, Senhor.\n" + list_running() + "\n\n" + list_running_fala()

        # Lembrete
        m = re.match(r"(?:lembre|lembrete|avise|aviso|me\s+avise|me\s+lembre|lembra|avisar)\s+(.+?)\s+(?:em|daqui|daqui a|daqui\s+a)\s+(\d+)\s*(?:minuto|min|hora|h)", text)
        if m:
            texto_lembrete = m.group(1)
            minutos = int(m.group(2))
            if "hora" in text:
                minutos *= 60
            return add_reminder(texto_lembrete, minutos)

        # Listar lembretes
        if re.search(r"(?:lembretes?|avisos?|meus\s+lembretes?|o\s+que\s+(?:tenho|devo)\s+(?:para|pra)\s+fazer|compromissos?)", text):
            return "Aqui estao seus lembretes, Senhor.\n" + list_reminders()

        # Listar arquivos
        m = re.match(r"(?:liste|lista|mostre|mostre|mostrar|ver|verificar)\s+(?:os\s+)?(?:arquivos?|pastas?|o\s+conteudo)\s+(?:em|de|na|do)\s+(.+)", text)
        if m:
            return "Permita-me verificar, Senhor.\n" + list_dir(m.group(1).strip())

        # Criar arquivo
        m = re.match(r"(?:cria|crie|criar|criar\s+um|novo\s+arquivo)\s+(?:um\s+)?arquivo\s+(?:chamado\s+)?(.+?)\s+(?:com|que tenha|contendo|chamado|named|que tenha o conteudo|que tenha o texto|com o conteudo|com o texto)\s+(.+)", text)
        if m:
            return "Criando o arquivo, Senhor.\n" + create_file(m.group(1).strip(), m.group(2).strip())

        # Deletar arquivo
        m = re.match(r"(?:delete|deleta|apague|remova|excluir|exclua|deletar|apagar|remover)\s+(.+)", text)
        if m:
            return "Removendo, Senhor.\n" + delete_file(m.group(1).strip())

        return None

    def _handle_code(self, lang, task):
        prompt = f"Crie um codigo em {lang} que: {task}. Responda APENAS com o codigo entre crases triplas."
        resposta = chat(prompt, modelo=self._get_modelo(), provider=self._provider, api_key=self._get_api_key())
        m = re.search(r"```(?:\w+)?\s*\n(.*?)```", resposta, re.DOTALL)
        if m:
            codigo = m.group(1).strip()
            resultado = run_code(codigo, lang)
            return f"Codigo criado e executado:\n{resultado}"
        return f"Nao consegui gerar o codigo. Resposta:\n{resposta}"

    def _finish(self, text, resp):
        self.historico.append({"role": "user", "content": text})
        self.historico.append({"role": "assistant", "content": resp})
        if len(self.historico) > 20:
            self.historico = self.historico[-20:]
        self.after(0, lambda: self._show_response(resp))

    def _show_response(self, resp):
        if not self.pensando:
            return
        self.after(0, lambda: self.stop_btn.configure(fg_color=RED))
        self.log("jarvis", resp)
        self._set_status("Pronto")

        # Se tem tabela + fala, fala so a parte de texto (ultima linha)
        if "\n+" in resp and resp.count("\n+") >= 1:
            partes = resp.split("\n\n")
            texto_fala = partes[-1] if len(partes) > 1 else ""
            if texto_fala:
                threading.Thread(target=speak, args=(texto_fala, self.vozelecionada, self.velocidade_voz), daemon=True).start()
            else:
                # Tenta pegar apos a ultima tabela
                linhas = resp.split("\n")
                fala_linhas = []
                after_table = False
                for l in linhas:
                    if l.startswith("+"):
                        after_table = True
                        continue
                    if after_table and l.strip():
                        fala_linhas.append(l.strip())
                texto_fala = " ".join(fala_linhas)
                if texto_fala:
                    threading.Thread(target=speak, args=(texto_fala, self.vozelecionada, self.velocidade_voz), daemon=True).start()
        else:
            threading.Thread(target=speak, args=(resp, self.vozelecionada, self.velocidade_voz), daemon=True).start()

    def _atualizar_modelos(self):
        """Busca modelos instalados no Ollama e atualiza o dropdown."""
        combo = self._model_combo
        info_label = self._model_info_label
        def buscar():
            modelos = obter_modelos_ollama()
            self._modelos_info = {m["display"]: m for m in modelos}
            displays = [m["display"] for m in modelos] or ["Nenhum modelo encontrado"]
            try:
                if combo.winfo_exists():
                    self.after(0, lambda: combo.configure(values=displays))
                if modelos and combo.winfo_exists():
                    self.after(0, lambda: self._model_var.set(modelos[0]["display"]))
                    self.after(0, lambda: self._atualizar_info_modelo(modelos[0]["display"]))
            except Exception:
                pass
        threading.Thread(target=buscar, daemon=True).start()

    def _atualizar_info_modelo(self, display):
        """Atualiza label com info do modelo selecionado."""
        try:
            if not self._model_info_label.winfo_exists():
                return
        except Exception:
            return
        info = self._modelos_info.get(display, {})
        if info:
            texto = (f"Modelo: {info['nome']}\n"
                     f"Tamanho: {info['tamanho_gb']} GB\n"
                     f"Parâmetros: {info['parametros']}\n"
                     f"Quantização: {info['quantizacao']}\n"
                     f"Família: {info['familia']}")
        else:
            texto = "Nenhum modelo selecionado"
        self._model_info_label.configure(text=texto)

    def _iniciar_reminders(self):
        callback = lambda texto: self._on_reminder(texto)
        check_reminders(callback)

    def _atualizar_host_ollama(self):
        global OLLAMA_HOST
        host = self._host_entry.get().strip()
        if host:
            OLLAMA_HOST = host

    def _get_api_key(self):
        """Retorna a API key do provider selecionado."""
        if self._provider == "gemini":
            return self._gemini_key
        return None

    def _get_modelo(self):
        """Retorna o modelo correto baseado no provider."""
        if self._provider == "gemini":
            return self._gemini_model
        return self.modelo_ollama

    def _on_provider_change(self):
        """Mostra/esconde configs baseado no provider selecionado."""
        prov = self._provider_var.get()
        if prov == "ollama":
            self._box_ollama.pack(fill="x", pady=(0, 8), after=self._box_ollama.master.winfo_children()[0] if self._box_ollama.master.winfo_children() else None)
            self._box_gemini.pack_forget()
        else:
            self._box_gemini.pack(fill="x", pady=(0, 8), after=self._box_ollama.master.winfo_children()[0] if self._box_ollama.master.winfo_children() else None)
            self._box_ollama.pack_forget()

    def _load_config(self):
        """Carrega configuracoes salvas."""
        try:
            if os.path.exists(self._config_path):
                with open(self._config_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                self.vozelecionada = cfg.get("voz", self.vozelecionada)
                self.velocidade_voz = cfg.get("velocidade", self.velocidade_voz)
                self.modelo_ollama = cfg.get("modelo", self.modelo_ollama)
                self._provider = cfg.get("provider", self._provider)
                self._gemini_key = cfg.get("gemini_key", self._gemini_key)
                self._gemini_model = cfg.get("gemini_model", self._gemini_model)
                self._motor_voz = cfg.get("motor_voz", self._motor_voz)
                self._tema = cfg.get("tema", {})
                # Aplica o motor de voz (ex: gemini) ao modulo de voz global
                configurar_motor_voz(self._motor_voz, self._gemini_key, self._gemini_model)
        except Exception:
            pass

    def _save_config(self):
        """Salva configuracoes atuais."""
        try:
            cfg = {
                "voz": self.vozelecionada,
                "velocidade": self.velocidade_voz,
                "modelo": self.modelo_ollama,
                "provider": self._provider,
                "gemini_key": self._gemini_key,
                "gemini_model": self._gemini_model,
                "motor_voz": self._motor_voz,
                "tema": {
                    "accent": self._tema_cores["accent"].get(),
                    "bg": self._tema_cores["bg"].get(),
                    "panel": self._tema_cores["panel"].get(),
                    "text": self._tema_cores["text"].get(),
                    "intensidade": self._intensidade_slider.get(),
                },
            }
            with open(self._config_path, "w", encoding="utf-8") as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _aplicar_tema(self):
        global BG, PANEL, ACCENT, ACCENT_DIM, TEXT, MUTED, GREEN, RED, ORANGE
        if self._tema:
            BG = self._tema.get("bg", BG)
            PANEL = self._tema.get("panel", PANEL)
            ACCENT = self._tema.get("accent", ACCENT)
            TEXT = self._tema.get("text", TEXT)
            inten = self._tema.get("intensidade", 1.0)
            if inten != 1.0:
                BG = self._ajustar_brilho(BG, inten)
                PANEL = self._ajustar_brilho(PANEL, inten)
                ACCENT = self._ajustar_brilho(ACCENT, inten)
                TEXT = self._ajustar_brilho(TEXT, inten)
            ACCENT_DIM = self._ajustar_brilho(ACCENT, 0.7)
            MUTED = self._ajustar_brilho(TEXT, 0.5)
            GREEN = "#00ff88"
            RED = "#ff4444"
            ORANGE = "#ffaa00"

    @staticmethod
    def _ajustar_brilho(hex_color, fator):
        hex_color = hex_color.lstrip("#")
        if len(hex_color) != 6:
            return "#" + hex_color
        r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        r = min(255, int(r * fator))
        g = min(255, int(g * fator))
        b = min(255, int(b * fator))
        return f"#{r:02x}{g:02x}{b:02x}"

    def _toggle_topmost(self):
        self._topmost = not self._topmost
        self.attributes("-topmost", self._topmost)
        if self._topmost:
            self._topmost_btn.configure(fg_color=ACCENT_DIM, text_color=BG, text="\U0001f513")
        else:
            self._topmost_btn.configure(fg_color="#1a1a3a", text_color=TEXT, text="\U0001f512")

    def _create_tray_image(self):
        if not HAS_TRAY:
            return None
        img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        accent = ACCENT.lstrip("#")
        r, g, b = int(accent[0:2], 16), int(accent[2:4], 16), int(accent[4:6], 16)
        draw.rounded_rectangle([4, 4, 60, 60], radius=12, fill=(r, g, b, 255))
        draw.text((16, 10), "J", fill=(0, 0, 0, 255))
        return img

    def _start_tray(self):
        if not HAS_TRAY or self._tray_icon:
            return
        image = self._create_tray_image()
        if not image:
            return
        menu = pystray.Menu(
            pystray.MenuItem("Abrir Jarvis", self._show_from_tray, default=True),
            pystray.MenuItem("Sair", self._quit_from_tray),
        )
        self._tray_icon = pystray.Icon("Jarvis", image, "Jarvis Assistente", menu)
        threading.Thread(target=self._tray_icon.run, daemon=True).start()

    def _stop_tray(self):
        if self._tray_icon:
            try:
                self._tray_icon.stop()
            except Exception:
                pass
            self._tray_icon = None

    def _show_from_tray(self, icon=None, item=None):
        self.after(0, self._do_show_from_tray)

    def _do_show_from_tray(self):
        self.deiconify()
        self.lift()
        self.focus_force()
        self._stop_tray()

    def _quit_from_tray(self, icon=None, item=None):
        self.after(0, self._do_quit_from_tray)

    def _do_quit_from_tray(self):
        self._stop_tray()
        self._save_config()
        if self.escuta_dinamica and self.escuta_dinamica.ativo:
            self.escuta_dinamica.parar()
        self.destroy()
        import os
        os._exit(0)

    def _on_minimize(self, event):
        if event.state == "iconic":
            self.after(100, self._start_tray)

    def _on_close(self):
        self._do_quit_from_tray()
