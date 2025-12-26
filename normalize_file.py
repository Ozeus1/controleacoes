
filename = r'c:\Users\Orlei\OneDrive\ProjPython\FINAN\sistema_financeiro_v15.py'

with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

# Write back clean
with open(filename, 'w', encoding='utf-8') as f:
    for line in lines:
        f.write(line)

print("File normalized.")
