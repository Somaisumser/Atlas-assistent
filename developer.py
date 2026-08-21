"""
Jarvis - Modo Desenvolvedor
Permite modificar o codigo fonte do Jarvis com aprovacao do usuario.
"""
import os
import re
import difflib
import shutil
from datetime import datetime
from brain import chat

JARVIS_DIR = os.path.dirname(os.path.abspath(__file__))
BACKUP_DIR = os.path.join(JARVIS_DIR, "backups")


def _garantir_backup_dir():
    os.makedirs(BACKUP_DIR, exist_ok=True)


def criar_backup(nome_arquivo):
    """Cria um backup antes de modificar."""
    _garantir_backup_dir()
    caminho = os.path.join(JARVIS_DIR, nome_arquivo)
    if not os.path.exists(caminho):
        return None
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    nome_backup = f"{nome_arquivo}.{timestamp}.bak"
    caminho_backup = os.path.join(BACKUP_DIR, nome_backup)
    shutil.copy2(caminho, caminho_backup)
    return caminho_backup


def listar_backups():
    """Lista backups disponiveis."""
    _garantir_backup_dir()
    return [f for f in os.listdir(BACKUP_DIR) if f.endswith(".bak")]


def restaurar_backup(nome_backup):
    """Restaura um backup."""
    caminho_backup = os.path.join(BACKUP_DIR, nome_backup)
    if not os.path.exists(caminho_backup):
        return "Backup nao encontrado."
    nome_original = nome_backup.rsplit(".", 2)[0]
    caminho_original = os.path.join(JARVIS_DIR, nome_original)
    shutil.copy2(caminho_backup, caminho_original)
    return f"Arquivo '{nome_original}' restaurado com sucesso."


def listar_arquivos_codigo():
    """Lista os arquivos Python do Jarvis."""
    arquivos = []
    for f in os.listdir(JARVIS_DIR):
        if f.endswith(".py"):
            arquivos.append(f)
    return sorted(arquivos)


def ler_arquivo(nome_arquivo):
    """Le o conteudo de um arquivo do Jarvis."""
    caminho = os.path.join(JARVIS_DIR, nome_arquivo)
    if not os.path.exists(caminho):
        return None, f"Arquivo '{nome_arquivo}' nao encontrado."
    with open(caminho, "r", encoding="utf-8") as f:
        conteudo = f.read()
    return conteudo, None


def salvar_arquivo(nome_arquivo, conteudo):
    """Salva o conteudo em um arquivo do Jarvis COM backup."""
    if not conteudo or not conteudo.strip():
        return "Erro: conteudo vazio nao pode ser salvo."
    criar_backup(nome_arquivo)
    caminho = os.path.join(JARVIS_DIR, nome_arquivo)
    with open(caminho, "w", encoding="utf-8") as f:
        f.write(conteudo)
    return f"Arquivo '{nome_arquivo}' salvo com sucesso. Backup criado."


def validar_modificacao(conteudo_original, novo_conteudo):
    """Verifica se a modificacao parece valida."""
    linhas_orig = len(conteudo_original.splitlines())
    linhas_nova = len(novo_conteudo.splitlines())

    if linhas_nova < linhas_orig * 0.3:
        return False, f"ATENCAO: Arquivo original tem {linhas_orig} linhas, novo tem {linhas_nova}. Parece que o codigo foi deletado!"

    if linhas_nova > linhas_orig * 2:
        return False, f"ATENCAO: Arquivo original tem {linhas_orig} linhas, novo tem {linhas_nova}. Parece codigo duplicado!"

    return True, "OK"


def gerar_diff(original, novo, nome_arquivo):
    """Gera um diff visual entre o codigo original e o novo."""
    orig_linhas = original.splitlines(keepends=True)
    novas_linhas = novo.splitlines(keepends=True)
    diff = difflib.unified_diff(
        orig_linhas, novas_linhas,
        fromfile=f"original/{nome_arquivo}",
        tofile=f"novo/{nome_arquivo}",
        lineterm=""
    )
    return "".join(diff)


def _extrair_codigo_completo(resposta, num_linhas_esperado):
    """Extrai o codigo do resposta, tentando varios padroes."""
    # Tenta padrao principal
    m = re.search(r"```(?:python)?\s*\n(.*?)```", resposta, re.DOTALL)
    if m:
        codigo = m.group(1).strip()
        # Verifica se tem numero razoavel de linhas
        linhas = len(codigo.splitlines())
        if linhas >= num_linhas_esperado * 0.3:
            return codigo

    # Tenta sem crases (ultima tentativa)
    if "def " in resposta or "class " in resposta or "import " in resposta:
        return resposta.strip()

    return None


def sugerir_modificacao(nome_arquivo, descricao, conteudo_atual):
    """Usa Ollama para sugerir uma modificacao no codigo."""
    num_linhas = len(conteudo_atual.splitlines())

    prompt = f"""Voce e um programador Python expert. Modifique o codigo abaixo conforme a descricao.

CODIGO ATUAL ({num_linhas} linhas):
```python
{conteudo_atual}
```

DESCRICAO DA MUDANCA:
{descricao}

REGRAS OBRIGATORIAS:
1. Retorne o ARQUIVO COMPLETO modificado (todas as {num_linhas} linhas aproximadamente)
2. NAO retorne apenas a funcao modificada - RETORNE O ARQUIVO INTEIRO
3. Nao remova funcoes, classes ou imports existentes
4. Nao mude nada alem do que foi pedido
5. Mantenha a identacao e estilo do codigo original
6. Responda APENAS com o codigo entre crases triplas

IMPORTANTE: O resultado deve ser o ARQUIVO INTEIRO COM TODAS AS FUNCOES!

Codigo modificado:"""

    resposta = chat(prompt)
    return _extrair_codigo_completo(resposta, num_linhas)


def aplicar_modificacao(nome_arquivo, descricao):
    """Fluxo completo: ler, sugerir, validar, mostrar diff."""
    conteudo, erro = ler_arquivo(nome_arquivo)
    if erro:
        return None, erro, None

    novo_conteudo = sugerir_modificacao(nome_arquivo, descricao, conteudo)
    if not novo_conteudo:
        return None, "Nao consegui gerar a modificacao. Verifique se o Ollama esta rodando.", None

    valido, msg_validacao = validar_modificacao(conteudo, novo_conteudo)
    if not valido:
        return None, msg_validacao, None

    diff = gerar_diff(conteudo, novo_conteudo, nome_arquivo)

    if not diff.strip():
        return None, "Nenhuma alteracao detectada no codigo.", None

    return novo_conteudo, diff, conteudo