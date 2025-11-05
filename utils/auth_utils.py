"""
Authentication and authorization utilities
"""
import json
import os
from flask import session

USERS_FILE = os.path.join('data', 'users.json')

def load_users():
    """Load users from JSON file"""
    if not os.path.exists(USERS_FILE):
        return {}
    with open(USERS_FILE, 'r') as f:
        return json.load(f)

def get_current_user():
    """Get current logged-in user from session"""
    user_id = session.get('user_id')
    if not user_id:
        return None
    
    users = load_users()
    return users.get(user_id)

def is_admin():
    """Check if current user is admin"""
    user = get_current_user()
    if not user:
        return False
    
    # Check if user has admin role
    role = user.get('role', 'user').lower()
    return role == 'admin'

def require_admin():
    """Check if current user has admin access (admin, super admin, manager, support) - returns (has_access, user)"""
    user = get_current_user()
    if not user:
        return False, None
    
    role = user.get('role', 'user').lower()
    # Admin roles: admin, super admin, superadmin, manager, support
    has_access = role in ['admin', 'super admin', 'superadmin', 'manager', 'support']
    return has_access, user

