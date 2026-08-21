"""
Jarvis - Versao Terminal
Rode com: python terminal.py
"""
import re
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from brain import chat
from voice import listen, speak, VOZES, EscutaDinamica, stop_speak
from system_control import open_program, close_program, monitor_pc, list_running
from file_manager import list_dir, read_file, create_file, delete_file
from web_search import search
from code_runner import run_code
from reminders import add_reminder, list_reminders, check_reminders
from developer import listar_arquivos_codigo, aplicar_modificacao, salvar_arquivo, ler_arquivo

HISTORICO = []
VOZ_ATUAL = "Antonio"
VELOCIDADE = 1.0
escuta_dinamica = None


def _limpar_artigo(texto):
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


def _parse_monitor(texto):
    """Extrai numero do monitor de um texto."""
    texto = texto.lower()
    mapa_numeros = {
        "primeiro": 1, "um": 1, "1": 1, "1o": 1,
        "segundo": 2, "dois": 2, "2": 2, "2o": 2,
        "terceiro": 3, "tres": 3, "3": 3, "3o": 3,
        "quarto": 4, "quatro": 4, "4": 4, "4o": 4,
        "quinto": 5, "cinco": 5, "5": 5, "5o": 5,
    }
    m = re.search(r"monitor\s+(\d+)", texto)
    if m:
        return int(m.group(1))
    for palavra, num in mapa_numeros.items():
        if f"monitor" in texto and palavra in texto:
            return num
        if f"{palavra} monitor" in texto:
            return num
    return None


def on_dynamic_voice(texto):
    print_colorido(f"\n[Jarvis ouviu]: {texto}", "azul")
    HISTORICO.append({"role": "user", "content": texto})
    resp = processar(texto)
    HISTORICO.append({"role": "assistant", "content": resp})
    print_colorido(f"\nJarvis: {resp}", "verde")
    speak(resp, VOZ_ATUAL, VELOCIDADE)


def print_colorido(texto, cor="branco"):
    cores = {
        "azul": "\033[94m",
        "verde": "\033[92m",
        "vermelho": "\033[91m",
        "amarelo": "\033[93m",
        "ciano": "\033[96m",
        "branco": "\033[0m",
        "negrito": "\033[1m",
    }
    print(f"{cores.get(cor, '')}{texto}\033[0m")


