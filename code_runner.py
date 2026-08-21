import os
import subprocess
import sys
import tempfile

CODE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "codigos")
os.makedirs(CODE_DIR, exist_ok=True)

TIMEOUT = 15


def run_code(code: str, language: str = "python") -> str:
    """Salva e roda um codigo. Retorna a saida."""
    if language == "python":
        ext = ".py"
        cmd = [sys.executable]
    elif language == "java":
        ext = ".java"
        cmd = ["java"]
    elif language == "c":
        ext = ".c"
        cmd = ["gcc", "-o"]
    else:
        return f"Linguagem '{language}' nao suportada. Use: python, java ou c."

    filename = f"temp_code{ext}"
    filepath = os.path.join(CODE_DIR, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(code)

    try:
        if language == "python":
            result = subprocess.run(
                cmd + [filepath],
                capture_output=True, text=True, timeout=TIMEOUT,
                cwd=CODE_DIR, encoding="utf-8", errors="replace",
            )
        elif language == "java":
            # Compilar
            comp = subprocess.run(
                ["javac", filepath],
                capture_output=True, text=True, timeout=TIMEOUT,
                cwd=CODE_DIR,
            )
            if comp.returncode != 0:
                return f"Erro de compilacao:\n{comp.stderr}"
            # Rodar
            classname = os.path.splitext(filename)[0]
            result = subprocess.run(
                ["java", "-cp", CODE_DIR, classname],
                capture_output=True, text=True, timeout=TIMEOUT,
                cwd=CODE_DIR,
            )
        elif language == "c":
            exe = os.path.join(CODE_DIR, "temp_code.exe")
            comp = subprocess.run(
                ["gcc", filepath, "-o", exe],
                capture_output=True, text=True, timeout=TIMEOUT,
                cwd=CODE_DIR,
            )
            if comp.returncode != 0:
                return f"Erro de compilacao:\n{comp.stderr}"
            result = subprocess.run(
                [exe],
                capture_output=True, text=True, timeout=TIMEOUT,
                cwd=CODE_DIR,
            )

        output = result.stdout.strip()
        errors = result.stderr.strip()

        if result.returncode != 0:
            return f"Erro:\n{errors or output}"
        return output or "(programa nao gerou saida)"

    except subprocess.TimeoutExpired:
        return f"Timeout: o codigo demorou mais de {TIMEOUT}s."
    except FileNotFoundError as e:
        return f"Ferramenta nao encontrada: {e}"
    except Exception as e:
        return f"Erro ao rodar: {e}"
