#!/usr/bin/env python3
# ransomware_educativo.py
#
# RANSOMWARE EDUCATIVO (SIMULADO E CONTROLADO)
# - NÃO usa criptografia real (apenas transformação reversível com Base64).
# - Só atua dentro de uma pasta de teste indicada pelo utilizador.
# - Não tem persistência, propagação, nem comunicação externa.
# - Cria nota de "resgate" educativa claramente identificada como simulação académica.
#
# Uso (Windows / Linux):
#   python ransomware_educativo.py simulate "C:\LAB\PASTA_TESTE" --ext .txt .docx .pdf
#   python ransomware_educativo.py restore  "C:\LAB\PASTA_TESTE"
#
# Dica: aponta o Wazuh FIM para esta pasta de teste.

import argparse
import base64
import os
import sys
from pathlib import Path
from datetime import datetime

MARKER_HEADER = b"EDU_RANSOMWARE_SIM_V1\n"
LOCKED_EXT = ".edu_locked"
NOTE_NAME = "README_RESCATE_EDUCATIVO.txt"
MAX_FILES_DEFAULT = 500  # limite de segurança para evitar correr em massa por engano

NOTE_TEMPLATE = """\
*** SIMULACAO ACADEMICA - RANSOMWARE EDUCATIVO ***

Os seus ficheiros foram "bloqueados" de forma SIMULADA para fins academicos.
Nenhuma criptografia real foi usada. Nao existe perda de dados.

O que foi feito:
- Os ficheiros elegiveis foram transformados de forma REVERSIVEL (Base64) e marcados.
- Os ficheiros foram renomeados com a extensao: {locked_ext}

Como reverter:
- Execute o mesmo programa em modo RESTORE na mesma pasta de teste.

Data/Hora: {ts}

(Trabalho pratico defensivo - deteccao/análise com Wazuh FIM)
"""

def is_safe_test_dir(p: Path) -> bool:
    try:
        p = p.resolve()
    except Exception:
        return False

    # Recusar raiz
    if p == p.anchor:
        return False

    # Recusar diretórios comuns perigosos
    dangerous_names = {"windows", "program files", "program files (x86)", "users", "system32", "system"}
    parts_lower = {x.lower() for x in p.parts}
    if any(name in parts_lower for name in dangerous_names):
        # Permitir se o utilizador criou uma pasta de lab dentro de Users? Normalmente é lá.
        # Mas para segurança, só permitimos se a pasta tiver explicitamente "lab" ou "teste" no nome.
        name = p.name.lower()
        if "lab" not in name and "teste" not in name and "test" not in name:
            return False

    return True

def eligible_file(path: Path, exts: set[str]) -> bool:
    if not path.is_file():
        return False
    if path.name == NOTE_NAME:
        return False
    if path.suffix.lower() == LOCKED_EXT:
        return False
    if path.suffix.lower() in exts:
        return True
    return False

def write_note(root: Path):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    note_path = root / NOTE_NAME
    content = NOTE_TEMPLATE.format(locked_ext=LOCKED_EXT, ts=ts)
    note_path.write_text(content, encoding="utf-8", errors="replace")

def simulate(root: Path, exts: set[str], max_files: int):
    # Percorrer recursivamente apenas dentro da pasta indicada
    files = []
    for p in root.rglob("*"):
        if eligible_file(p, exts):
            files.append(p)
            if len(files) >= max_files:
                break

    # Criar nota educativa (gera evento FIM)
    write_note(root)

    changed = 0
    for p in files:
        try:
            data = p.read_bytes()
            # Evitar reprocessar se já tem marker
            if data.startswith(MARKER_HEADER):
                continue

            encoded = base64.b64encode(data)
            new_data = MARKER_HEADER + encoded

            # Escrever por cima (gera evento FIM)
            p.write_bytes(new_data)

            # Renomear (gera evento FIM)
            new_name = p.with_name(p.name + LOCKED_EXT)
            # Se já existir, evita sobrescrever
            if not new_name.exists():
                p.rename(new_name)

            changed += 1
        except Exception:
            # Ignorar erros para não bloquear o lab por permissões/ficheiros em uso
            continue

    print(f"[SIMULATE] Pasta: {root}")
    print(f"[SIMULATE] Extensoes alvo: {sorted(exts)}")
    print(f"[SIMULATE] Ficheiros transformados/renomeados: {changed}")
    print(f"[SIMULATE] Nota criada: {NOTE_NAME}")

def restore(root: Path, max_files: int):
    # Restaurar apenas ficheiros com extensão LOCKED_EXT
    locked_files = []
    for p in root.rglob(f"*{LOCKED_EXT}"):
        if p.is_file():
            locked_files.append(p)
            if len(locked_files) >= max_files:
                break

    restored = 0
    for p in locked_files:
        try:
            data = p.read_bytes()
            if not data.startswith(MARKER_HEADER):
                continue

            b64 = data[len(MARKER_HEADER):]
            original = base64.b64decode(b64)

            # Escrever conteúdo original e remover extensão LOCKED_EXT
            restored_path = Path(str(p)[: -len(LOCKED_EXT)])
            restored_path.write_bytes(original)

            # Apagar o ficheiro "bloqueado"
            try:
                p.unlink()
            except Exception:
                pass

            restored += 1
        except Exception:
            continue

    print(f"[RESTORE] Pasta: {root}")
    print(f"[RESTORE] Ficheiros restaurados: {restored}")
    print(f"[RESTORE] (Opcional) Apaga manualmente a nota: {NOTE_NAME}")

def parse_args():
    ap = argparse.ArgumentParser(description="Ransomware Educativo (simulado) - apenas para laboratório controlado.")
    ap.add_argument("mode", choices=["simulate", "restore"], help="simulate: simula 'encriptação'; restore: reverte.")
    ap.add_argument("path", help="Pasta de teste (apenas esta pasta será percorrida).")
    ap.add_argument("--ext", nargs="*", default=[".txt", ".log", ".csv", ".json", ".xml"],
                    help="Lista de extensões alvo (apenas no modo simulate). Ex: --ext .txt .docx .pdf")
    ap.add_argument("--max-files", type=int, default=MAX_FILES_DEFAULT,
                    help=f"Limite máximo de ficheiros a processar (default: {MAX_FILES_DEFAULT}).")
    return ap.parse_args()

def main():
    args = parse_args()
    root = Path(args.path).expanduser()

    if not root.exists() or not root.is_dir():
        print("Erro: a pasta indicada nao existe ou nao e uma diretoria.")
        sys.exit(1)

    if not is_safe_test_dir(root):
        print("Erro: a pasta indicada parece perigosa (ex.: raiz do disco/sistema).")
        print("Escolhe uma pasta de teste dedicada, por ex.: C:\\LAB\\PASTA_TESTE")
        sys.exit(1)

    # Normalizar extensões
    exts = set()
    for e in args.ext:
        if not e:
            continue
        e = e.strip()
        if not e.startswith("."):
            e = "." + e
        exts.add(e.lower())

    if args.mode == "simulate":
        simulate(root, exts, args.max_files)
    else:
        restore(root, args.max_files)

if __name__ == "__main__":
    main()
