
filename = r'c:\Users\Orlei\OneDrive\ProjPython\FINAN\sistema_financeiro_v15.py'
with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

# Uncomment lines 2490 to 2502
start = 2490 - 1
end = 2502 - 1
for i in range(start, end + 1):
    if i < len(lines) and lines[i].startswith('#'):
        lines[i] = lines[i][1:]

with open(filename, 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("Block uncommented.")
