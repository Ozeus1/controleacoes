import google.generativeai as genai
import os

api_key = os.getenv('GOOGLE_API_KEY')
if not api_key:
    # Tenta ler do arquivo se o usuário salvou na GUI (mas a GUI salva em os.environ do processo dela)
    # Vou pedir para o usuário definir ou assumir que ele vai rodar isso no mesmo ambiente
    print("Defina a variável de ambiente GOOGLE_API_KEY")
else:
    genai.configure(api_key=api_key)
    print("Listando modelos disponíveis...")
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"- {m.name}")
