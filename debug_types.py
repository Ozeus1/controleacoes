import inspect
from google import genai
from google.genai import types

print(f"GenAI Version: {genai.__version__}")

print("\n--- types.Tool attributes ---")
for name, val in inspect.getmembers(types.Tool):
    if not name.startswith('_'):
        print(name)

print("\n--- types.FileSearch attributes ---")
for name, val in inspect.getmembers(types.FileSearch):
    if not name.startswith('_'):
        print(name)

print("\n--- types.GenerateContentConfig attributes ---")
for name, val in inspect.getmembers(types.GenerateContentConfig):
    if not name.startswith('_'):
        print(name)
