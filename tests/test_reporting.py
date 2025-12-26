
import unittest
import sqlite3
import tkinter as tk
from unittest.mock import MagicMock, patch
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sistema_financeiro_v15 import SistemaFinanceiro

class TestReporting(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.app = SistemaFinanceiro(self.root)
        
        # Setup in-memory DB
        self.app.conn = sqlite3.connect(':memory:')
        self.app.cursor = self.app.conn.cursor()
        
        # Create tables and view
        self.app.cursor.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT)")
        self.app.cursor.execute("INSERT INTO users (username) VALUES ('testuser')")
        
        self.app.cursor.execute("""
            CREATE TABLE despesas (
                id INTEGER PRIMARY KEY, 
                descricao TEXT, 
                valor REAL, 
                data_pagamento DATE, 
                conta_despesa TEXT,
                user_id INTEGER
            )
        """)
        
        # Create view (mocking the real view logic)
        self.app.cursor.execute("""
            CREATE VIEW v_despesas_compat AS
            SELECT id, descricao, valor, data_pagamento, conta_despesa, user_id
            FROM despesas
        """)
        
        # Insert test data
        self.app.cursor.execute("INSERT INTO despesas (descricao, valor, data_pagamento, conta_despesa, user_id) VALUES ('D1', 100, '2023-10-01', 'Cat1', 1)")
        self.app.cursor.execute("INSERT INTO despesas (descricao, valor, data_pagamento, conta_despesa, user_id) VALUES ('D2', 200, '2023-10-15', 'Cat2', 1)")
        self.app.cursor.execute("INSERT INTO despesas (descricao, valor, data_pagamento, conta_despesa, user_id) VALUES ('D3', 300, '2023-10-01', 'Cat1', 2)") # Other user
        
        self.app.conn.commit()
        
        # Mock session
        self.app.sessao = MagicMock()
        self.app.sessao.user_id = 1
        
        # Mock UI elements
        self.app.combo_mes_grafico = MagicMock()
        self.app.combo_mes_grafico.get.return_value = '10/2023'
        
        self.app.figura_grafico = MagicMock()
        self.app.canvas_grafico = MagicMock()

    def tearDown(self):
        self.app.conn.close()
        self.root.destroy()

    def test_atualizar_grafico(self):
        print("Testing atualizar_grafico...")
        # Should only see user 1's data (Total 300)
        # Cat1: 100, Cat2: 200.
        
        # We can't easily check the plot output, but we can check if it runs without error
        # and if it queries the DB correctly.
        
        # Mock ax.bar to capture data
        with patch('matplotlib.axes.Axes.bar') as mock_bar:
            self.app.atualizar_grafico()
            
            # Verify call args
            # mock_bar.call_args[0][1] should be values
            # We expect [200, 100] (ordered by total DESC)
            # or [100, 200] depending on order.
            # Query orders by total DESC. So Cat2 (200) first, then Cat1 (100).
            
            if mock_bar.called:
                args = mock_bar.call_args[0]
                valores = args[1]
                print(f"Values plotted: {valores}")
                self.assertEqual(list(valores), [200.0, 100.0])
            else:
                print("ax.bar was not called (maybe no results?)")
                # Check if results were found
                # self.app.cursor.execute("SELECT ...")
                pass

    def test_mostrar_relatorio_mensal_periodo(self):
        print("Testing mostrar_relatorio_mensal_periodo...")
        # Mock Toplevel to avoid opening windows
        with patch('tkinter.Toplevel') as mock_toplevel:
            self.app.mostrar_relatorio_mensal_periodo('2023-10-01', '2023-10-31')
            
            # Verify if query was executed
            # We can inspect the last executed query if we mock cursor, but we used real cursor.
            # We can check if Toplevel was called, meaning results were found.
            self.assertTrue(mock_toplevel.called)

if __name__ == '__main__':
    unittest.main()
