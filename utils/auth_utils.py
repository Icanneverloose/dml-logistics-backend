"""
Authentication and authorization utilities
"""
import json
import os
import jwt
from flask import session, request

USERS_FILE = os.path.join('data', 'users.json')

def load_users():
    """Load users from JSON file"""
    if not os.path.exists(USERS_FILE):
        return {}
    with open(USERS_FILE, 'r') as f:
        return json.load(f)

def verify_token(token):
    """Verify JWT token and return user_id"""
    try:
        secret_key = os.environ.get('SECRET_KEY', 'your-super-secret-key-change-in-production')
        payload = jwt.decode(token, secret_key, algorithms=['HS256'])
        return payload.get('user_id')
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def get_user_id_from_request():
    """Get user_id from session (desktop) or Authorization header (mobile)"""
    # Try session first (for desktop compatibility)
    user_id = session.get('user_id')
    if user_id:
        return user_id
    
    # Try Authorization header (for mobile)
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.startswith('Bearer '):
        token = auth_header.split(' ')[1]
        user_id = verify_token(token)
        if user_id:
            return user_id
    
    return None

def get_current_user():
    """Get current logged-in user from session or token"""
    user_id = get_user_id_from_request()
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

