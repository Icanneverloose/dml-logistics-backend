from flask import Blueprint, request, jsonify, session
from datetime import datetime
import uuid
import json
import os

chat_bp = Blueprint('chat_bp', __name__)

# File paths for data storage
CHAT_SESSIONS_FILE = os.path.join('data', 'chat_sessions.json')
CHAT_MESSAGES_FILE = os.path.join('data', 'chat_messages.json')

# Ensure data directory exists
if not os.path.exists('data'):
    os.makedirs('data')

# Helper: Load chat sessions from file
def load_chat_sessions():
    if not os.path.exists(CHAT_SESSIONS_FILE):
        return {}
    try:
        with open(CHAT_SESSIONS_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}

# Helper: Save chat sessions to file
def save_chat_sessions(sessions):
    with open(CHAT_SESSIONS_FILE, 'w') as f:
        json.dump(sessions, f, indent=2)

# Helper: Load chat messages from file
def load_chat_messages():
    if not os.path.exists(CHAT_MESSAGES_FILE):
        return {}
    try:
        with open(CHAT_MESSAGES_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}

# Helper: Save chat messages to file
def save_chat_messages(messages):
    with open(CHAT_MESSAGES_FILE, 'w') as f:
        json.dump(messages, f, indent=2)

# Helper: Get user ID from session (for admin endpoints)
def get_user_id():
    return session.get('user_id')

# Helper: Check if user is admin
def is_admin():
    user_id = get_user_id()
    if not user_id:
        return False
    try:
        users_file = os.path.join('data', 'users.json')
        if os.path.exists(users_file):
            with open(users_file, 'r') as f:
                users = json.load(f)
                user = users.get(user_id, {})
                role = user.get('role', '').lower()
                return role in ['admin', 'super admin', 'manager']
    except:
        pass
    return False

