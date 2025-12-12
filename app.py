from flask import Flask, session, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import models and blueprints
from models.shipment import db, Shipment
from models.status_log import StatusLog
from routes.shipments import shipment_bp
from routes.status import status_bp
from content.routes import content_bp
from routes.users import user_bp  # ✅ Make sure this file exists
from routes.chat import chat_bp  # ✅ Chat routes
from routes.contact import contact_bp  # ✅ Contact routes

# ✅ Create Flask app
app = Flask(__name__)  # ✅ Corrected here

# ✅ Secret key for sessions
app.secret_key = os.environ.get('SECRET_KEY', 'your-super-secret-key-change-in-production')
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_COOKIE_SAMESITE'] = 'None'  # Required for cross-origin
app.config['SESSION_COOKIE_SECURE'] = True      # Required for HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True    # Security
app.config['SESSION_COOKIE_DOMAIN'] = None      # Allow cross-domain cookies
app.config['SESSION_COOKIE_NAME'] = 'dml_session'  # Custom session name
app.config['PERMANENT_SESSION_LIFETIME'] = 86400  # 24 hours session

# ✅ Enable CORS for React frontend
# Get frontend URL from environment variable or default to localhost
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000")

CORS(app,
     supports_credentials=True,
     origins=[
         "https://dmllogisticsxpress.com",        # Your custom domain
         "https://www.dmllogisticsxpress.com",    # With www subdomain
         "https://dmlmainlogistics.netlify.app",  # Netlify default URL
         "https://*.netlify.app",                  # Netlify preview deployments
        "http://localhost:3000",                  # Local development
        "http://localhost:3001",                  # Local development (alternative port)
        "http://localhost:5173",                  # Vite dev server
         "http://localhost:5000",                  # Local backend
         "http://127.0.0.1:5000",                  # Alternative localhost
         FRONTEND_URL  # Environment variable fallback
     ],
     allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
     methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
)

# ✅ Database configuration - support both SQLite (local) and PostgreSQL (Render)
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL:
    # Check if it's a PostgreSQL URL (postgres:// or postgresql://)
    if DATABASE_URL.startswith('postgres://'):
        # SQLAlchemy needs postgresql:// not postgres://
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
    elif DATABASE_URL.startswith('postgresql://'):
        # Already in correct format
        pass
    else:
        # If DATABASE_URL is set but doesn't start with postgres, use it anyway (might be custom format)
        pass
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
else:
    # Use SQLite for local development (only if DATABASE_URL is not set)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# #region agent log
import json
import os
import time
def _debug_log(hypothesis_id, location, message, data=None):
    try:
        log_entry = {
            "sessionId": "debug-session",
            "runId": "run1",
            "hypothesisId": hypothesis_id,
            "location": location,
            "message": message,
            "data": data or {},
            "timestamp": time.time() * 1000
        }
        # Write to both file (local) and console (Render)
        log_json = json.dumps(log_entry)
        print(f"🔍 DEBUG [{hypothesis_id}]: {location} - {message} - {json.dumps(data) if data else '{}'}")
        # Try file logging (works locally)
        try:
            log_path = os.path.join(os.path.dirname(__file__), '.cursor', 'debug.log')
            os.makedirs(os.path.dirname(log_path), exist_ok=True)
            with open(log_path, 'a', encoding='utf-8') as f:
                f.write(log_json + '\n')
        except: pass
    except Exception as e:
        print(f"DEBUG_LOG_ERROR: {e}")
# #endregion

# ✅ Create database tables if they don't exist
with app.app_context():
    try:
        # #region agent log
        _debug_log("A", "app.py:71", "Database initialization start", {"db_uri": app.config.get('SQLALCHEMY_DATABASE_URI', 'unknown').split('@')[-1] if '@' in str(app.config.get('SQLALCHEMY_DATABASE_URI', '')) else 'local'})
        # #endregion
        db.create_all()
        print("✅ Database tables initialized")
        # #region agent log
        _debug_log("A", "app.py:74", "Database tables created successfully")
        # #endregion
    except Exception as e:
        print(f"⚠️ Database initialization note: {e}")
        # #region agent log
        _debug_log("A", "app.py:77", "Database initialization failed", {"error": str(e)})
        # #endregion

