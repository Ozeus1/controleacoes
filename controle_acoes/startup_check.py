
import sys
import os

print("--- Starting Import Check ---")
try:
    from app import app
    print("SUCCESS: App imported successfully.")
except Exception as e:
    print("CRITICAL IMPORT ERROR:")
    import traceback
    traceback.print_exc()
except SystemExit as e:
    print(f"SystemExit: {e}")
print("--- End Import Check ---")
