"""
Jarvis - Assistente Pessoal
Ponto de entrada principal. Rode com: python main.py
"""
import sys
import os

# Garante que os imports funcionem
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gui import JarvisApp


def main():
    print("[Jarvis] Iniciando...")
    print("[Jarvis] Certifique-se que o Ollama esta rodando: ollama serve")
    app = JarvisApp()
    app.mainloop()


if __name__ == "__main__":
    main()
