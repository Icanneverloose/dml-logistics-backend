from flask import Blueprint, request, jsonify, session
from werkzeug.security import check_password_hash, generate_password_hash
import uuid
import json
import os
from datetime import datetime

user_bp = Blueprint('user_bp', __name__)

USERS_FILE = os.path.join('data', 'users.json')
SHIPMENTS_FILE = os.path.join('data', 'shipments.json')

# ✅ Helper: Load users from file
def load_users():
    if not os.path.exists(USERS_FILE):
        return {}
    with open(USERS_FILE, 'r') as f:
        return json.load(f)

# ✅ Helper: Save users to file
def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=2)

# ✅ Sign Up Route (POST)
@user_bp.route('/signup', methods=['POST', 'OPTIONS'])
def signup():
    if request.method == 'OPTIONS':
        return jsonify({'ok': True}), 200  # Handle CORS preflight
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    name = data.get('name')
    
    # Validate required fields
    if not email or not password or not name:
        return jsonify({'success': False, 'error': 'Email, password, and name are required'}), 400
    
    # Check if user already exists
    users = load_users()
    for user_id, user in users.items():
        if user.get('email') == email:
            return jsonify({'success': False, 'error': 'User with this email already exists'}), 409
    
    # Create new user
    user_id = str(uuid.uuid4())
    new_user = {
        'id': user_id,
        'email': email,
        'name': name,
        'password': generate_password_hash(password),
        'role': 'user',  # Default role is 'user', can be changed to 'admin'
        'created_at': str(datetime.utcnow())
    }
    
    users[user_id] = new_user
    save_users(users)
    
    # Log in the user automatically
    session['user_id'] = user_id
    
    # Return user data without password
    user_response = {k: v for k, v in new_user.items() if k != 'password'}
    return jsonify({'success': True, 'user': user_response, 'message': 'User registered successfully'}), 201

# ✅ Login Route (POST)
@user_bp.route('/login', methods=['POST', 'OPTIONS'])
def login():
    if request.method == 'OPTIONS':
        return jsonify({'ok': True}), 200  # Handle CORS preflight
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    users = load_users()
    for user_id, user in users.items():
        if user.get('email') == email and check_password_hash(user.get('password', ''), password):
            # Ensure user has a role (default to 'user' for existing users)
            if 'role' not in user:
                user['role'] = 'user'
                users[user_id] = user
                save_users(users)
            
            session['user_id'] = user_id
            # Return user data without password
            user_response = {k: v for k, v in user.items() if k != 'password'}
            return jsonify({'success': True, 'user': user_response})
    return jsonify({'success': False, 'error': 'Invalid email or password'}), 401

# ✅ Logout Route (POST)
@user_bp.route('/logout', methods=['POST', 'OPTIONS'])
def logout():
    if request.method == 'OPTIONS':
        return jsonify({'ok': True}), 200  # Handle CORS preflight
    session.pop('user_id', None)
    return jsonify({'success': True, 'message': 'Logged out successfully'})

# ✅ GET Profile Route
@user_bp.route('/profile', methods=['GET'])
def get_profile():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'error': 'Not logged in'}), 401

    users = load_users()
    user = users.get(user_id)
    if not user:
        return jsonify({'success': False, 'error': 'User not found'}), 404

    # Ensure user has a role (default to 'user' for existing users)
    if 'role' not in user:
        user['role'] = 'user'
        users[user_id] = user
        save_users(users)

    # Return user data without password
    user_response = {k: v for k, v in user.items() if k != 'password'}
    return jsonify({'success': True, 'user': user_response})

# ✅ GET Recent Shipments by Email
@user_bp.route('/recent-shipments', methods=['GET'])
def get_recent_shipments():
    email = request.args.get('email')
    if not email:
        return jsonify({'success': False, 'error': 'Email is required'}), 400

    if not os.path.exists(SHIPMENTS_FILE):
        return jsonify({'success': True, 'shipments': []})

    with open(SHIPMENTS_FILE, 'r') as f:
        shipments = json.load(f)

    user_shipments = [
        s for s in shipments
        if s.get('sender', {}).get('email') == email or s.get('receiver', {}).get('email') == email
    ]

    for s in user_shipments:
        if 'createdAt' not in s:
            s['createdAt'] = s.get('status_logs', [{}])[0].get('date', '')

    sorted_shipments = sorted(user_shipments, key=lambda x: x.get('createdAt', ''), reverse=True)
    return jsonify({'success': True, 'shipments': sorted_shipments[:5]})

# Helper: Check if user is admin
def is_admin(user_id):
    if not user_id:
        return False
    users = load_users()
    user = users.get(user_id, {})
    role = user.get('role', '').lower()
    return role in ['admin', 'super admin', 'manager']

