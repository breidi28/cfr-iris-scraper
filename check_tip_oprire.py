import re
with open('trenuri-2025-2026_sntfc.xml', 'r', encoding='utf-8') as f:
    text = f.read()
    matches = set(re.findall(r'TipOprire="([^"]*)"', text))
    print(matches)
