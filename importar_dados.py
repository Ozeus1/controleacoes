#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para importar dados dos bancos antigos para o novo sistema Flask
"""
from app import create_app
from utils.importador import importar_dados_antigos, importar_fluxo_caixa
import os

def main():
    # Criar aplicação
    app = create_app('development')
    
    print("=" * 80)
    print("IMPORTADOR DE DADOS DO SISTEMA ANTIGO")
    print("=" * 80)
    print()
    
    # Caminhos dos bancos antigos
    caminho_base = os.path.dirname(__file__)
    caminho_financas = os.path.join(caminho_base, 'financas.db')
    caminho_receitas = os.path.join(caminho_base, 'financas_receitas.db')
    caminho_fluxo = os.path.join(caminho_base, 'fluxo_caixa.db')
    
    # Verificar se os arquivos existem
    print("Verificando arquivos de banco de dados...")
    arquivos = [
        ('Despesas', caminho_financas),
        ('Receitas', caminho_receitas),
        ('Fluxo de Caixa', caminho_fluxo)
    ]
    
    for nome, caminho in arquivos:
        if os.path.exists(caminho):
            print(f"✓ {nome}: {caminho}")
        else:
            print(f"✗ {nome}: {caminho} (NÃO ENCONTRADO)")
    
    print()
    
    # Perguntar ao usuário
    resposta = input("Deseja continuar com a importação? (s/n): ").strip().lower()
    if resposta != 's':
        print("Importação cancelada.")
        return
    
    print()
    print("-" * 80)
    print("IMPORTANDO DESPESAS E RECEITAS")
    print("-" * 80)
    
    # Importar despesas e receitas
    if os.path.exists(caminho_financas) or os.path.exists(caminho_receitas):
        relatorio = importar_dados_antigos(
            app,
            caminho_financas=caminho_financas,
            caminho_receitas=caminho_receitas,
            user_id=1  # Admin
        )
        
        print("\nResultado:")
        print(f"  Categorias de despesa: {relatorio['categorias_despesa']}")
        print(f"  Categorias de receita: {relatorio['categorias_receita']}")
        print(f"  Meios de pagamento: {relatorio['meios_pagamento']}")
        print(f"  Meios de recebimento: {relatorio['meios_recebimento']}")
        print(f"  Despesas importadas: {relatorio['despesas']}")
        print(f"  Receitas importadas: {relatorio['receitas']}")
        
        if relatorio['erros']:
            print("\n⚠️ Erros encontrados:")
            for erro in relatorio['erros']:
                print(f"  - {erro}")
        
        if relatorio['sucesso']:
            print("\n✓ Importação concluída com sucesso!")
        else:
            print("\n✗ Importação falhou.")
    else:
        print("Nenhum arquivo de despesas/receitas encontrado. Pulando...")
    
    print()
    print("-" * 80)
    print("IMPORTANDO FLUXO DE CAIXA")
    print("-" * 80)
    
    # Importar fluxo de caixa
    if os.path.exists(caminho_fluxo):
        relatorio_fluxo = importar_fluxo_caixa(
            app,
            caminho_fluxo_caixa=caminho_fluxo,
            user_id=1  # Admin
        )
        
        print("\nResultado:")
        print(f"  Balanços mensais: {relatorio_fluxo['balancos_mensais']}")
        print(f"  Eventos de caixa avulsos: {relatorio_fluxo['eventos_caixa']}")
        
        if relatorio_fluxo['erros']:
            print("\n⚠️ Erros encontrados:")
            for erro in relatorio_fluxo['erros']:
                print(f"  - {erro}")
        
        if relatorio_fluxo['sucesso']:
            print("\n✓ Importação concluída com sucesso!")
        else:
            print("\n✗ Importação falhou.")
    else:
        print("Arquivo fluxo_caixa.db não encontrado. Pulando...")
    
    print()
    print("=" * 80)
    print("IMPORTAÇÃO FINALIZADA")
    print("=" * 80)

if __name__ == '__main__':
    main()
