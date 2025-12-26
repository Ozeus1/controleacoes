#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para verificar se a importação foi bem-sucedida
"""
from app import create_app
from models import db, CategoriaDespesa, CategoriaReceita, MeioPagamento, MeioRecebimento, Despesa, Receita, BalancoMensal, EventoCaixaAvulso

def main():
    app = create_app('development')
    
    with app.app_context():
        print("=" * 80)
        print("VERIFICAÇÃO DOS DADOS IMPORTADOS")
        print("=" * 80)
        print()
        
        print("📊 CONFIGURAÇÕES:")
        print(f"  Categorias de Despesa: {CategoriaDespesa.query.count()}")
        print(f"  Categorias de Receita: {CategoriaReceita.query.count()}")
        print(f"  Meios de Pagamento: {MeioPagamento.query.count()}")
        print(f"  Meios de Recebimento: {MeioRecebimento.query.count()}")
        
        print()
        print("💰 TRANSAÇÕES:")
        print(f"  Despesas: {Despesa.query.count()}")
        print(f"  Receitas: {Receita.query.count()}")
        
        print()
        print("📈 FLUXO DE CAIXA:")
        print(f"  Balanços Mensais: {BalancoMensal.query.count()}")
        print(f"  Eventos Avulsos: {EventoCaixaAvulso.query.count()}")
        
        print()
        
        # Mostrar algumas despesas
        if Despesa.query.count() > 0:
            print("Últimas 3 despesas importadas:")
            despesas = Despesa.query.order_by(Despesa.id.desc()).limit(3).all()
            for d in despesas:
                print(f"  - {d.data_pagamento} | {d.descricao} | R$ {d.valor:.2f}")
        
        print()
        
        # Mostrar algumas receitas
        if Receita.query.count() > 0:
            print("Últimas 3 receitas importadas:")
            receitas = Receita.query.order_by(Receita.id.desc()).limit(3).all()
            for r in receitas:
                print(f"  - {r.data_recebimento} | {r.descricao} | R$ {r.valor:.2f}")
        
        print()
        print("=" * 80)

if __name__ == '__main__':
    main()
