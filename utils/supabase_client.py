import requests
import json
from datetime import datetime

class SupabaseClient:
    def __init__(self, url, key):
        # Sanitização de entradas (removendo espaços e possíveis prefixos acidentais como '1')
        self.url = url.strip()
        self.key = key.strip()
        
        # Correção específica para erro comum de cópia (prefixo '1')
        if self.url.startswith('https://1gbr'):
            self.url = self.url.replace('https://1gbr', 'https://gbr', 1)
            
        if self.key.startswith('1eyJ'):
            self.key = self.key[1:]

        self.url = self.url.rstrip('/')
        
        self.headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal"
        }

    def test_connection(self, table_name):
        """Testa a conexão tentando buscar 1 registro"""
        try:
            endpoint = f"{self.url}/rest/v1/{table_name}?select=*&limit=1"
            response = requests.get(endpoint, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                return {"success": True, "message": "Conectado com sucesso!"}
            else:
                return {"success": False, "message": f"Erro: {response.status_code} - {response.text}"}
        except Exception as e:
            return {"success": False, "message": f"Erro de conexão: {str(e)}"}

    def fetch_data(self, table_name, limit=100):
        """Busca dados da tabela"""
        try:
            # Busca registros que NÃO foram migrados ainda
            endpoint = f"{self.url}/rest/v1/{table_name}?select=*&migrado=is.false&order=data_despesa.desc&limit={limit}"
            
            response = requests.get(endpoint, headers=self.headers, timeout=15)
            
            if response.status_code == 200:
                return {"success": True, "data": response.json()}
            else:
                return {"success": False, "message": f"Erro ao buscar dados: {response.text}"}
        except Exception as e:
            return {"success": False, "message": f"Erro ao buscar dados: {str(e)}"}

    def update_record(self, table_name, id, data):
        """Atualiza um registro"""
        try:
            endpoint = f"{self.url}/rest/v1/{table_name}?id=eq.{id}"
            response = requests.patch(endpoint, headers=self.headers, json=data)
            
            if response.status_code in [200, 204]:
                return {"success": True}
            else:
                return {"success": False, "message": f"Erro ao atualizar: {response.text}"}
        except Exception as e:
            return {"success": False, "message": f"Erro ao atualizar: {str(e)}"}

    def delete_record(self, table_name, id):
        """Exclui um registro"""
        try:
            endpoint = f"{self.url}/rest/v1/{table_name}?id=eq.{id}"
            response = requests.delete(endpoint, headers=self.headers)
            
            if response.status_code in [200, 204]:
                return {"success": True}
            else:
                return {"success": False, "message": f"Erro ao excluir: {response.text}"}
        except Exception as e:
            return {"success": False, "message": f"Erro ao excluir: {str(e)}"}
