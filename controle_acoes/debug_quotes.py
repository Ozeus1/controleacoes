
import os
import sys

# Windows path fix
sys.path.append(os.getcwd())

from flask import Flask
from models import db, Asset, Settings, User
from services import get_quotes
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
# Use absolute path for DB to avoid confusion
basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(basedir, 'instance', 'investments.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'debug'

print(f"DEBUG: Using DB Path: {db_path}")

db.init_app(app)

def test_update():
    with app.app_context():
        try:
            print("--- Starting Debug ---")
            
            # Check DB Connection
            try:
                user = User.query.first()
            except Exception as e:
                print(f"CRITICAL DB ERROR: {e}")
                import traceback
                traceback.print_exc()
                return

            if not user:
                print("No user found!")
                return

            print(f"Testing for user: {user.username} (ID: {user.id})")
            
            assets = Asset.query.filter_by(user_id=user.id).all()
            relevant = [a for a in assets if a.type in ['ACAO', 'FII']]
            print(f"Found {len(relevant)} assets.")
            
            chunk_size = 5
            relevant_chunks = [relevant[i:i + chunk_size] for i in range(0, len(relevant), chunk_size)]
            
            for i, chunk in enumerate(relevant_chunks):
                tickers = [a.ticker for a in chunk if a.ticker]
                print(f"Chunk {i}: {tickers}")
                
                try:
                    quotes = get_quotes(tickers, user_id=user.id)
                    print(f"  > Success! Got {len(quotes)} quotes.")
                except Exception as e:
                    print(f"  > CRASH/ERROR in Chunk {i}: {e}")
                    import traceback
                    traceback.print_exc()
                    
        except Exception as outer_e:
            print(f"OUTER FAULT: {outer_e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_update()
