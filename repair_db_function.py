
filename = r'c:\Users\Orlei\OneDrive\ProjPython\FINAN\sistema_financeiro_v15.py'

# Read lines
with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

# 1. Delete garbage lines 1002-1016 (indices 1001-1015)
# Line 1002 is index 1001. Line 1016 is index 1015.
# We want to keep 1017 (index 1016) which is '    def configurar_estilo(self):\n'
garbage_start = 1001
garbage_end = 1016 # Slice end is exclusive, so 1016 means up to index 1015

# 2. Find insertion point for criar_banco_dados header
# It should be before '            self.cursor = self.conn.cursor()'
# In original lines, this was around 1051.
insert_idx = -1
for i in range(1040, 1060):
    if 'self.cursor = self.conn.cursor()' in lines[i]:
        insert_idx = i
        break

if insert_idx == -1:
    print("Could not find insertion point for criar_banco_dados header.")
    exit(1)

print(f"Garbage range: {garbage_start}-{garbage_end}")
print(f"Insertion point (original index): {insert_idx}")
print(f"Line at insertion: {repr(lines[insert_idx])}")

# Construct new lines
new_lines = []
new_lines.extend(lines[:garbage_start])
new_lines.extend(lines[garbage_end:insert_idx])

# Header to insert
header = [
    '    def criar_banco_dados(self):\n',
    '        """Cria o banco de dados e as tabelas (Multi-usuário)"""\n',
    '        try:\n',
    "            self.conn = sqlite3.connect('financas.db')\n"
]
new_lines.extend(header)

new_lines.extend(lines[insert_idx:])

with open(filename, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("File repaired.")