# ✅ Register blueprints - status_bp first to avoid route conflicts
# status_bp handles /<tracking_number>/status (GET and PUT)
# shipment_bp handles other shipment routes
app.register_blueprint(status_bp, url_prefix='/api/shipments')
app.register_blueprint(shipment_bp, url_prefix='/api/shipments')
app.register_blueprint(content_bp, url_prefix='/api/content')
app.register_blueprint(user_bp, url_prefix='/api/user')
app.register_blueprint(chat_bp, url_prefix='/api/chat')  # ✅ Chat routes
app.register_blueprint(contact_bp, url_prefix='/api/contact')  # ✅ Contact routes

# ✅ Register admin routes (admin endpoints need to be at /api/admin/users)
@app.route('/api/admin/users', methods=['GET', 'POST', 'OPTIONS'])
def admin_users_handler():
    """Route handler for admin users endpoints"""
    from flask import session
    from routes.users import load_users
    from werkzeug.security import generate_password_hash
    import uuid
    from datetime import datetime
    
    if request.method == 'OPTIONS':
        return jsonify({'ok': True}), 200
    
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    # Check if user is admin
    users = load_users()
    user = users.get(user_id, {})
    role = user.get('role', '').lower()
    if role not in ['admin', 'super admin', 'manager']:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    if request.method == 'GET':
        try:
            users_list = []
            for user_id_key, user_data in users.items():
                # Skip password field
                user_info = {k: v for k, v in user_data.items() if k != 'password'}
                
                # Map to expected format
                mapped_user = {
                    'id': user_info.get('id', user_id_key),
                    'name': user_info.get('name', 'Unknown'),
                    'email': user_info.get('email', 'unknown@example.com'),
                    'role': user_info.get('role', 'user'),
                    'created_at': user_info.get('created_at', user_info.get('createdAt', datetime.utcnow().isoformat())),
                    'last_login': user_info.get('last_login', user_info.get('lastLogin', None)),
                    'status': user_info.get('status', 'Active')
                }
                
                # Map role to admin format if needed
                role_lower = mapped_user['role'].lower()
                if role_lower == 'admin' or role_lower == 'super admin':
                    mapped_user['role'] = 'Super Admin'
                elif role_lower == 'manager':
                    mapped_user['role'] = 'Manager'
                elif role_lower == 'user':
                    mapped_user['role'] = 'Support'
                else:
                    mapped_user['role'] = 'Support'  # Default
                
                users_list.append(mapped_user)
            
            # Sort by created_at (most recent first)
            users_list.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            
            return jsonify({
                'success': True,
                'users': users_list
            })
        except Exception as e:
            import traceback
            print(f"Error in get_admin_users: {str(e)}")
            print(traceback.format_exc())
            return jsonify({'success': False, 'error': str(e)}), 500
    
    elif request.method == 'POST':
        try:
            data = request.get_json()
            email = data.get('email')
            password = data.get('password')
            name = data.get('name')
            role = data.get('role', 'Support')
            
            if not email or not password or not name:
                return jsonify({'success': False, 'error': 'Email, password, and name are required'}), 400
            
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
            from routes.users import save_users
            save_users(users)
            
            # Return user data without password
            user_response = {k: v for k, v in new_user.items() if k != 'password'}
            return jsonify({
                'success': True,
                'user': user_response
            }), 201
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/admin/users/<user_id_to_manage>', methods=['PUT', 'DELETE', 'OPTIONS'])
def admin_user_handler(user_id_to_manage):
    """Route handler for individual admin user operations"""
    from flask import session
    from routes.users import load_users, save_users
    from werkzeug.security import generate_password_hash
    
    if request.method == 'OPTIONS':
        return jsonify({'ok': True}), 200
    
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    # Check if user is admin
    users = load_users()
    user = users.get(user_id, {})
    role = user.get('role', '').lower()
    if role not in ['admin', 'super admin', 'manager']:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    if request.method == 'PUT':
        try:
            user_to_update = users.get(user_id_to_manage)
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
            
            users[user_id_to_manage] = user_to_update
            save_users(users)
            
            # Return user data without password
            user_response = {k: v for k, v in user_to_update.items() if k != 'password'}
            return jsonify({
                'success': True,
                'user': user_response
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    elif request.method == 'DELETE':
        try:
            # Prevent deleting yourself
            if user_id_to_manage == user_id:
                return jsonify({'success': False, 'error': 'Cannot delete your own account'}), 400
            
            if user_id_to_manage not in users:
                return jsonify({'success': False, 'error': 'User not found'}), 404
            
            # Delete user
            del users[user_id_to_manage]
            save_users(users)
            
            return jsonify({
                'success': True,
                'message': 'User deleted successfully'
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

# ✅ Admin: Get Frontend Customers (non-admin users)
@app.route('/api/admin/customers', methods=['GET', 'OPTIONS'])
def get_frontend_customers():
    """Get all frontend users (exclude admin, super admin, manager, support roles)"""
    from flask import session
    from routes.users import load_users
    
    if request.method == 'OPTIONS':
        return jsonify({'ok': True}), 200
    
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    # Check if user is admin
    users = load_users()
    user = users.get(user_id, {})
    role = user.get('role', '').lower()
    if role not in ['admin', 'super admin', 'manager', 'support']:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    try:
        customers_list = []
        
        for user_id_key, user_data in users.items():
            # Skip password field
            user_info = {k: v for k, v in user_data.items() if k != 'password'}
            
            # Get user role and check if it's a frontend user (not admin)
            user_role = (user_info.get('role', 'user') or 'user').lower()
            
            # Exclude admin roles - only include frontend users
            if user_role not in ['admin', 'super admin', 'superadmin', 'manager', 'support']:
                # Map to customer format (only name and email)
                customer = {
                    'id': user_info.get('id', user_id_key),
                    'name': user_info.get('name', 'Unknown'),
                    'email': user_info.get('email', 'unknown@example.com')
                }
                customers_list.append(customer)
        
        # Sort by name alphabetically
        customers_list.sort(key=lambda x: x.get('name', '').lower())
        
        return jsonify({
            'success': True,
            'customers': customers_list
        })
    except Exception as e:
        import traceback
        print(f"Error in get_frontend_customers: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500

# ✅ Test admin users endpoint
@app.route('/api/admin/users/test', methods=['GET'])
def test_admin_users():
    """Test endpoint to check if admin users route is accessible"""
    from flask import session
    from routes.users import load_users
    return jsonify({
        'success': True,
        'message': 'Admin users endpoint is accessible',
        'session_user_id': session.get('user_id'),
        'total_users': len(load_users())
    })

# ✅ Health check route
@app.route('/api/ping')
def ping():
    return {'message': '✅ Backend is live and working!'}

# ✅ Diagnostic endpoint to check database status
@app.route('/api/diagnose', methods=['GET'])
def diagnose():
    """Diagnostic endpoint to check database status"""
    from models.shipment import Shipment
    from models.status_log import StatusLog
    from sqlalchemy import text
    import os
    
    diagnostics = {
        'database_url_set': bool(os.environ.get('DATABASE_URL')),
        'database_type': 'PostgreSQL' if os.environ.get('DATABASE_URL') else 'SQLite',
        'shipments_count': 0,
        'status_logs_count': 0,
        'sample_tracking_numbers': [],
        'recent_shipments': [],
        'database_connection': 'unknown'
    }
    
    try:
        with app.app_context():
            # Test database connection
            try:
                db.engine.connect()
                diagnostics['database_connection'] = 'success'
            except Exception as conn_error:
                diagnostics['database_connection'] = f'failed: {str(conn_error)}'
            
            # Count shipments
            result = db.session.execute(text('SELECT COUNT(*) FROM shipments'))
            diagnostics['shipments_count'] = result.scalar() or 0
            
            # Count status logs
            result = db.session.execute(text('SELECT COUNT(*) FROM status_logs'))
            diagnostics['status_logs_count'] = result.scalar() or 0
            
            # Get sample tracking numbers
            if diagnostics['shipments_count'] > 0:
                result = db.session.execute(text('SELECT tracking_number FROM shipments LIMIT 10'))
                diagnostics['sample_tracking_numbers'] = [row[0] for row in result.fetchall()]
                
                # Get recent shipments
                result = db.session.execute(text('''
                    SELECT tracking_number, status, date_registered 
                    FROM shipments 
                    ORDER BY date_registered DESC 
                    LIMIT 5
                '''))
                for row in result.fetchall():
                    diagnostics['recent_shipments'].append({
                        'tracking_number': row[0],
                        'status': row[1],
                        'date_registered': str(row[2]) if row[2] else None
                    })
    except Exception as e:
        diagnostics['error'] = str(e)
        import traceback
        diagnostics['traceback'] = traceback.format_exc()
    
    return jsonify(diagnostics)

# ✅ Debug: Check Foreign Key Constraints
@app.route('/api/debug/check-constraints', methods=['GET'])
def check_constraints():
    """Check foreign key constraints - diagnostic endpoint"""
    from sqlalchemy import text
    
    try:
        # Detect database type
        db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
        is_postgres = 'postgresql' in db_uri.lower() or 'postgres' in db_uri.lower()
        is_sqlite = 'sqlite' in db_uri.lower()
        
        database_info = {
            'database_uri_preview': db_uri.split('@')[-1] if '@' in db_uri else 'local/sqlite',
            'database_type': 'PostgreSQL' if is_postgres else ('SQLite' if is_sqlite else 'Unknown'),
            'env_database_url_set': bool(os.environ.get('DATABASE_URL'))
        }
        
        if is_sqlite:
            # SQLite doesn't have information_schema, use pragma instead
            query = text("PRAGMA foreign_key_list(status_logs)")
            result = db.session.execute(query)
            constraints = []
            for row in result:
                # SQLite pragma returns: id, seq, table, from, to, on_update, on_delete, match
                constraints.append({
                    'constraint_name': f'fk_{row[2]}_{row[3]}',  # table_from
                    'table_name': 'status_logs',
                    'column_name': row[3],  # from column
                    'foreign_table_name': row[2],  # referenced table
                    'foreign_column_name': row[4],  # to column
                    'delete_rule': row[6] if len(row) > 6 else 'NO ACTION',  # on_delete
                    'update_rule': row[5] if len(row) > 5 else 'NO ACTION'  # on_update
                })
            
            return jsonify({
                'success': True,
                'database_info': database_info,
                'constraints': constraints,
                'warning': '⚠️ You are using SQLite! SQLite files on Render are EPHEMERAL and reset on restart. This is why shipments disappear!',
                'message': 'Switch to PostgreSQL to persist data. Check delete_rule - if it says CASCADE, that might also cause issues.'
            })
        elif is_postgres:
            # PostgreSQL query
            query = text("""
                SELECT 
                    tc.constraint_name, 
                    tc.table_name, 
                    kcu.column_name,
                    ccu.table_name AS foreign_table_name,
                    ccu.column_name AS foreign_column_name,
                    rc.delete_rule,
                    rc.update_rule
                FROM information_schema.table_constraints AS tc 
                JOIN information_schema.key_column_usage AS kcu
                  ON tc.constraint_name = kcu.constraint_name
                JOIN information_schema.constraint_column_usage AS ccu
                  ON ccu.constraint_name = tc.constraint_name
                JOIN information_schema.referential_constraints AS rc
                  ON rc.constraint_name = tc.constraint_name
                WHERE tc.constraint_type = 'FOREIGN KEY' 
                  AND (tc.table_name = 'status_logs' OR tc.table_name = 'shipments')
            """)
            
            result = db.session.execute(query)
            constraints = []
            for row in result:
                constraints.append({
                    'constraint_name': row[0],
                    'table_name': row[1],
                    'column_name': row[2],
                    'foreign_table_name': row[3],
                    'foreign_column_name': row[4],
                    'delete_rule': row[5],
                    'update_rule': row[6]
                })
            
            return jsonify({
                'success': True,
                'database_info': database_info,
                'constraints': constraints,
                'message': 'Check delete_rule - if it says CASCADE, that might be causing automatic deletions'
            })
        else:
            return jsonify({
                'success': False,
                'database_info': database_info,
                'error': 'Unknown database type'
            })
            
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

# ✅ Homepage (for Render)
@app.route('/')
def home():
    return '✅ Logistics Backend Running on Render!'

# ✅ Run the app
if __name__ == '__main__':  # ✅ Fixed here too
    port = int(os.environ.get("PORT", 5000))
    # Support up to 15 concurrent sessions
    app.run(host='0.0.0.0', port=port, threaded=True, processes=1)