#!/bin/bash
echo "=== DIAGNOSTICO ==="
echo "1. Data/Hora: $(date)"
echo "2. Processos Rodando:"
ps aux | grep -E "gunicorn|python|uwsgi|flask|controle_acoes" | grep -v grep
echo "-------------------"
echo "3. Conteudo do Arquivo (Procurando string removida):"
if grep -q "Erro na Página FIIs" app.py; then
    echo "FALHA: O arquivo app.py AINDA TEM o código antigo!"
else
    echo "SUCESSO: O arquivo app.py está limpo no disco."
fi
echo "-------------------"
echo "4. Git Hash:"
git log -n 1 --oneline
echo "==================="
