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

    # Verifica se tem funcoes originais no novo codigo
    funcoes_orig = set()
    for l in conteudo_original.splitlines():
        m = re.match(r'\s*(?:def|class)\s+(\w+)', l)
        if m:
            funcoes_orig.add(m.group(1))

    funcoes_nova = set()
    for l in novo_conteudo.splitlines():
        m = re.match(r'\s*(?:def|class)\s+(\w+)', l)
        if m:
            funcoes_nova.add(m.group(1))

    funcoes_faltando = funcoes_orig - funcoes_nova
    if funcoes_faltando:
        return False, f"ATENCAO: Funcoes/Classes faltando no codigo novo: {', '.join(funcoes_faltando)}"

    if linhas_nova < linhas_orig * 0.5:
        return False, f"ATENCAO: Arquivo original tem {linhas_orig} linhas, novo tem {linhas_nova}. Parece que o codigo foi deletado!"

    if linhas_nova > linhas_orig * 2.5:
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
    # Tenta padrao principal: ```python ... ```
    m = re.search(r"```python\s*\n(.*?)```", resposta, re.DOTALL)
    if m:
        codigo = m.group(1).strip()
        linhas = len(codigo.splitlines())
        if linhas >= num_linhas_esperado * 0.5:
            return codigo

    # Tenta sem linguagem especifica: ``` ... ```
    m = re.search(r"```\s*\n(.*?)```", resposta, re.DOTALL)
    if m:
        codigo = m.group(1).strip()
        linhas = len(codigo.splitlines())
        if linhas >= num_linhas_esperado * 0.5:
            return codigo

    # Tenta sem crases: se tem def/class no inicio e tem muitas linhas
    linhas = resposta.splitlines()
    if linhas:
        # Procura onde comeca o codigo
        inicio = 0
        for i, l in enumerate(linhas):
            if l.strip().startswith(('def ', 'class ', 'import ', 'from ')):
                inicio = i
                break
        codigo = "\n".join(linhas[inicio:])
        num_linhas = len(codigo.splitlines())
        if num_linhas >= num_linhas_esperado * 0.5:
            return codigo.strip()

    return None


def sugerir_modificacao(nome_arquivo, descricao, conteudo_atual, provider="ollama", api_key=None, modelo=None):
    """Usa IA para sugerir uma modificacao no codigo."""
    num_linhas = len(conteudo_atual.splitlines())

    prompt = f"""INSTRUCAO CRITICA: Voce deve retornar o ARQUIVO COMPLETO com a mudanca aplicada.
Se voce retornar apenas parte do codigo, o sistema sera danificado.

ARQUIVO ATUAL ({num_linhas} linhas):
```python
{conteudo_atual}
```

O QUE MUDAR:
{descricao}

REGRAS ABSOLUTAS:
1. Retorne TODAS as {num_linhas} linhas do arquivo (ou mais, se precisar adicionar)
2. NUNCA retorne apenas a funcao modificada
3. NUNCA retorne "// ... resto do codigo" ou "..."
4. NAO remova NENHUMA funcao, classe ou import existente
5. NAO mude nada alem do que foi pedido
6. Mantenha toda a identacao e estilo original
7. Responda APENAS com o codigo entre ```python ```

O ARQUIVO DEVE CONTER TODAS ESTAS FUNCOES:
{chr(10).join('- ' + l.strip() for l in conteudo_atual.splitlines() if l.strip().startswith('def ') or l.strip().startswith('class '))}

RETORNE O ARQUIVO COMPLETO INTEIRO:"""

    print(f"[Dev] Provider: {provider}, Modelo: {modelo}")
    resposta = chat(prompt, provider=provider, api_key=api_key, modelo=modelo)
    
    if not resposta:
        print("[Dev] Resposta vazia do chat")
        return None
    
    if "Erro" in resposta[:20] or "erro" in resposta[:20]:
        print(f"[Dev] Erro do chat: {resposta[:200]}")
        return None
    
    print(f"[Dev] Resposta recebida ({len(resposta)} chars)")
    codigo = _extrair_codigo_completo(resposta, num_linhas)

    if codigo:
        linhas_codigo = len(codigo.splitlines())
        print(f"[Dev] Codigo extraido: {linhas_codigo} linhas (esperado: {num_linhas})")
        # Se retornou menos de 50% do original, algo deu errado
        if linhas_codigo < num_linhas * 0.5:
            print("[Dev] Codigo muito curto, rejeitado")
            return None
        return codigo

    print("[Dev] Nao conseguiu extrair codigo da resposta")
    return None


def aplicar_modificacao(nome_arquivo, descricao, provider="ollama", api_key=None, modelo=None):
    """Fluxo completo: ler, sugerir, validar, mostrar diff."""
    conteudo, erro = ler_arquivo(nome_arquivo)
    if erro:
        return None, erro, None

    novo_conteudo = sugerir_modificacao(nome_arquivo, descricao, conteudo, provider=provider, api_key=api_key, modelo=modelo)
    if not novo_conteudo:
        return None, f"Nao consegui gerar a modificacao. Verifique se o {provider.upper()} esta rodando.", None

    valido, msg_validacao = validar_modificacao(conteudo, novo_conteudo)
    if not valido:
        return None, msg_validacao, None

    diff = gerar_diff(conteudo, novo_conteudo, nome_arquivo)

    if not diff.strip():
        return None, "Nenhuma alteracao detectada no codigo.", None

    return novo_conteudo, diff, conteudo