def processar(texto):
    text_low = texto.lower().strip()

    # Abrir programa (com opcao de monitor)
    m = re.match(r"(?:abra|abrir|abre|iniciar|inicia)\s+(.+)", text_low)
    if m:
        resto = m.group(1)
        monitor = _parse_monitor(resto)
        nome_limpo = re.sub(r"\s*(?:no|na)\s+(?:\w+\s+)?monitor\s*\d*", "", resto, flags=re.IGNORECASE)
        nome_limpo = re.sub(r"\s*(?:\w+\s+)?monitor\s*\d*", "", nome_limpo, flags=re.IGNORECASE)
        return open_program(_limpar_artigo(nome_limpo.strip()), monitor=monitor)

    # Fechar programa
    m = re.match(r"(?:feche|fechar|fecha|mate|matar)\s+(.+)", text_low)
    if m:
        return close_program(_limpar_artigo(m.group(1)))

    # Monitorar PC
    if "monitor" in text_low or "status" in text_low or "desempenho" in text_low:
        return "Permita-me verificar o PC, Senhor.\n" + monitor_pc()

    # Programas abertos
    if "programas" in text_low and ("aberto" in text_low or "rodando" in text_low):
        return "Aqui esta a lista, Senhor.\n" + list_running()

    # Lembrete
    m = re.match(
        r"(?:lembre|lembrete|avise|aviso)\s+(.+?)\s+(?:em|daqui|daqui a)\s+(\d+)\s*(?:minuto|min|hora|h)",
        text_low,
    )
    if m:
        texto_l = m.group(1)
        mins = int(m.group(2))
        if "hora" in text_low:
            mins *= 60
        return add_reminder(texto_l, mins)

    # Listar lembretes
    if "lembretes" in text_low:
        return "Aqui estao seus lembretes, Senhor.\n" + list_reminders()

    # Listar arquivos
    m = re.match(r"(?:liste|lista|mostre)\s+(?:os\s+)?(?:arquivos?|pastas?)\s+(?:em|de|na)\s+(.+)", text_low)
    if m:
        return "Permita-me verificar, Senhor.\n" + list_dir(m.group(1).strip())

    # Criar arquivo
    m = re.match(r"(?:cria|crie)\s+(?:um\s+)?arquivo\s+(.+?)\s+(?:com|que tenha|contendo)\s+(.+)", text_low)
    if m:
        return "Criando o arquivo, Senhor.\n" + create_file(m.group(1).strip(), m.group(2).strip())

    # Deletar arquivo
    m = re.match(r"(?:delete|deleta|apague|remova)\s+(.+)", text_low)
    if m:
        return "Removendo, Senhor.\n" + delete_file(m.group(1).strip())

    # Trocar voz
    m = re.match(r"(?:troca|trocar|muda|mudar)\s+voz\s+(.+)", text_low)
    if m:
        nome = m.group(1).strip().title()
        if nome in VOZES:
            return f"Voz alterada para {nome}, Senhor."
        return f"Peço desculpas, Senhor, mas a voz '{nome}' nao foi encontrada. Opcoes: {', '.join(VOZES.keys())}"

    # Listar vozes
    if "vozes" in text_low or "listar vozes" in text_low:
        lista = "\n".join(f"- {nome}: {vid}" for nome, vid in VOZES.items())
        return f"Vozes disponiveis, Senhor:\n{lista}"

    # Velocidade da voz
    m = re.match(r"(?:velocidade|veloc|rapido|lento|devagar)\s+(?:da\s+)?voz\s+(\d+\.?\d*)", text_low)
    if m:
        vel = float(m.group(1))
        if 0.5 <= vel <= 2.0:
            return f"Velocidade ajustada para {vel}x, Senhor."
        return "A velocidade deve ser entre 0.5 e 2.0, Senhor."

    if "velocidade" in text_low and "voz" in text_low:
        return f"Velocidade atual: {VELOCIDADE}x, Senhor. Use 'velocidade voz 1.5' para alterar (0.5 a 2.0)."

    # Listar arquivos codigo
    if "arquivos codigo" in text_low or "listar arquivos codigo" in text_low:
        arquivos = listar_arquivos_codigo()
        return "Arquivos do Jarvis, Senhor:\n" + "\n".join(f"  - {a}" for a in arquivos)

    # Ler arquivo codigo
    m = re.match(r"(?:leia|leer|mostrar|ver)\s+(?:o\s+)?arquivo\s+(.+)", text_low)
    if m:
        nome = m.group(1).strip()
        conteudo, erro = ler_arquivo(nome)
        if erro:
            return erro
        return f"--- {nome} ---\n{conteudo}\n--- fim ---"

    # Modificar arquivo
    m = re.match(r"(?:modifique|modificar|altere|alterar|mude|mudar)\s+(.+?)\s+(?:para|que|adicionando|removendo|com)\s+(.+)", text_low)
    if m:
        arquivo = m.group(1).strip()
        desc = m.group(2).strip()
        return f"Use a GUI (botao Dev) para ver o diff e aprovar a mudanca em '{arquivo}'."

    # Codigo
    code_match = re.match(
        r"(?:cria|crie|escreva|fa[cç]a)\s+(?:um\s+)?(?:codigo|programa|script)\s+"
        r"(?:em\s+)?(python|java|c)\s+(?:para|pra|que)\s+(.+)",
        text_low,
    )
    if code_match:
        lang = code_match.group(1)
        task = code_match.group(2)
        prompt = f"Crie um codigo em {lang} que: {task}. Responda APENAS com o codigo entre crases triplas."
        resp = chat(prompt)
        m_code = re.search(r"```(?:\w+)?\s*\n(.*?)```", resp, re.DOTALL)
        if m_code:
            resultado = run_code(m_code.group(1).strip(), lang)
            return f"Como o Senhor desejar. Segue o codigo:\n{resultado}"
        return f"Peço desculpas, Senhor, mas nao consegui gerar o codigo."

    # Pesquisa
    search_match = re.match(
        r"(?:pesquisa|pesquise|procure|busque)\s+(?:na\s+internet\s+)?(?:por\s+|sobre\s+)?(.+)",
        text_low,
    )
    if search_match:
        query = search_match.group(1)
        resultados = search(query)
        return "Permita-me buscar essa informacao, Senhor.\n" + chat(f"Resuma de forma curta:\n{resultados}")

    # Geral (IA)
    return chat(texto, HISTORICO)


