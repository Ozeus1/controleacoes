
import re

filename = r'c:\Users\Orlei\OneDrive\ProjPython\FINAN\sistema_financeiro_v15.py'
with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

# Skip line 1102 (index 1101)
skip_indices = [1101]

for i, line in enumerate(lines):
    if i in skip_indices:
        continue
    
    if 'FROM despesas' in line:
        print(f"--- Line {i+1} ---")
        print(f"Original: {line.strip()}")
        
        # Determine type
        is_select = 'SELECT' in line or 'SELECT' in lines[i-1] or 'SELECT' in lines[i-2] # Heuristic
        is_delete = 'DELETE' in line
        
        new_line = line
        
        if is_select:
            new_line = new_line.replace('FROM despesas', 'FROM v_despesas_compat')
        
        # Check for WHERE in this line
        if 'WHERE' in new_line:
            # Append AND user_id = ?
            # Need to be careful about placement if line continues
            # Assuming simple cases for now
            if '?' in new_line:
                 # It has parameters.
                 pass
        
        print(f"Proposed: {new_line.strip()}")
        
        # Check for execute params in next lines
        # This is hard to visualize in a simple script.
        # I'll just print the context.
        print("Context:")
        for j in range(max(0, i-2), min(len(lines), i+5)):
             print(f"{j+1}: {lines[j].rstrip()}")
        print("------------------")
