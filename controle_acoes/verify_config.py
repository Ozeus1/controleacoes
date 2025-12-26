
from app import app, db, Settings
# Ensure app context
with app.app_context():
    # 1. Test Settings Model
    print("Testing Settings...")
    Settings.set_value('brapi_token', 'TEST_KEY_123')
    val = Settings.get_value('brapi_token')
    assert val == 'TEST_KEY_123'
    print(f"Success: Stored and retrieved key: {val}")
    
    # Reset for cleanliness (optional, or keep generic for user convenience if they run this)
    # Settings.set_value('brapi_token', '') # Don't clear if this runs on user machine, but we are running it, so...
    
    # 2. Test raw quote fetch (mocked or real depending on key validation)
    # Since 'TEST_KEY_123' is invalid, the API call should fail or return error message from BRAPI
    from services import get_raw_quote_data
    print("\nTesting Raw Quote Fetch (with invalid key)...")
    success, data = get_raw_quote_data('PETR4') 
    # Even with invalid key, BRAPI might work for PETR4 or return 401
    print(f"Result (Success={success}): {str(data)[:100]}...") # Print snippet
    
    print("\nVerification script finished.")