# ✅ Admin: Get All Users
@user_bp.route('/admin/users', methods=['GET', 'OPTIONS'])
def get_admin_users():
    if request.method == 'OPTIONS':
        return jsonify({'ok': True}), 200
    
    user_id = session.get('user_id')
    if not user_id or not is_admin(user_id):
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    try:
        users = load_users()
        users_list = []
        
        for user_id_key, user in users.items():
            # Skip password field
            user_data = {k: v for k, v in user.items() if k != 'password'}
            
            # Map to expected format
            mapped_user = {
                'id': user_data.get('id', user_id_key),
                'name': user_data.get('name', 'Unknown'),
                'email': user_data.get('email', 'unknown@example.com'),
                'role': user_data.get('role', 'user'),
                'created_at': user_data.get('created_at', user_data.get('createdAt', datetime.utcnow().isoformat())),
                'last_login': user_data.get('last_login', user_data.get('lastLogin', None)),
                'status': user_data.get('status', 'Active')
            }
            
            # Map role to admin format if needed
            if mapped_user['role'].lower() == 'admin':
                mapped_user['role'] = 'Super Admin'
            elif mapped_user['role'].lower() == 'user':
                mapped_user['role'] = 'Support'
            
            users_list.append(mapped_user)
        
        # Sort by created_at (most recent first)
        users_list.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        
        return jsonify({
            'success': True,
            'users': users_list
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ✅ Admin: Create Admin User
@user_bp.route('/admin/users', methods=['POST', 'OPTIONS'])
def create_admin_user():
    if request.method == 'OPTIONS':
        return jsonify({'ok': True}), 200
    
    user_id = session.get('user_id')
    if not user_id or not is_admin(user_id):
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        name = data.get('name')
        role = data.get('role', 'Support')
        
        if not email or not password or not name:
            return jsonify({'success': False, 'error': 'Email, password, and name are required'}), 400
        
        users = load_users()
        
        # Check if user already exists
        for existing_user_id, existing_user in users.items():
            if existing_user.get('email') == email:
                return jsonify({'success': False, 'error': 'User with this email already exists'}), 409
        
        # Create new admin user
        new_user_id = str(uuid.uuid4())
        new_user = {
            'id': new_user_id,
            'email': email,
            'name': name,
            'password': generate_password_hash(password),
            'role': role.lower(),
            'created_at': datetime.utcnow().isoformat(),
            'status': 'Active'
        }
        
        users[new_user_id] = new_user
        save_users(users)
        
        # Return user data without password
        user_response = {k: v for k, v in new_user.items() if k != 'password'}
        return jsonify({
            'success': True,
            'user': user_response
        }), 201
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ✅ Admin: Update Admin User
@user_bp.route('/admin/users/<user_id_to_update>', methods=['PUT', 'OPTIONS'])
def update_admin_user(user_id_to_update):
    if request.method == 'OPTIONS':
        return jsonify({'ok': True}), 200
    
    user_id = session.get('user_id')
    if not user_id or not is_admin(user_id):
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    try:
        users = load_users()
        user_to_update = users.get(user_id_to_update)
        
        if not user_to_update:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        
        data = request.get_json()
        
        # Update fields if provided
        if 'name' in data:
            user_to_update['name'] = data['name']
        if 'email' in data:
            user_to_update['email'] = data['email']
        if 'role' in data:
            user_to_update['role'] = data['role'].lower()
        if 'status' in data:
            user_to_update['status'] = data['status']
        if 'password' in data and data['password']:
            user_to_update['password'] = generate_password_hash(data['password'])
        
        users[user_id_to_update] = user_to_update
        save_users(users)
        
        # Return user data without password
        user_response = {k: v for k, v in user_to_update.items() if k != 'password'}
        return jsonify({
            'success': True,
            'user': user_response
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ✅ Admin: Delete Admin User
@user_bp.route('/admin/users/<user_id_to_delete>', methods=['DELETE', 'OPTIONS'])
def delete_admin_user(user_id_to_delete):
    if request.method == 'OPTIONS':
        return jsonify({'ok': True}), 200
    
    user_id = session.get('user_id')
    if not user_id or not is_admin(user_id):
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    try:
        # Prevent deleting yourself
        if user_id_to_delete == user_id:
            return jsonify({'success': False, 'error': 'Cannot delete your own account'}), 400
        
        users = load_users()
        
        if user_id_to_delete not in users:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        
        # Delete user
        del users[user_id_to_delete]
        save_users(users)
        
        return jsonify({
            'success': True,
            'message': 'User deleted successfully'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500