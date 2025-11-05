"""
Script to create a new admin user
Usage: python create_admin_user.py <email> <password> <name>
"""
import sys
import json
import os
import uuid
from werkzeug.security import generate_password_hash
from datetime import datetime

USERS_FILE = os.path.join('data', 'users.json')

def create_admin_user(email, password, name="Admin User"):
    """Create a new admin user"""
    if not os.path.exists(USERS_FILE):
        print(f"Error: {USERS_FILE} does not exist")
        os.makedirs('data', exist_ok=True)
        users = {}
    else:
        with open(USERS_FILE, 'r') as f:
            users = json.load(f)
    
    # Check if user already exists
    for user_id, user in users.items():
        if user.get('email') == email:
            print(f"User with email {email} already exists. Making them admin...")
            user['role'] = 'admin'
            users[user_id] = user
            with open(USERS_FILE, 'w') as f:
                json.dump(users, f, indent=2)
            print(f"✓ User {email} is now an admin")
            return True
    
    # Create new user
    user_id = str(uuid.uuid4())
    new_user = {
        'id': user_id,
        'email': email,
        'name': name,
        'password': generate_password_hash(password),
        'role': 'admin',
        'created_at': str(datetime.utcnow())
    }
    
    users[user_id] = new_user
    
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=2)
    
    print(f"✓ Admin user created successfully!")
    print(f"  Email: {email}")
    print(f"  Name: {name}")
    print(f"  Role: admin")
    return True

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python create_admin_user.py <email> <password> [name]")
        print("Example: python create_admin_user.py admin@example.com password123 \"Admin Name\"")
        sys.exit(1)
    
    email = sys.argv[1]
    password = sys.argv[2]
    name = sys.argv[3] if len(sys.argv) > 3 else "Admin User"
    
    if create_admin_user(email, password, name):
        print("\n✓ Done! You can now login with these credentials.")
    else:
        sys.exit(1)

