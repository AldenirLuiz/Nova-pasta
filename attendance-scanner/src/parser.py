import re
import unicodedata
from collections import Counter
from typing import List, Dict, Any

# try to import matcher for roster fuzzy-matching; if not available, we'll skip matching
try:
    from matcher import load_roster, match_to_roster
    ROSTER = load_roster()
except Exception:
    ROSTER = []


# Heurísticas e listas auxiliares para limpar nomes reconhecidos via OCR
COMMON_ROLES = [
    'PEDREIRO', 'SERVENTE', 'PINTOR', 'ELETRICISTA', 'ALMOXARIFE',
    'FERREIRO', 'AUXILIAR', 'ENCANADOR', 'MARCENEIRO', 'SERVICO',
]

# Lista pequena de primeiros nomes comuns brasileiros para tentar ``descolar'' nomes colados
COMMON_FIRST_NAMES = [
    'ADRIANO','ALDENIR','ANDRE','ANTONIO','ANTONIO','CAIO','RAFAEL','COSME','DAMIAO','EMERSON',
    'FLAVIO','FRANCISCO','JOAO','JOSE','JORGE','LEANDRO','MAICOM','MARCOS','MATHEUS',
    'MICHAEL','PAULO','RAILSON','RENATO','RICARDO','RONALDO','SEBASTIAO','TIAGO','WELLINGTON',
    'JEFERSON','JEFERSON','JOAQUIM','JONALDO','ISRAEL'
]


def _remove_accents(s: str) -> str:
    nkfd = unicodedata.normalize('NFKD', s)
    return ''.join([c for c in nkfd if not unicodedata.combining(c)])


def clean_ocr_text(s: str) -> str:
    """Aplica normalizações básicas a uma linha de OCR

    - Substitui caracteres estranhos por espaços
    - Remove múltiplos espaços
    - Normaliza acentos
    - Corrige alguns erros comuns (ex: % -> A etc.)
    """
    if not s:
        return s

    # Mapeamento de correções simples observadas em OCR
    corrections = {
        '—': ' ', '–': ' ', '|': ' ', '\\': ' ', '/': ' ', '_': ' ', 'º': ' ', 'ª': ' ',
        '%': 'A', 'Ã': 'A', 'Ãº': 'U', 'Í': 'I', 'í': 'i', 'â': 'a', 'ó': 'o', '�': ' ',"\n": " "
    }

    out = s
    for k, v in corrections.items():
        out = out.replace(k, v)

    # Remove sequences of characters that are obviously non-text
    out = re.sub(r'[\u2018\u2019\u201c\u201d\u00b4\[\]<>\"*#@~]', ' ', out)
    out = re.sub(r'[-=+~©®]', ' ', out)

    # Collapse repeated non-letter characters
    out = re.sub(r'[^\w\s]', ' ', out)

    # Normalize whitespace
    out = re.sub(r'\s+', ' ', out).strip()

    # Normalize accents to help matching
    out = _remove_accents(out)

    return out


def strip_times_and_roles(line: str) -> str:
    """Remove horários, números, cargos e outras marcações para isolar o nome principal."""
    if not line:
        return line

    # remove padrões de tempo HH:MM e variantes
    line = re.sub(r'\b(?:[01]?\d|2[0-3])[:|lI][0-5]\d\b', ' ', line)
    line = re.sub(r'\b(?:[01]?\d|2[0-3])[:][0-5]\d\b', ' ', line)

    # remove números longos, telefones, códigos
    line = re.sub(r'\b\d{2,}\b', ' ', line)

    # remove palavras de cargos
    for r in COMMON_ROLES:
        line = re.sub(rf'\b{r}\b', ' ', line, flags=re.IGNORECASE)

    # remove tokens curtos não relevantes
    line = re.sub(r'\b(?:E|DE|DA|DO|DOS|DAS|O|A)\b', ' ', line, flags=re.IGNORECASE)

    # collapse spaces
    line = re.sub(r'\s+', ' ', line).strip()
    return line


