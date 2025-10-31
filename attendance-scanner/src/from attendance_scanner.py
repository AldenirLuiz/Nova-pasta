import parser  # local module import
sample = """\nADRIANO DANTAS íBOCA SERVENTE 11:37 17101\nALDENIRLUIZ — — GAMBIARRA — [PEDREIRO | 635 1133 / 13:02/ 170\nANDREVIEIBA — ANDRE — o PINTOR %ÃJTÉÃ:% 13:07 | 17:09"""
res = parser.parse_attendance_data(sample)
for d in res['details']:    
    print(d['original_line'])    
    print('  cleaned:', d['cleaned_name'])   
print('  corrected:', d['corrected_name'])
print('  status:', d['status'])
print('---')
print('present/absent totals:', res['present'], res['absent'])