# 1. Create Chat Session
@chat_bp.route('/sessions', methods=['POST', 'OPTIONS'])
def create_chat_session():
    if request.method == 'OPTIONS':
        return jsonify({'ok': True}), 200
    
    try:
        data = request.get_json()
        email = data.get('email')
        name = data.get('name', 'Guest')
        
        if not email:
            return jsonify({'success': False, 'error': 'Email is required'}), 400
        
        sessions = load_chat_sessions()
        session_id = str(uuid.uuid4())
        
        session_data = {
            'id': session_id,
            'email': email,
            'name': name,
            'status': 'active',
            'createdAt': datetime.utcnow().isoformat(),
            'updatedAt': datetime.utcnow().isoformat(),
            'assignedAgent': None
        }
        
        sessions[session_id] = session_data
        save_chat_sessions(sessions)
        
        # Initialize empty messages for this session
        messages = load_chat_messages()
        if session_id not in messages:
            messages[session_id] = []
            save_chat_messages(messages)
        
        return jsonify({
            'success': True,
            'session': session_data
        }), 201
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# 2. Get Chat Session
@chat_bp.route('/sessions/<session_id>', methods=['GET', 'OPTIONS'])
def get_chat_session(session_id):
    if request.method == 'OPTIONS':
        return jsonify({'ok': True}), 200
    
    try:
        sessions = load_chat_sessions()
        session_data = sessions.get(session_id)
        
        if not session_data:
            return jsonify({'success': False, 'error': 'Session not found'}), 404
        
        return jsonify({
            'success': True,
            'session': session_data
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# 3. Get All Chat Sessions (Admin only)
@chat_bp.route('/sessions', methods=['GET', 'OPTIONS'])
def get_all_chat_sessions():
    if request.method == 'OPTIONS':
        return jsonify({'ok': True}), 200
    
    try:
        # Check if user has admin access (support, manager, or super admin)
        user_id = get_user_id()
        if not user_id:
            return jsonify({'success': False, 'error': 'Unauthorized'}), 401
        
        # Check user role
        users_file = os.path.join('data', 'users.json')
        if not os.path.exists(users_file):
            return jsonify({'success': False, 'error': 'Unauthorized'}), 401
        
        with open(users_file, 'r') as f:
            users = json.load(f)
            user = users.get(user_id, {})
            role = user.get('role', '').lower()
            # Support, Manager, and Super Admin can access chat
            if role not in ['support', 'manager', 'admin', 'super admin', 'superadmin']:
                return jsonify({'success': False, 'error': 'Unauthorized'}), 401
        
        sessions = load_chat_sessions()
        messages = load_chat_messages()
        
        # Get filter parameters
        status_filter = request.args.get('status')
        email_filter = request.args.get('email')
        
        # Get current user email to filter sessions (only show sessions for logged-in user's email)
        user_id = get_user_id()
        current_user_email = None
        if user_id:
            try:
                users_file = os.path.join('data', 'users.json')
                if os.path.exists(users_file):
                    with open(users_file, 'r') as f:
                        users = json.load(f)
                        user = users.get(user_id, {})
                        current_user_email = user.get('email', '').lower()
            except:
                pass
        
        sessions_list = []
        for session_id, session_data in sessions.items():
            # Apply filters
            if status_filter and status_filter != 'all' and session_data.get('status') != status_filter:
                continue
            if email_filter and email_filter.lower() not in session_data.get('email', '').lower():
                continue
            
            # For non-admin users, only show their own sessions
            # For admin users, show all sessions
            session_email = session_data.get('email', '').lower()
            if current_user_email and role not in ['admin', 'super admin', 'superadmin', 'manager', 'support']:
                if session_email != current_user_email:
                    continue
            
            # Get message count and last message
            session_messages = messages.get(session_id, [])
            last_message = session_messages[-1] if session_messages else None
            
            session_info = {
                'id': session_data.get('id'),
                'email': session_data.get('email'),
                'name': session_data.get('name'),
                'status': session_data.get('status', 'active'),
                'assignedAgent': session_data.get('assignedAgent'),
                'createdAt': session_data.get('createdAt'),
                'updatedAt': session_data.get('updatedAt'),
                'messageCount': len(session_messages),
                'lastMessage': last_message.get('text', '') if last_message else '',
                'lastMessageTime': last_message.get('timestamp', '') if last_message else ''
            }
            sessions_list.append(session_info)
        
        # Sort by updatedAt (most recent first)
        sessions_list.sort(key=lambda x: x.get('updatedAt', ''), reverse=True)
        
        return jsonify({
            'success': True,
            'sessions': sessions_list
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# 4. Update Chat Session
@chat_bp.route('/sessions/<session_id>', methods=['PATCH', 'OPTIONS'])
def update_chat_session(session_id):
    if request.method == 'OPTIONS':
        return jsonify({'ok': True}), 200
    
    try:
        # Check if user is admin
        if not is_admin():
            return jsonify({'success': False, 'error': 'Unauthorized'}), 401
        
        sessions = load_chat_sessions()
        session_data = sessions.get(session_id)
        
        if not session_data:
            return jsonify({'success': False, 'error': 'Session not found'}), 404
        
        data = request.get_json()
        
        # Update status if provided
        if 'status' in data:
            session_data['status'] = data['status']
        
        # Update assigned agent if provided
        if 'assignedAgent' in data:
            session_data['assignedAgent'] = data['assignedAgent']
        
        session_data['updatedAt'] = datetime.utcnow().isoformat()
        sessions[session_id] = session_data
        save_chat_sessions(sessions)
        
        return jsonify({
            'success': True,
            'session': session_data
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# 5. Get Chat Messages
@chat_bp.route('/sessions/<session_id>/messages', methods=['GET', 'OPTIONS'])
def get_chat_messages(session_id):
    if request.method == 'OPTIONS':
        return jsonify({'ok': True}), 200
    
    try:
        messages = load_chat_messages()
        session_messages = messages.get(session_id, [])
        
        # Sort messages by timestamp
        session_messages.sort(key=lambda x: x.get('timestamp', ''))
        
        return jsonify({
            'success': True,
            'messages': session_messages
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# 6. Send Chat Message
@chat_bp.route('/sessions/<session_id>/messages', methods=['POST', 'OPTIONS'])
def send_chat_message(session_id):
    if request.method == 'OPTIONS':
        return jsonify({'ok': True}), 200
    
    try:
        data = request.get_json()
        message_text = data.get('message')
        
        if not message_text:
            return jsonify({'success': False, 'error': 'Message is required'}), 400
        
        sessions = load_chat_sessions()
        session_data = sessions.get(session_id)
        
        if not session_data:
            return jsonify({'success': False, 'error': 'Session not found'}), 404
        
        messages = load_chat_messages()
        if session_id not in messages:
            messages[session_id] = []
        
        # Add user message
        user_message = {
            'id': str(uuid.uuid4()),
            'text': message_text,
            'sender': 'user',
            'timestamp': datetime.utcnow().isoformat()
        }
        messages[session_id].append(user_message)
        
        # Check if agent is active - if so, don't generate AI response
        # CRITICAL: Preserve the current session status - don't change it unless explicitly needed
        session_status = session_data.get('status', 'active')
        ai_response_text = None
        
        # Only generate AI response if no agent is active or assigned
        # Allow AI when status is 'active' (no agent) or 'ended' (chat ended, AI can resume)
        # Block AI when status is 'agent_active', 'agent_assigned', or 'waiting_agent'
        if session_status not in ['agent_active', 'agent_assigned', 'waiting_agent']:
            # If chat was ended, reset to active status to allow AI responses
            if session_status == 'ended':
                session_data['status'] = 'active'
                sessions[session_id] = session_data
                save_chat_sessions(sessions)  # Save immediately to persist the change
            # Generate AI response (simple rule-based for now)
            ai_response_text = generate_ai_response(message_text)
            
            # Add AI response
            ai_message = {
                'id': str(uuid.uuid4()),
                'text': ai_response_text,
                'sender': 'assistant',
                'timestamp': datetime.utcnow().isoformat()
            }
            messages[session_id].append(ai_message)
        # IMPORTANT: If agent is active, preserve the status - don't change it to 'active'
        # The status should remain 'agent_active' or 'agent_assigned' when agent is handling the chat
        
        save_chat_messages(messages)
        
        # Update session timestamp but PRESERVE the status (don't reset it)
        # Only update updatedAt, keep the status as-is
        session_data['updatedAt'] = datetime.utcnow().isoformat()
        # Ensure status is preserved - reload session to make sure we have latest status
        sessions[session_id] = session_data
        save_chat_sessions(sessions)
        
        return jsonify({
            'success': True,
            'response': ai_response_text,  # Will be None if agent is active
            'session': session_data
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# 7. Request Live Agent
@chat_bp.route('/sessions/<session_id>/request-agent', methods=['POST', 'OPTIONS'])
def request_live_agent(session_id):
    if request.method == 'OPTIONS':
        return jsonify({'ok': True}), 200
    
    try:
        sessions = load_chat_sessions()
        session_data = sessions.get(session_id)
        
        if not session_data:
            return jsonify({'success': False, 'error': 'Session not found'}), 404
        
        # Update status to waiting_agent
        session_data['status'] = 'waiting_agent'
        session_data['updatedAt'] = datetime.utcnow().isoformat()
        sessions[session_id] = session_data
        save_chat_sessions(sessions)
        
        # Add system message (no emojis)
        messages = load_chat_messages()
        if session_id not in messages:
            messages[session_id] = []
        
        system_message = {
            'id': str(uuid.uuid4()),
            'text': 'Customer service will join the chat soon.',
            'sender': 'assistant',
            'timestamp': datetime.utcnow().isoformat()
        }
        messages[session_id].append(system_message)
        save_chat_messages(messages)
        
        return jsonify({
            'success': True,
            'session': session_data
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# 8. Send Agent Message (Admin only)
@chat_bp.route('/sessions/<session_id>/agent-message', methods=['POST', 'OPTIONS'])
def send_agent_message(session_id):
    if request.method == 'OPTIONS':
        return jsonify({'ok': True}), 200
    
    try:
        # Check if user is admin
        if not is_admin():
            return jsonify({'success': False, 'error': 'Unauthorized'}), 401
        
        data = request.get_json()
        message_text = data.get('message')
        
        if not message_text:
            return jsonify({'success': False, 'error': 'Message is required'}), 400
        
        sessions = load_chat_sessions()
        session_data = sessions.get(session_id)
        
        if not session_data:
            return jsonify({'success': False, 'error': 'Session not found'}), 404
        
        # Update session to agent_active
        session_data['status'] = 'agent_active'
        session_data['updatedAt'] = datetime.utcnow().isoformat()
        
        # Get agent name from request or use default
        agent_name = data.get('agent_name')
        if not agent_name:
            # Try to get from user data
            user_id = get_user_id()
            if user_id:
                try:
                    users_file = os.path.join('data', 'users.json')
                    if os.path.exists(users_file):
                        with open(users_file, 'r') as f:
                            users = json.load(f)
                            user = users.get(user_id, {})
                            agent_name = user.get('name', 'Admin')
                except:
                    agent_name = 'Admin'
            else:
                agent_name = 'Admin'
        
        session_data['assignedAgent'] = agent_name
        sessions[session_id] = session_data
        save_chat_sessions(sessions)
        
        # Check if this is the first agent message (agent just joined)
        messages = load_chat_messages()
        if session_id not in messages:
            messages[session_id] = []
        
        # Check if agent just joined (no previous agent messages)
        has_agent_messages = any(msg.get('sender') == 'agent' for msg in messages[session_id])
        
        # If agent just joined, add "joined the chat" message first
        if not has_agent_messages and message_text != f"{agent_name} joined the chat.":
            join_message = {
                'id': str(uuid.uuid4()),
                'text': f"{agent_name} joined the chat.",
                'sender': 'agent',
                'timestamp': datetime.utcnow().isoformat()
            }
            messages[session_id].append(join_message)
        
        # Add agent message
        agent_message = {
            'id': str(uuid.uuid4()),
            'text': message_text,
            'sender': 'agent',
            'timestamp': datetime.utcnow().isoformat()
        }
        messages[session_id].append(agent_message)
        save_chat_messages(messages)
        
        return jsonify({
            'success': True,
            'message': agent_message,
            'session': session_data
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# 9. End Chat Session
@chat_bp.route('/sessions/<session_id>/end', methods=['POST', 'OPTIONS'])
def end_chat_session(session_id):
    if request.method == 'OPTIONS':
        return jsonify({'ok': True}), 200
    
    try:
        # Check if user is admin
        if not is_admin():
            return jsonify({'success': False, 'error': 'Unauthorized'}), 401
        
        sessions = load_chat_sessions()
        session_data = sessions.get(session_id)
        
        if not session_data:
            return jsonify({'success': False, 'error': 'Session not found'}), 404
        
        # Update status to ended
        session_data['status'] = 'ended'
        session_data['updatedAt'] = datetime.utcnow().isoformat()
        sessions[session_id] = session_data
        save_chat_sessions(sessions)
        
        return jsonify({
            'success': True,
            'session': session_data
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# 10. Delete Chat Session (Admin only)
@chat_bp.route('/sessions/<session_id>/delete', methods=['POST', 'DELETE', 'OPTIONS'])
def delete_chat_session(session_id):
    if request.method == 'OPTIONS':
        # Handle CORS preflight request - validate origin against allowed list
        origin = request.headers.get('Origin')
        allowed_origins = [
            'http://localhost:3000',
            'http://127.0.0.1:3000',
            'http://localhost:5000',
            'http://127.0.0.1:5000'
        ]
        
        # Check if origin is in allowed list or if it's None (for same-origin requests)
        if origin in allowed_origins or origin is None:
            response = jsonify({'ok': True})
            if origin:
                response.headers.add('Access-Control-Allow-Origin', origin)
            response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization')
            response.headers.add('Access-Control-Allow-Methods', 'POST, DELETE, OPTIONS')
            response.headers.add('Access-Control-Allow-Credentials', 'true')
            response.headers.add('Access-Control-Max-Age', '3600')
            return response, 200
        else:
            # Origin not allowed
            return jsonify({'error': 'Origin not allowed'}), 403
    
    try:
        # Check if user has admin access (support, manager, or super admin)
        user_id = get_user_id()
        if not user_id:
            return jsonify({'success': False, 'error': 'Unauthorized'}), 401
        
        # Check user role - allow support, manager, admin, and super admin
        users_file = os.path.join('data', 'users.json')
        if not os.path.exists(users_file):
            return jsonify({'success': False, 'error': 'Unauthorized'}), 401
        
        with open(users_file, 'r') as f:
            users = json.load(f)
            user = users.get(user_id, {})
            role = user.get('role', '').lower()
            # Support, Manager, and Super Admin can delete conversations
            if role not in ['support', 'manager', 'admin', 'super admin', 'superadmin']:
                return jsonify({'success': False, 'error': 'Unauthorized'}), 401
        
        sessions = load_chat_sessions()
        messages = load_chat_messages()
        
        if session_id not in sessions:
            return jsonify({'success': False, 'error': 'Session not found'}), 404
        
        # Delete session
        del sessions[session_id]
        save_chat_sessions(sessions)
        
        # Delete all messages for this session
        if session_id in messages:
            del messages[session_id]
            save_chat_messages(messages)
        
        return jsonify({
            'success': True,
            'message': 'Conversation deleted successfully'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Helper: Generate AI response (simple rule-based)
def generate_ai_response(user_input):
    """Simple rule-based AI response generator (no emojis, includes URLs)"""
    user_input_lower = user_input.lower()
    
    # Track package queries
    if any(word in user_input_lower for word in ['track', 'tracking', 'package', 'shipment']):
        return "To track your package, you can:\n\n1. Visit the Track page: https://dmllogistics.com/track\n2. Enter your tracking number (format: DML followed by 8 digits)\n3. View real-time updates on your shipment status\n\nYou can also track packages from your dashboard if you're logged in: https://dmllogistics.com/dashboard/shipment-history\n\nWould you like help with anything else?"
    
    # Shipping information
    if any(word in user_input_lower for word in ['shipping', 'delivery', 'ship']):
        return "DML Logistics offers various shipping options:\n\nExpress Delivery: 1-2 business days\nStandard Shipping: 3-5 business days\nInternational: 7-14 business days\n\nWe serve 50+ countries worldwide with 99.9% on-time delivery. Learn more about our services: https://dmllogistics.com/services\n\nNeed more specific information?"
    
    # Account/Login queries
    if any(word in user_input_lower for word in ['login', 'sign in', 'account']):
        return "You can sign in or create an account:\n\n1. Visit the Sign In page: https://dmllogistics.com/auth/signin\n2. Click 'Sign In' in the header\n3. New users can click 'Sign Up' to create an account: https://dmllogistics.com/auth/signup\n\nOnce logged in, you'll have access to your dashboard, shipment history, and more. Need help with registration?"
    
    # Pricing queries
    if any(word in user_input_lower for word in ['price', 'cost', 'rate', 'fee']):
        return "Our pricing is competitive and transparent with no hidden fees. Shipping costs depend on:\n\n• Package weight and dimensions\n• Destination\n• Service type (Express, Standard, etc.)\n• Insurance options\n\nFor a custom quote, please contact our sales team through the Contact page: https://dmllogistics.com/contact or use the Get Quote feature. Would you like to register a package?"
    
    # Service information
    if any(word in user_input_lower for word in ['service', 'services', 'what do you offer']):
        return "DML Logistics provides comprehensive logistics solutions:\n\nExpress Shipping & Home Delivery\nFreight Services (Air, Sea, Land)\nWarehousing Solutions\nSupply Chain Management\nInternational Shipping\n\nVisit our Services page to learn more: https://dmllogistics.com/services\n\nWhich service interests you most?"
    
    # Contact/Support queries
    if any(word in user_input_lower for word in ['contact', 'support', 'help', 'phone']):
        return "You can reach us through:\n\n1. Contact page: https://dmllogistics.com/contact\n2. Customer Support: Available 24/7\n3. Dashboard Help: If logged in, check 'Help & Support' in your dashboard: https://dmllogistics.com/dashboard\n\nWe're here to help with any questions or concerns. What would you like assistance with?"
    
    # Location queries
    if any(word in user_input_lower for word in ['where', 'location', 'address']):
        return "DML Logistics operates globally with:\n\nMain Office: 1234 Logistics Boulevard, Suite 500, New York, NY 10001\nService Coverage: 50+ countries worldwide\nDistribution Centers: Multiple locations across major regions\n\nWe have a vast network to serve you efficiently. Visit our contact page for more information: https://dmllogistics.com/contact"
    
    # Website/URL queries
    if any(word in user_input_lower for word in ['website', 'site', 'url', 'homepage']):
        return "Our main website is: https://dmllogistics.com\n\nKey pages:\n• Home: https://dmllogistics.com\n• Services: https://dmllogistics.com/services\n• Track Package: https://dmllogistics.com/track\n• Contact: https://dmllogistics.com/contact\n• Sign In: https://dmllogistics.com/auth/signin\n\nIs there a specific page you're looking for?"
    
    # Greetings
    if any(word in user_input_lower for word in ['hello', 'hi', 'hey']):
        return "Hello! Welcome to DML Logistics. I'm here to help you with:\n\n• Package tracking\n• Shipping information\n• Account questions\n• Service inquiries\n• General support\n\nWhat can I assist you with today?"
    
    # Default response
    return "Thank you for your message! I'm here to help with logistics and shipping questions. You can ask me about:\n\n• Tracking packages - Visit https://dmllogistics.com/track\n• Shipping rates and services - Visit https://dmllogistics.com/services\n• Creating an account - Visit https://dmllogistics.com/auth/signup\n• Delivery times\n• Our services\n\nCould you provide more details about what you need help with?"

