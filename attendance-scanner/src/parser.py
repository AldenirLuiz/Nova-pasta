import re
from collections import Counter
from typing import List, Dict, Any

def parse_attendance_data(text: str) -> Dict[str, Any]:
    """
    Detecta presença quando a linha contém horários (HH:MM).
    Detecta falta quando a linha contém marcações como 'F', 'FALTA', 'AUSENTE'.
    Retorna contagens e detalhes por linha para auditoria.
    """
    if not text:
        return {"present": 0, "absent": 0, "total_lines": 0, "details": []}

    lines: List[str] = [ln.strip() for ln in text.splitlines() if ln.strip()]
    time_re = re.compile(r'\b(?:[01]?\d|2[0-3]):[0-5]\d\b')
    absent_re = re.compile(r'\bF?\b', re.IGNORECASE)
    names_re = re.compile(r'^[A-Za-z\s]+$')

    present = 0
    absent = 0
    details: List[Dict[str, Any]] = []

    for ln in lines[2:-1]:  # pula cabeçalho
        has_time = bool(time_re.search(ln))
        has_absent = bool(absent_re.search(ln))
        has_name = bool(names_re.search(ln))

        if has_time:
            if has_name:
                name = names_re.search(ln).group(0).strip()
                print(f"Detected present for name: {name}")
            else:
                name = "Unknown"
            status = "present"
            present += 1
        elif has_absent:
            if has_name:
                name = names_re.search(ln).group(0).strip()
                print(f"Detected absent for name: {name}")
            else:
                name = "Unknown"
            
            status = "absent"
            absent += 1
        else:
            if has_name:
                name = names_re.search(ln).group(0).strip()
            else:
                name = "Unknown"
            status = "unknown"

        details.append({"name": name, "line": ln, "status": status, "has_time": has_time, "has_absent_mark": has_absent})
        #print(f"Parsed line: '{ln}' => Name: '{name}', Status: '{status}'")
    return {
        "present": int(present),
        "absent": int(absent),
        "total_lines": len(lines),
        "details": details
    }


def parse_attendance_data_simple(text: str):
    """
    Conta ocorrências de marcas comuns em folhas de ponto:
    - Presença: 'P', 'PRESENTE', 'PRES', 'X' (se X for usado)
    - Falta: 'F', 'FALTA', 'AUSENTE'
    Retorna dicionário com present, absent e tokens brutos.
    """
    if not text:
        return {"present": 0, "absent": 0, "raw_counts": {}}

    t = text.upper()
    # Captura P e F isolados, palavras e marcas comuns (X, ✓)
    tokens = re.findall(r'\bP\b|\bF\b|\bPRESENTE\b|\bPRES\b|\bFALTA\b|\bAUSENTE\b|[X\u2713\u2714]', t)
    counts = Counter(tokens)

    present = counts.get('P', 0) + counts.get('PRESENTE', 0) + counts.get('PRES', 0) + counts.get('X', 0) + counts.get('✓', 0) + counts.get('✔', 0)
    absent  = counts.get('F', 0) + counts.get('FALTA', 0) + counts.get('AUSENTE', 0)

    return {"present": int(present), "absent": int(absent), "raw_counts": dict(counts)}