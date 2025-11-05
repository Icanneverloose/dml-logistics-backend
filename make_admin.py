"""
Script to make a user an admin
Usage: python make_admin.py <user_email>
"""
import sys
import json
import os

USERS_FILE = os.path.join('data', 'users.json')

def make_admin(email):
    """Make a user admin by email"""
    if not os.path.exists(USERS_FILE):
        print(f"Error: {USERS_FILE} does not exist")
        return False
    
    with open(USERS_FILE, 'r') as f:
        users = json.load(f)
    
    found = False
    for user_id, user in users.items():
        if user.get('email') == email:
            user['role'] = 'admin'
            found = True
            print(f"✓ User {email} is now an admin")
            break
    
    if not found:
        print(f"Error: User with email {email} not found")
        return False
    
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=2)
    
    return True

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python make_admin.py <user_email>")
        print("Example: python make_admin.py admin@example.com")
        sys.exit(1)
    
    email = sys.argv[1]
    if make_admin(email):
        print("Done!")
    else:
        sys.exit(1)

