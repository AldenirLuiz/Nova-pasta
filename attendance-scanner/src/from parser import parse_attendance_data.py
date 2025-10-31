from parser import parse_attendance_data
from matcher import load_roster, match_to_roster

text = open('..\\roster_candidates.txt', encoding='utf-8').read()
res = parse_attendance_data(text)
roster = load_roster('attendance-scanner/roster.csv')
for d in res['details']:
    corrected = d['corrected_name']
    canonical, score = match_to_roster(corrected, roster, threshold=85)
    print(corrected, '->', canonical, score)