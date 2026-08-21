"""
Jarvis - Assistente Pessoal
Ponto de entrada principal. Rode com: python main.py
"""
import sys
import os
import threading

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gui import JarvisApp
from updater import verificar_atualizacoes, aplicar_atualizacao, reiniciar


def _verificar_updates_gui(app):
    """Verifica atualizacoes em background e mostra popup se encontrar."""
    tem_updates, msg = verificar_atualizacoes()
    if not tem_updates:
        return

    def _mostrar_popup():
        import customtkinter as ctk

        popup = ctk.CTkToplevel(app)
        popup.title("Atualizacao Disponivel")
        popup.geometry("380x200")
        popup.configure(fg_color="#1a1a2e")
        popup.grab_set()
        popup.attributes("-topmost", True)

        ctk.CTkLabel(popup, text="Atualizacao Disponivel!",
                     font=ctk.CTkFont(size=16, weight="bold"),
                     text_color="#00cc66").pack(pady=(20, 5))
        ctk.CTkLabel(popup, text=msg,
                     font=ctk.CTkFont(size=12),
                     text_color="#ffffff").pack(pady=(0, 15))

        status_label = ctk.CTkLabel(popup, text="", font=ctk.CTkFont(size=11), text_color="#888888")
        status_label.pack()

        btn_frame = ctk.CTkFrame(popup, fg_color="transparent")
        btn_frame.pack(pady=(10, 15))

        def atualizar():
            btn_update.configure(state="disabled", text="Atualizando...")
            def tarefa():
                ok, msg_r = aplicar_atualizacao()
                app.after(0, lambda: _finalizar(msg_r, ok))
            threading.Thread(target=tarefa, daemon=True).start()

        def _finalizar(msg_r, ok):
            status_label.configure(text=msg_r, text_color="#00cc66" if ok else "#ff4444")
            if ok and "Reinicie" in msg_r:
                btn_restart = ctk.CTkButton(btn_frame, text="Reiniciar Agora",
                                           fg_color="#00cc66", text_color="#ffffff",
                                           font=ctk.CTkFont(size=12, weight="bold"),
                                           command=reiniciar)
                btn_restart.pack(side="left", padx=5)
            btn_close = ctk.CTkButton(btn_frame, text="Depois",
                                      fg_color="#444444", text_color="#ffffff",
                                      font=ctk.CTkFont(size=12),
                                      command=popup.destroy)
            btn_close.pack(side="left", padx=5)

        btn_update = ctk.CTkButton(btn_frame, text="Atualizar Agora",
                                   fg_color="#00cc66", text_color="#ffffff",
                                   font=ctk.CTkFont(size=12, weight="bold"),
                                   command=atualizar)
        btn_update.pack(side="left", padx=5)

        btn_skip = ctk.CTkButton(btn_frame, text="Pular",
                                 fg_color="#444444", text_color="#ffffff",
                                 font=ctk.CTkFont(size=12),
                                 command=popup.destroy)
        btn_skip.pack(side="left", padx=5)

    app.after(15000, _mostrar_popup)


def main():
    print("[Jarvis] Iniciando...")
    app = JarvisApp()
    threading.Thread(target=_verificar_updates_gui, args=(app,), daemon=True).start()
    app.mainloop()


if __name__ == "__main__":
    main()