def main():
    print_colorido("=" * 55, "ciano")
    print_colorido("  JARVIS - Mordomo Virtual Pessoal", "negrito")
    print_colorido("  Comandos:", "ciano")
    print_colorido("  'falar' - voz unica | 'escuta on' - escuta dinamica", "ciano")
    print_colorido("  'trocar voz [nome]' | 'velocidade voz 1.5'", "ciano")
    print_colorido("  'arquivos codigo' - ver arquivos do Jarvis", "ciano")
    print_colorido("  'leia arquivo gui.py' - ver codigo fonte", "ciano")
    print_colorido("  'parar' - interromper | 'sair' - fechar", "ciano")
    print_colorido("=" * 55, "ciano")
    print_colorido("Jarvis: Aos seus servicos, Senhor. Como posso ajuda-lo?", "verde")

    global escuta_dinamica
    check_reminders(lambda msg: print_colorido(f"\n[Lembrete] {msg}", "amarelo"))

    while True:
        try:
            texto = input("\n\033[96mVoce: \033[0m").strip()
        except (EOFError, KeyboardInterrupt):
            print_colorido("\nAte logo!", "ciano")
            break

        if not texto:
            continue
        if texto.lower() in ("sair", "exit", "quit"):
            if escuta_dinamica:
                escuta_dinamica.parar()
            print_colorido("Ate logo!", "ciano")
            break
        if texto.lower() in ("parar", "stop"):
            stop_speak()
            print_colorido("Interrompido.", "vermelho")
            continue
        if texto.lower() in ("escuta on", "ligar escuta", "escuta ligar"):
            escuta_dinamica = EscutaDinamica(callback=on_dynamic_voice)
            escuta_dinamica.iniciar()
            print_colorido("Escuta dinamica LIGADA. Diga 'Jarvis' para ativar.", "verde")
            continue
        if texto.lower() in ("escuta off", "desligar escuta", "escuta desligar"):
            if escuta_dinamica:
                escuta_dinamica.parar()
                escuta_dinamica = None
            print_colorido("Escuta dinamica DESLIGADA.", "vermelho")
            continue
        if texto.lower() == "falar":
            print_colorido("Ouvindo...", "verde")
            texto = listen()
            if not texto:
                print_colorido("Nao entendi.", "vermelho")
                continue
            print_colorido(f"Voce (voz): {texto}", "azul")

        HISTORICO.append({"role": "user", "content": texto})
        resp = processar(texto)

        # Atualizar voz se comando de troca
        m = re.match(r"(?:troca|trocar|muda|mudar)\s+voz\s+(.+)", texto.lower().strip())
        if m:
            nome = m.group(1).strip().title()
            if nome in VOZES:
                VOZ_ATUAL = nome

        # Atualizar velocidade
        m = re.match(r"(?:velocidade|veloc|rapido|lento|devagar)\s+(?:da\s+)?voz\s+(\d+\.?\d*)", texto.lower().strip())
        if m:
            vel = float(m.group(1))
            if 0.5 <= vel <= 2.0:
                VELOCIDADE = vel

        HISTORICO.append({"role": "assistant", "content": resp})

        print_colorido(f"\nJarvis: {resp}", "verde")
        speak(resp, VOZ_ATUAL, VELOCIDADE)


if __name__ == "__main__":
    main()
