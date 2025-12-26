
import re

filename = r'c:\Users\Orlei\OneDrive\ProjPython\FINAN\sistema_financeiro_v15.py'
with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read()

def fix_query(match):
    full_match = match.group(0)
    quote = match.group('quote')
    sql = match.group('sql')
    params = match.group('params')
    
    # Skip if not using despesas
    if 'FROM despesas' not in sql and 'UPDATE despesas' not in sql:
        return full_match
    
    # Skip view creation (heuristic: CREATE TABLE or CREATE VIEW)
    if 'CREATE TABLE' in sql or 'CREATE VIEW' in sql:
        return full_match
        
    # Determine operation
    is_select = 'SELECT' in sql.upper()
    is_delete = 'DELETE' in sql.upper()
    is_update = 'UPDATE' in sql.upper()
    
    new_sql = sql
    
    # 1. Update Table Name (SELECT only)
    if is_select and not is_delete and not is_update:
        new_sql = new_sql.replace('FROM despesas', 'FROM v_despesas_compat')
    
    # 2. Add WHERE clause
    # Check if WHERE exists
    # We need to insert AND user_id = ? or WHERE user_id = ?
    # Insertion point: before GROUP BY, ORDER BY, LIMIT, or end of string
    
    # Normalize spaces for regex
    # But we want to keep original formatting.
    # We'll search for keywords.
    
    keywords = ['GROUP BY', 'ORDER BY', 'LIMIT']
    insert_pos = len(new_sql)
    for kw in keywords:
        match_kw = re.search(kw, new_sql, re.IGNORECASE)
        if match_kw:
            insert_pos = min(insert_pos, match_kw.start())
            
    # Check if WHERE exists before insert_pos
    where_match = re.search(r'WHERE', new_sql[:insert_pos], re.IGNORECASE)
    
    suffix = new_sql[insert_pos:]
    prefix = new_sql[:insert_pos]
    
    if where_match:
        # Append AND user_id = ?
        # Be careful with whitespace.
        # We'll append it at the end of prefix.
        prefix = prefix.rstrip() + " AND user_id = ?\n                " 
    else:
        # Append WHERE user_id = ?
        prefix = prefix.rstrip() + "\n                WHERE user_id = ?\n                "
        
    new_sql = prefix + suffix
    
    # 3. Update Params
    new_params = params
    if params:
        # It's a tuple or list string, e.g. (a, b) or (a,)
        # We need to insert self.sessao.user_id
        # Regex to find the closing parenthesis
        # This is hard with regex if params has nested parens.
        # But usually params are simple variables.
        if params.strip().endswith(')'):
            new_params = params.strip()[:-1] + ", self.sessao.user_id)"
        else:
            # Maybe it's a variable name? e.g. execute(sql, params_var)
            # If so, we can't easily modify it without changing code structure.
            # But in this file, params are usually tuples literal.
            # Let's assume tuple literal.
            pass
    else:
        # No params. Add tuple.
        new_params = "(self.sessao.user_id,)"
        
    return f'self.cursor.execute({quote}{new_sql}{quote}, {new_params})'

# Regex to find execute calls
# Handles single and triple quotes
pattern = re.compile(r'self\.cursor\.execute\s*\(\s*(?P<quote>"""|\'\'\'|(?<!")"(?!")|(?<!\')\'(?!\'))(?P<sql>.*?)(?P=quote)\s*(?:,\s*(?P<params>.*?))?\s*\)', re.DOTALL)

new_content = pattern.sub(fix_query, content)

with open(filename, 'w', encoding='utf-8') as f:
    f.write(new_content)

print("SQL queries fixed.")
