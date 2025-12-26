
filename = r'c:\Users\Orlei\OneDrive\ProjPython\FINAN\sistema_financeiro_v15.py'
with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if 'sessao.user_id))' in line:
        print(f'{i+1}: {line.strip()}')
