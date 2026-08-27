"""
Jarvis - Versao Terminal
Rode com: python terminal.py
"""
import re
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from brain import chat, ver_tela, GEMINI_MODELS
from voice import listen, speak, VOZES, EscutaDinamica, stop_speak
from system_control import open_program, close_program, monitor_pc, monitor_pc_fala, list_running, list_running_fala, desligar_computador, reiniciar_computador, suspender_computador, open_folder, open_file
from file_manager import list_dir, read_file, create_file, delete_file
from web_search import search
from code_runner import run_code
from reminders import add_reminder, list_reminders, check_reminders
from developer import listar_arquivos_codigo, aplicar_modificacao, salvar_arquivo, ler_arquivo

HISTORICO = []
VOZ_ATUAL = "Antonio"
VELOCIDADE = 1.0
escuta_dinamica = None
_provider = "ollama"
_gemini_key = ""
_gemini_model = "gemini-3.6-flash"
_config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")


def _load_config():
    global _provider, _gemini_key, _gemini_model
    try:
        if os.path.exists(_config_path):
            with open(_config_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            _provider = cfg.get("provider", _provider)
            _gemini_key = cfg.get("gemini_key", _gemini_key)
            _gemini_model = cfg.get("gemini_model", _gemini_model)
    except Exception:
        pass


def _get_api_key():
    if _provider == "gemini":
        return _gemini_key
    return None


def _get_model():
    if _provider == "gemini":
        return _gemini_model
    return None


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

    # Abrir pasta
    m = re.match(r"(?:abra|abrir|abre|abra a|abrir a|abra o|abrir o)\s+(?:pasta|diretorio|diretorio)\s+(.+)", text_low)
    if m:
        return open_folder(m.group(1).strip())

    # Abrir arquivo por caminho
    m = re.match(r"(?:abra|abrir|abre)\s+(?:o\s+)?arquivo\s+(.+)", text_low)
    if m:
        return open_file(m.group(1).strip())

    # Ver tela
    if re.search(r"(?:veja|ver|olhe|olha|mostra|mostrar)\s+(?:a\s+)?(?:tela|monitor|display|screen)", text_low):
        return "Permita-me observar a tela, Senhor.\n" + ver_tela(api_key=_get_api_key(), modelo=_get_model())

    # Ajuda / Comandos
    if text_low in ("?", "ajuda", "comandos", "help", "o que voce faz", "o que voce sabe fazer"):
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
    m = re.match(r"(?:abra|abrir|abre|iniciar|inicia|quero|preciso|pode|pode me)\s+(.+)", text_low)
    if m:
        resto = m.group(1)
        monitor = _parse_monitor(resto)
        nome_limpo = re.sub(r"\s*(?:no|na)\s+(?:\w+\s+)?monitor\s*\d*", "", resto, flags=re.IGNORECASE)
        nome_limpo = re.sub(r"\s*(?:\w+\s+)?monitor\s*\d*", "", nome_limpo, flags=re.IGNORECASE)
        nome_limpo = re.sub(r"^(?:o|a|os|as|um|uma|o\s+|a\s+)", "", nome_limpo, flags=re.IGNORECASE)
        return open_program(_limpar_artigo(nome_limpo.strip()), monitor=monitor)

    # Fechar programa
    m = re.match(r"(?:feche|fechar|fecha|mate|matar|encerrar|encerre|fechar o|fechar a)\s+(.+)", text_low)
    if m:
        return close_program(_limpar_artigo(m.group(1)))

    # Desligar/Reiniciar/Suspender
    if re.search(r"(?:desligue|desligar|desliga)", text_low) and re.search(r"(?:computador|pc|maquina|sistema)", text_low):
        return desligar_computador()
    if re.search(r"(?:reinicie|reiniciar|reinicia|reboot)", text_low) and re.search(r"(?:computador|pc|maquina|sistema)", text_low):
        return reiniciar_computador()
    if re.search(r"(?:suspenda|suspender|hibernar|suspenso|modo\s+suspens)", text_low):
        return suspender_computador()

    # Monitorar PC - varias formas
    if re.search(r"(?:monitorar|monitora|verificar\s+(?:o\s+)?pc|como\s+(?:esta|estao)\s+(?:o\s+)?(?:pc|computador|desempenho|sistema)|qual\s+(?:o|a|as|os)\s+(?:status|desempenho|situacao|estado)\s+(?:do\s+)?(?:pc|computador)|status\s+(?:do\s+)?pc|desempenho\s+(?:do\s+)?pc)", text_low):
        return "Permita-me verificar o PC, Senhor.\n" + monitor_pc() + "\n\n" + monitor_pc_fala()

    # Programas abertos - varias formas
    if re.search(r"(?:programas?\s+(?:abertos?|rodando|em\s+execucao|em\s+uso)|quais?\s+(?:os|estao)\s+(?:abertos?|rodando)|o\s+que\s+(?:esta|estao)\s+(?:aberto|rodando|rodando)|lista\s+de\s+programas?|mostrar?\s+programas?)", text_low):
        return "Aqui esta a lista, Senhor.\n" + list_running() + "\n\n" + list_running_fala()

    # Lembrete
    m = re.match(
        r"(?:lembre|lembrete|avise|aviso|me\s+avise|me\s+lembre|lembra|avisar)\s+(.+?)\s+(?:em|daqui|daqui a|daqui\s+a)\s+(\d+)\s*(?:minuto|min|hora|h)",
        text_low,
    )
    if m:
        texto_l = m.group(1)
        mins = int(m.group(2))
        if "hora" in text_low:
            mins *= 60
        return add_reminder(texto_l, mins)

    # Listar lembretes
    if re.search(r"(?:lembretes?|avisos?|meus\s+lembretes?|o\s+que\s+(?:tenho|devo)\s+(?:para|pra)\s+fazer|compromissos?)", text_low):
        return "Aqui estao seus lembretes, Senhor.\n" + list_reminders()

    # Listar arquivos
    m = re.match(r"(?:liste|lista|mostre|mostrar|ver|verificar)\s+(?:os\s+)?(?:arquivos?|pastas?|o\s+conteudo)\s+(?:em|de|na|do)\s+(.+)", text_low)
    if m:
        return "Permita-me verificar, Senhor.\n" + list_dir(m.group(1).strip())

    # Criar arquivo
    m = re.match(r"(?:cria|crie|criar|criar\s+um|novo\s+arquivo)\s+(?:um\s+)?arquivo\s+(.+?)\s+(?:com|que tenha|contendo|chamado|named)\s+(.+)", text_low)
    if m:
        return "Criando o arquivo, Senhor.\n" + create_file(m.group(1).strip(), m.group(2).strip())

    # Deletar arquivo
    m = re.match(r"(?:delete|deleta|apague|remova|excluir|exclua|deletar|apagar|remover)\s+(.+)", text_low)
    if m:
        return "Removendo, Senhor.\n" + delete_file(m.group(1).strip())

    # Trocar voz
    m = re.match(r"(?:troca|trocar|muda|mudar|altera|alterar|coloca|colocar)\s+voz\s+(.+)", text_low)
    if m:
        nome = m.group(1).strip().title()
        if nome in VOZES:
            return f"Voz alterada para {nome}, Senhor."
        return f"Peço desculpas, Senhor, mas a voz '{nome}' nao foi encontrada. Opcoes: {', '.join(VOZES.keys())}"

    # Listar vozes
    if re.search(r"(?:vozes?|listar\s+vozes?|quais\s+(?:as|são)\s+as\s+vozes?|opcoes?\s+de\s+voz)", text_low):
        lista = "\n".join(f"- {nome}: {vid}" for nome, vid in VOZES.items())
        return f"Vozes disponiveis, Senhor:\n{lista}"

    # Velocidade da voz
    m = re.match(r"(?:velocidade|veloc|rapido|lento|devagar|acelerar|desacelerar)\s+(?:da\s+)?voz\s+(\d+\.?\d*)", text_low)
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
        resp = chat(prompt, provider=_provider, api_key=_get_api_key(), modelo=_get_model())
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
        return "Permita-me buscar essa informacao, Senhor.\n" + chat(f"Resuma de forma curta:\n{resultados}", provider=_provider, api_key=_get_api_key(), modelo=_get_model())

    # Geral (IA)
    return chat(texto, HISTORICO, provider=_provider, api_key=_get_api_key(), modelo=_get_model())


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
    _load_config()
    print_colorido(f"Provider: {_provider.upper()}", "amarelo")
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
