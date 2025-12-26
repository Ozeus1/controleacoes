
from app import app, db, User

def list_users():
    with app.app_context():
        users = User.query.all()
        print(f"Users found: {len(users)}")
        for u in users:
            print(f"- {u.username}")

if __name__ == "__main__":
    list_users()
