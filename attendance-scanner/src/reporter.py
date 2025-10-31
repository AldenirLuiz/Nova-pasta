from pathlib import Path
import csv
from datetime import datetime

def generate_report(data: dict, out_path: str = None):
    present = data.get('present', 0)
    absent = data.get('absent', 0)
    total = present + absent

    if out_path is None:
        base = Path(__file__).resolve().parent
        out_dir = base.parent.joinpath('reports')
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir.joinpath(f'attendance_summary_{datetime.now():%Y%m%d_%H%M%S}.csv')

    with open(out_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['present', 'absent', 'total'])
        writer.writerow([present, absent, total])

    print("Relatório de Presença")
    print("---------------------")
    print(f"Presentes: {present}")
    print(f"Ausentes : {absent}")
    print(f"Total    : {total}")
    print(f"Relatório salvo em: {out_path}")