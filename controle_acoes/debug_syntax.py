try:
    import app
    print("Import Successful")
except SyntaxError as e:
    print(f"SyntaxError Detected:")
    print(f"Line: {e.lineno}")
    print(f"Message: {e.msg}")
    print(f"Text: {e.text}")
except Exception as e:
    print(f"Other Error: {e}")
