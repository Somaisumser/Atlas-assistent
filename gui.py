import functools
import customtkinter as ctk
import threading
import re
import os
import requests
import json
from datetime import datetime
import unicodedata


def _strip_ansi(texto):
    """Remove codigos ANSI de cores para exibicao na GUI."""
    return re.sub(r'\033\[[0-9;]*m', '', texto)

from brain import chat
from voice import listen, speak, stop_speak, VOZES, EscutaDinamica
from system_control import open_program, close_program, monitor_pc, list_running
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
        self._config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
        self._load_config()
        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(100, self._iniciar_reminders)
        self.log("Jarvis", "Aos seus servicos, Senhor. Como posso ajuda-lo?")

    def _build_ui(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(15, 5))
        title_box = ctk.CTkFrame(header, fg_color="transparent")
        title_box.pack(side="left")
        ctk.CTkLabel(title_box, text="JARVIS", font=ctk.CTkFont(size=28, weight="bold"), text_color=ACCENT).pack(anchor="w")
        ctk.CTkLabel(title_box, text="assistente pessoal", font=ctk.CTkFont(size=11), text_color=MUTED).pack(anchor="w")
        ctk.CTkButton(header, text="\u2699", width=40, height=32, corner_radius=10, fg_color=PANEL, hover_color="#1a1a3a", text_color=TEXT, font=ctk.CTkFont(size=16), command=self._open_settings).pack(side="right")

        self.status = ctk.CTkLabel(self, text="Pronto", font=ctk.CTkFont(size=12), text_color=MUTED)
        self.status.pack(anchor="w", padx=20)

        self.chat = ctk.CTkTextbox(self, fg_color=PANEL, text_color=TEXT, font=ctk.CTkFont(size=13), wrap="word", border_width=1, border_color="#1a1a3a", corner_radius=12)
        self.chat.pack(padx=20, pady=10, fill="both", expand=True)
        self.chat.configure(state="disabled")

        input_frame = ctk.CTkFrame(self, fg_color="transparent")
        input_frame.pack(fill="x", padx=20, pady=(0, 10))
        self.entry = ctk.CTkEntry(input_frame, placeholder_text="Digite seu comando...", height=42, corner_radius=12, fg_color=PANEL, border_color="#1a1a3a", text_color=TEXT, font=ctk.CTkFont(size=13))
        self.entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.entry.bind("<Return>", lambda e: self._send())
        ctk.CTkButton(input_frame, text="Enviar", width=70, height=42, corner_radius=12, fg_color=ACCENT_DIM, hover_color=ACCENT, text_color=BG, font=ctk.CTkFont(size=13, weight="bold"), command=self._send).pack(side="left", padx=(0, 8))
        self.mic_btn = ctk.CTkButton(input_frame, text="Mic", width=55, height=42, corner_radius=12, fg_color="#2a2a4a", hover_color="#3a3a5a", text_color=TEXT, command=self._toggle_mic)
        self.mic_btn.pack(side="left", padx=(0, 8))
        self.stop_btn = ctk.CTkButton(input_frame, text="Parar", width=60, height=42, corner_radius=12, fg_color=RED, hover_color="#cc3333", text_color=TEXT, font=ctk.CTkFont(size=12, weight="bold"), command=self._stop_all)
        self.stop_btn.pack(side="left")
        self.listen_btn = ctk.CTkButton(input_frame, text="Escuta: OFF", width=80, height=42, corner_radius=12, fg_color="#1a1a3a", hover_color="#2a2a4a", text_color=MUTED, font=ctk.CTkFont(size=11), command=self._toggle_escuta_dinamica)
        self.listen_btn.pack(side="left", padx=(8, 0))
        quick = ctk.CTkFrame(self, fg_color="transparent")
        quick.pack(fill="x", padx=20, pady=(0, 15))
        for texto, cmd in [("Monitorar PC", lambda: self._cmd_direct("monitorar pc")), ("Programas abertos", lambda: self._cmd_direct("programas abertos")), ("Lembretes", lambda: self._cmd_direct("lembretes"))]:
            ctk.CTkButton(quick, text=texto, height=30, corner_radius=8, fg_color="#1a1a3a", hover_color="#2a2a4a", text_color=TEXT, font=ctk.CTkFont(size=11), command=cmd).pack(side="left", padx=(0, 4), expand=True, fill="x")
        quick2 = ctk.CTkFrame(self, fg_color="transparent")
        quick2.pack(fill="x", padx=20, pady=(0, 15))
        for texto, cmd in [("Pesquisar", self._abrir_pesquisa), ("Codigo", self._abrir_codigo), ("Arquivos", self._abrir_arquivos), ("Dev", self._abrir_dev)]:
            ctk.CTkButton(quick2, text=texto, height=30, corner_radius=8, fg_color="#1a1a3a", hover_color="#2a2a4a", text_color=TEXT, font=ctk.CTkFont(size=11), command=cmd).pack(side="left", padx=(0, 4), expand=True, fill="x")

    def _open_settings(self):
        win = ctk.CTkToplevel(self)
        win.title("Configuracoes")
        win.geometry("420x520")
        win.configure(fg_color=BG)
        win.grab_set()
        tab = ctk.CTkTabview(win, fg_color=PANEL, segmented_button_fg_color=BG, segmented_button_selected_color=ACCENT, segmented_button_unselected_color=PANEL, text_color=TEXT, corner_radius=10)
        tab.pack(padx=15, pady=15, fill="both", expand=True)

        aba_voz = tab.add("Voz")
        ctk.CTkLabel(aba_voz, text="Voz do Jarvis", font=ctk.CTkFont(size=14, weight="bold"), text_color=TEXT).pack(anchor="w", pady=(5, 10))
        self._voice_var = ctk.StringVar(value=self.vozelecionada)
        for nome, voz_id in VOZES.items():
            ctk.CTkRadioButton(aba_voz, text=f"{nome} ({voz_id})", variable=self._voice_var, value=nome, text_color=TEXT, fg_color=ACCENT, hover_color=ACCENT_DIM, font=ctk.CTkFont(size=12)).pack(anchor="w", pady=2)
        ctk.CTkLabel(aba_voz, text="Velocidade da voz:", text_color=MUTED, font=ctk.CTkFont(size=11)).pack(anchor="w", pady=(15, 5))
        self._speed_slider = ctk.CTkSlider(aba_voz, from_=0.5, to=2.0, number_of_steps=15, width=280, fg_color=PANEL, progress_color=ACCENT, button_color=ACCENT, button_hover_color=ACCENT_DIM)
        self._speed_slider.set(self.velocidade_voz)
        self._speed_slider.pack(anchor="w")
        self._speed_label = ctk.CTkLabel(aba_voz, text=f"Velocidade: {self.velocidade_voz:.1f}x", text_color=TEXT, font=ctk.CTkFont(size=11))
        self._speed_label.pack(anchor="w")
        self._speed_slider.configure(command=lambda v: self._speed_label.configure(text=f"Velocidade: {v:.1f}x"))
        ctk.CTkButton(aba_voz, text="Testar voz", fg_color="#2a2a4a", hover_color="#3a3a5a", text_color=TEXT, command=lambda: threading.Thread(target=speak, args=("Teste de voz.", self._voice_var.get(), self._speed_slider.get()), daemon=True).start()).pack(pady=(15, 0))

        aba_config = tab.add("Config")
        ctk.CTkLabel(aba_config, text="Configuracoes gerais", font=ctk.CTkFont(size=14, weight="bold"), text_color=TEXT).pack(anchor="w", pady=(5, 10))

        ctk.CTkLabel(aba_config, text="Modelo Ollama:", text_color=MUTED, font=ctk.CTkFont(size=11)).pack(anchor="w")

        self._model_var = ctk.StringVar(value="llama3.2")
        self._modelos_info = {}

        model_frame = ctk.CTkFrame(aba_config, fg_color="transparent")
        model_frame.pack(fill="x", pady=(0, 10))

        self._model_combo = ctk.CTkOptionMenu(
            model_frame, values=["Carregando..."], variable=self._model_var,
            fg_color=PANEL, button_color="#1a1a3a", button_hover_color=ACCENT, text_color=TEXT,
            width=260, font=ctk.CTkFont(size=11)
        )
        self._model_combo.pack(side="left", fill="x", expand=True)

        ctk.CTkButton(
            model_frame, text="🔄", width=30, height=28, corner_radius=6,
            fg_color="#2a2a4a", hover_color="#3a3a5a", text_color=TEXT,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._atualizar_modelos
        ).pack(side="left", padx=(5, 0))

        self._model_info_label = ctk.CTkLabel(
            aba_config, text="", text_color=MUTED, font=ctk.CTkFont(size=10), justify="left"
        )
        self._model_info_label.pack(anchor="w", pady=(5, 10))

        self._model_combo.configure(command=lambda v: self._atualizar_info_modelo(v))

        ctk.CTkLabel(aba_config, text="Host Ollama:", text_color=MUTED, font=ctk.CTkFont(size=11)).pack(anchor="w")
        self._host_entry = ctk.CTkEntry(aba_config, fg_color=PANEL, border_color="#1a1a3a", text_color=TEXT, placeholder_text="http://localhost:11434")
        self._host_entry.pack(fill="x", pady=(0, 10))

        self.after(100, self._atualizar_modelos)

        aba_sobre = tab.add("Sobre")
        ctk.CTkLabel(aba_sobre, text="Jarvis - Assistente Pessoal", font=ctk.CTkFont(size=16, weight="bold"), text_color=ACCENT).pack(pady=(20, 10))
        ctk.CTkLabel(aba_sobre, text="Assistente virtual local e gratuito.\nUsa Ollama como cerebro.\nVozes neurais da Microsoft.\n\nFuncionalidades:\n- Abrir/fechar programas\n- Criar e rodar codigo\n- Pesquisar na internet\n- Monitorar o PC\n- Gerenciar arquivos\n- Lembretes\n- Escuta dinamica\n- Modo desenvolvedor", text_color=TEXT, font=ctk.CTkFont(size=12), justify="left").pack(anchor="w", padx=15)

        def salvar():
            self.vozelecionada = self._voice_var.get()
            self.velocidade_voz = self._speed_slider.get()
            display = self._model_var.get()
            info = self._modelos_info.get(display, {})
            self.modelo_ollama = info.get("nome", "llama3.2")
            self._atualizar_host_ollama()
            win.destroy()
        ctk.CTkButton(win, text="Salvar", fg_color=ACCENT_DIM, hover_color=ACCENT, text_color=BG, font=ctk.CTkFont(size=13, weight="bold"), command=salvar).pack(pady=(0, 15), padx=15, fill="x")

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
                novo, diff, original = aplicar_modificacao(arquivo, desc)
                if novo and diff:
                    self.after(0, lambda: _mostrar_resultado(diff, novo, arquivo))
                else:
                    erro = diff if diff else "Nao consegui gerar a modificacao.\nVerifique se o Ollama esta rodando."
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
        self.chat.configure(state="normal")
        prefix = "Voce" if sender == "user" else "Jarvis"
        text_limpo = _strip_ansi(text)
        self.chat.insert("end", f"{prefix}: {text_limpo}\n\n")
        self.chat.configure(state="disabled")
        self.chat.see("end")

    def _set_status(self, text, color=None):
        self.status.configure(text=text, text_color=color or MUTED)

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
            resp = chat(f"Resuma de forma curta:\n{resultados}", modelo=self.modelo_ollama)
            self._finish(text, resp)
            return
        if not self.pensando:
            return
        self._set_status("Pensando...")
        resp = chat(text, self.historico, modelo=self.modelo_ollama)
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
        # Abrir programa (com opcao de monitor)
        m = re.match(r"(?:abra|abrir|abre|iniciar|inicia)\s+(.+)", text)
        if m:
            resto = m.group(1)
            monitor = self._parse_monitor(resto)
            # Remove a parte do monitor do nome do programa
            nome_limpo = re.sub(r"\s*(?:no|na)\s+(?:\w+\s+)?monitor\s*\d*", "", resto, flags=re.IGNORECASE)
            nome_limpo = re.sub(r"\s*(?:\w+\s+)?monitor\s*\d*", "", nome_limpo, flags=re.IGNORECASE)
            return open_program(self._limpar_artigo(nome_limpo.strip()), monitor=monitor)
        m = re.match(r"(?:feche|fechar|fecha|mate|matar)\s+(.+)", text)
        if m:
            return close_program(self._limpar_artigo(m.group(1)))
        if "monitor" in text or "status" in text or "desempenho" in text:
            return "Permita-me verificar o PC, Senhor.\n" + monitor_pc()
        if "programas" in text and ("aberto" in text or "rodando" in text):
            return "Aqui esta a lista, Senhor.\n" + list_running()
        m = re.match(r"(?:lembre|lembrete|avise|aviso)\s+(.+?)\s+(?:em|daqui|daqui a)\s+(\d+)\s*(?:minuto|min|hora|h)", text)
        if m:
            texto_lembrete = m.group(1)
            minutos = int(m.group(2))
            if "hora" in text:
                minutos *= 60
            return add_reminder(texto_lembrete, minutos)
        if "lembretes" in text:
            return "Aqui estao seus lembretes, Senhor.\n" + list_reminders()
        m = re.match(r"(?:liste|lista|mostre)\s+(?:os\s+)?(?:arquivos?|pastas?)\s+(?:em|de|na)\s+(.+)", text)
        if m:
            return "Permita-me verificar, Senhor.\n" + list_dir(m.group(1).strip())
        m = re.match(r"(?:cria|crie)\s+(?:um\s+)?arquivo\s+(.+?)\s+(?:com|que tenha|contendo)\s+(.+)", text)
        if m:
            return "Criando o arquivo, Senhor.\n" + create_file(m.group(1).strip(), m.group(2).strip())
        m = re.match(r"(?:delete|deleta|apague|remova)\s+(.+)", text)
        if m:
            return "Removendo, Senhor.\n" + delete_file(m.group(1).strip())
        return None

    def _handle_code(self, lang, task):
        prompt = f"Crie um codigo em {lang} que: {task}. Responda APENAS com o codigo entre crases triplas."
        resposta = chat(prompt, modelo=self.modelo_ollama)
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
        threading.Thread(target=speak, args=(resp, self.vozelecionada, self.velocidade_voz), daemon=True).start()

    def _atualizar_modelos(self):
        """Busca modelos instalados no Ollama e atualiza o dropdown."""
        def buscar():
            modelos = obter_modelos_ollama()
            self._modelos_info = {m["display"]: m for m in modelos}
            displays = [m["display"] for m in modelos] or ["Nenhum modelo encontrado"]
            self.after(0, lambda: self._model_combo.configure(values=displays))
            if modelos:
                self.after(0, lambda: self._model_var.set(modelos[0]["display"]))
                self.after(0, lambda: self._atualizar_info_modelo(modelos[0]["display"]))
        threading.Thread(target=buscar, daemon=True).start()

    def _atualizar_info_modelo(self, display):
        """Atualiza label com info do modelo selecionado."""
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

    def _load_config(self):
        """Carrega configuracoes salvas."""
        try:
            if os.path.exists(self._config_path):
                with open(self._config_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                self.vozelecionada = cfg.get("voz", self.vozelecionada)
                self.velocidade_voz = cfg.get("velocidade", self.velocidade_voz)
                self.modelo_ollama = cfg.get("modelo", self.modelo_ollama)
        except Exception:
            pass

    def _save_config(self):
        """Salva configuracoes atuais."""
        try:
            cfg = {
                "voz": self.vozelecionada,
                "velocidade": self.velocidade_voz,
                "modelo": self.modelo_ollama,
            }
            with open(self._config_path, "w", encoding="utf-8") as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _on_close(self):
        """Salva config e fecha o Jarvis."""
        self._save_config()
        if self.escuta_dinamica and self.escuta_dinamica.ativo:
            self.escuta_dinamica.parar()
        self.destroy()
