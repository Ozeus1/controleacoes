
import re

filename = r'c:\Users\Orlei\OneDrive\ProjPython\FINAN\sistema_financeiro_v15.py'
output_file = r'c:\Users\Orlei\OneDrive\ProjPython\FINAN\fixes_proposal.txt'

with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

# Skip line 1102 (index 1101)
skip_indices = [1101]

with open(output_file, 'w', encoding='utf-8') as out:
    for i, line in enumerate(lines):
        if i in skip_indices:
            continue
        
        if 'FROM despesas' in line:
            out.write(f"--- Line {i+1} ---\n")
            out.write(f"Original: {line.strip()}\n")
            
            # Determine type
            # Look backwards for SELECT/DELETE
            context_start = max(0, i-5)
            context = "".join(lines[context_start:i+1])
            
            is_select = 'SELECT' in context
            is_delete = 'DELETE' in context
            
            new_line = line
            
            if is_select and not is_delete:
                new_line = new_line.replace('FROM despesas', 'FROM v_despesas_compat')
            
            out.write(f"Proposed: {new_line.strip()}\n")
            
            out.write("Context:\n")
            for j in range(max(0, i-2), min(len(lines), i+5)):
                 out.write(f"{j+1}: {lines[j].rstrip()}\n")
            out.write("------------------\n")
