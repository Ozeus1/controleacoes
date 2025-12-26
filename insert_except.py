
filename = r'c:\Users\Orlei\OneDrive\ProjPython\FINAN\sistema_financeiro_v15.py'

# Read lines
with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

# Insert before line 2204 (index 2203)
insert_idx = 2203
except_block = """
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao exibir relatório: {e}")

"""

new_lines = lines[:insert_idx+1] + [except_block] + lines[insert_idx+1:]

with open(filename, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("Except block inserted.")
