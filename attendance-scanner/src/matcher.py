import csv
import os
from typing import List, Tuple, Optional

try:
    from rapidfuzz import process, fuzz
    HAS_RAPIDFUZZ = True
except Exception:
    HAS_RAPIDFUZZ = False


ROSTER_PATH = os.path.join(os.path.dirname(__file__), '..', 'roster.csv')


def load_roster(path: Optional[str] = None) -> List[str]:
    """Carrega nomes canônicos do arquivo roster.csv (coluna canonical_name)."""
    p = path or ROSTER_PATH
    names = []
    if not os.path.exists(p):
        return names
    with open(p, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # aceita header 'canonical_name' ou primeira coluna
            if 'canonical_name' in row and row['canonical_name'].strip():
                names.append(row['canonical_name'].strip())
            else:
                # fallback: pega primeira coluna
                first = next(iter(row.values()), '').strip()
                if first:
                    names.append(first)
    return names


def match_to_roster(name: str, roster: List[str], threshold: int = 85) -> Tuple[Optional[str], Optional[float]]:
    """Retorna (canonical_name, score) se houver match com score >= threshold, senão (None, best_score).

    Se `rapidfuzz` não estiver instalado, retorna (None, None) para indicar que a correspondência não foi feita.
    """
    if not name or not roster:
        return None, None
    if not HAS_RAPIDFUZZ:
        return None, None

    best = process.extractOne(name, roster, scorer=fuzz.WRatio)
    if not best:
        return None, None
    cand, score, _idx = best
    if score >= threshold:
        return cand, float(score)
    return None, float(score)