def split_joined_name(name: str) -> str:
    """Tenta separar nomes colados (ex: ALDENIRLUIZ -> ALDENIR LUIZ) usando uma lista de primeiros nomes.

    Estratégia simples:
    - Se já houver espaços suficientes, retorna
    - Se não, procura partições onde a parte esquerda é um primeiro nome conhecido
    """
    if not name:
        return name

    if ' ' in name and len(name.split()) >= 2:
        return name

    up = name.upper()
    # procura por partições possíveis
    for fn in COMMON_FIRST_NAMES:
        if up.startswith(fn):
            rest = up[len(fn):]
            # tenta encontrar outro first name no início do restante
            for fn2 in COMMON_FIRST_NAMES:
                if rest.startswith(fn2):
                    return (fn + ' ' + fn2).title()
            # se não encontrou, tenta partir em duas metades razoáveis
            if 3 <= len(rest) <= 12:
                return (fn + ' ' + rest).title()

    # fallback: tenta inserir espaço entre duas sequências de letras longas
    m = re.match(r'([A-Z]{3,})([A-Z]{3,})', up)
    if m:
        return (m.group(1) + ' ' + m.group(2)).title()

    return name.title()


def correct_name(raw: str) -> str:
    """Pipeline de correção que aplica limpeza, remoção de cargos e separação de nomes colados."""
    if not raw:
        return 'Unknown'

    s = clean_ocr_text(raw)
    s = strip_times_and_roles(s)
    # strip stray punctuation/digits
    s = re.sub(r'[^A-Za-z\s]', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()

    if not s:
        return 'Unknown'

    # tenta separar nomes colados
    s = split_joined_name(s)

    # limitar a primeiros 4 tokens (nome + sobrenomes)
    parts = s.split()
    if len(parts) > 4:
        parts = parts[:4]

    # capitaliza apropriadamente
    final = ' '.join([p.title() for p in parts])
    return final


def parse_attendance_data(text: str) -> Dict[str, Any]:
    """Versão melhorada do parser que tenta extrair e corrigir nomes OCR-corrompidos.

    Retorna contagens e detalhes por linha com campos adicionais:
    - original_line: a linha OCR bruta
    - cleaned_name: nome após limpeza/remoção de cargos/tempos
    - corrected_name: nome final sugerido
    - status: present/absent/unknown
    """
    if not text:
        return {"present": 0, "absent": 0, "total_lines": 0, "details": []}

    lines: List[str] = [ln.strip() for ln in text.splitlines() if ln.strip()]
    time_re = re.compile(r'\b(?:[01]?\d|2[0-3]):[0-5]\d\b')
    absent_tokens = re.compile(r'\b(F|FALTA|AUSENTE)\b', re.IGNORECASE)

    present = 0
    absent = 0
    details: List[Dict[str, Any]] = []

    # normalmente a folha tem cabeçalho; se poucas linhas, percorre todas
    iter_lines = lines[2:-1] if len(lines) > 4 else lines

    for ln in iter_lines:
        has_time = bool(time_re.search(ln))
        has_absent = bool(absent_tokens.search(ln))

        cleaned = clean_ocr_text(ln)
        cleaned_no_meta = strip_times_and_roles(cleaned)
        corrected = correct_name(cleaned_no_meta)

        if has_time:
            status = 'present'
            present += 1
        elif has_absent:
            status = 'absent'
            absent += 1
        else:
            status = 'unknown'

        # attempt to match corrected name to canonical roster name (if roster available)
        canonical = None
        match_score = None
        try:
            if ROSTER:
                canonical, match_score = match_to_roster(corrected, ROSTER, threshold=85)
        except Exception:
            canonical = None
            match_score = None

        details.append({
            'original_line': ln,
            'cleaned_name': cleaned_no_meta,
            'corrected_name': corrected,
            'canonical_name': canonical,
            'match_score': match_score,
            'status': status,
            'has_time': has_time,
            'has_absent_mark': has_absent
        })

    return {
        'present': int(present),
        'absent': int(absent),
        'total_lines': len(lines),
        'details': details
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