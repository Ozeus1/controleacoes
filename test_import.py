import sys
print(f"Python version: {sys.version}")

try:
    from models import db
    print("Models imported successfully!")
except Exception as e:
    print(f"Error importing models: {e}")
    import traceback
    traceback.print_exc()
