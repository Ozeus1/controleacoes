from app import app, db, Asset, process_assets, current_user, login_manager
from flask import render_template
import sys
import traceback

# Mock current_user for the script
class MockUser:
    id = 1
    is_authenticated = True

print("--- STARTING FII PAGE DEBUG ---")

try:
    with app.app_context():
        # Mock login
        # We assume user ID 1 for testing. If your user ID is different, change it here.
        user_id = 1
        print(f"Querying FIIs for User ID: {user_id}...")
        
        raw_assets = Asset.query.filter(Asset.type=='FII', Asset.user_id==user_id, Asset.quantity > 0).all()
        print(f"Found {len(raw_assets)} FII assets.")
        
        print("Processing assets...")
        processed_assets = process_assets(raw_assets)
        print("Assets processed successfully.")
        
        total_invested = sum(a['total_invested'] for a in processed_assets)
        total_current = sum(a['current_total'] for a in processed_assets)
        print(f"Totals calculated: Invested={total_invested:.2f}, Current={total_current:.2f}")
        
        print("Attempting to render template 'fiis.html'...")
        # We need a request context for url_for and filters to work during render
        with app.test_request_context():
            # Mock current_user inside request context
            from flask_login import login_user
            user = MockUser()
            # We can't easily mock login_user without a real user object, 
            # but render_template might essentially need variables.
            # However, templates often use 'current_user'.
            # Let's just try to render and catch specific jinja errors.
            
            output = render_template('fiis.html', assets=processed_assets, total_invested=total_invested, total_current=total_current)
            print("Template rendered successfully (Length: " + str(len(output)) + " chars).")

    print("\n--- TEST PASSED: No errors found in logic or template. ---")
    print("If you still see 500 in browser, it might be a specific library missing in the Web Server environment.")

except Exception as e:
    print("\n--- TEST FAILED: Error Detected ---")
    traceback.print_exc()
    sys.exit(1)
