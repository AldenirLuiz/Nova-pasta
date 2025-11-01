import re
import unicodedata
from collections import Counter
from typing import List, Dict, Any
from dataclasses import dataclass
from datetime import datetime

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


@dataclass
class AttendanceEntry:
    name: str
    role: str
    morning_in: str = ''
    morning_out: str = ''
    afternoon_in: str = ''
    afternoon_out: str = ''
    is_absent: bool = False


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


def parse_time(time_str: str) -> str:
    """Validates and formats time strings"""
    if time_str.upper() == 'F':
        return 'F'
    try:
        # Normalize time format
        if ':' in time_str:
            return time_str.strip()
        # Handle cases where : is missing
        if len(time_str) == 4:
            return f"{time_str[:2]}:{time_str[2:]}"
        return time_str
    except:
        return time_str


def parse_line(line: str) -> AttendanceEntry:
    """Parses a single line from the attendance sheet"""
    # Remove multiple spaces and split
    parts = [p.strip() for p in re.split(r'\s+', line) if p.strip()]
    
    if len(parts) < 4:  # Skip invalid lines
        return None
        
    # Extract times (looking for patterns like HH:MM or HHMM)
    times = []
    for part in parts:
        if re.match(r'^([0-2]?\d[:.]?[0-5]\d|F)$', part):
            times.append(parse_time(part))
    
    # Get name and role (typically first parts before times)
    name_parts = []
    role_parts = []
    found_role = False
    
    for part in parts:
        if not re.match(r'^([0-2]?\d[:.]?[0-5]\d|F)$', part):
            if found_role:
                role_parts.append(part)
            else:
                # Common roles that indicate role section started
                if part.upper() in ['SERVENTE', 'PEDREIRO', 'PINTOR', 'ELETRICISTA']:
                    found_role = True
                    role_parts.append(part)
                else:
                    name_parts.append(part)
    
    name = ' '.join(name_parts)
    role = ' '.join(role_parts)
    
    entry = AttendanceEntry(
        name=name,
        role=role,
        is_absent=any(t == 'F' for t in times)
    )
    
    # Assign times if available
    if len(times) >= 1: entry.morning_in = times[0]
    if len(times) >= 2: entry.morning_out = times[1]
    if len(times) >= 3: entry.afternoon_in = times[2]
    if len(times) >= 4: entry.afternoon_out = times[3]
    
    return entry

def parse_attendance_data(text: str) -> Dict[str, Any]:
    """Parses the complete attendance sheet"""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    entries: List[AttendanceEntry] = []
    
    for line in lines:
        entry = parse_line(line)
        if entry:
            entries.append(entry)
    
    # Count attendance
    present = sum(1 for e in entries if not e.is_absent)
    absent = sum(1 for e in entries if e.is_absent)
    
    return {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "present": present,
        "absent": absent,
        "total": len(entries),
        "entries": entries
    }