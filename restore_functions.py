
filename_v15 = r'c:\Users\Orlei\OneDrive\ProjPython\FINAN\sistema_financeiro_v15.py'
filename_backup = r'c:\Users\Orlei\OneDrive\ProjPython\FINAN\sistema_financeiro_v15_backup.py'

# Read v15
with open(filename_v15, 'r', encoding='utf-8', errors='ignore') as f:
    lines_v15 = f.readlines()

# Read backup
with open(filename_backup, 'r', encoding='utf-8', errors='ignore') as f:
    lines_backup = f.readlines()

# Define ranges (0-based indices)
# v15: keep 0 to 2064 (line 2065 is index 2064)
# So we want lines_v15[:2064]
v15_keep_start = lines_v15[:2064]

# backup: extract 2099 to 3846 (lines) -> indices 2098 to 3846 (exclusive? no, 3846 is the line number of the last line we want)
# Line 3847 is main(). So we want up to 3846.
# Index 3846 corresponds to line 3847. So slice up to 3846.
# Wait, line 2099 is index 2098.
# Line 3847 is index 3846.
# So lines_backup[2098:3846] gives lines 2099 to 3846.
backup_extract = lines_backup[2098:3846]

# v15: keep 2458 to end (line 2458 is index 2457)
# So lines_v15[2457:]
v15_keep_end = lines_v15[2457:]

# Combine
new_lines = v15_keep_start + backup_extract + v15_keep_end

# Write
with open(filename_v15, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print(f"Restored {len(backup_extract)} lines from backup.")
print(f"Total lines: {len(new_lines)}")
