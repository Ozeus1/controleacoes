import inspect
from google import genai
from google.genai import types

print("Versão do google-genai:", genai.__version__)

print("\nEstrutura de types.Tool:")
print(inspect.signature(types.Tool))

print("\nEstrutura de types.FileSearch:")
print(inspect.signature(types.FileSearch))

print("\nEstrutura de types.GenerateContentConfig:")
print(inspect.signature(types.GenerateContentConfig))
