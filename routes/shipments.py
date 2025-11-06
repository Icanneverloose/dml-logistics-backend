from flask import Blueprint, request, jsonify, session
from models.shipment import db, Shipment
from utils.pdf_generator import generate_pdf_receipt
from utils.auth_utils import require_admin
from datetime import datetime
import uuid
import json
import os

shipment_bp = Blueprint('shipment_bp', __name__)

@shipment_bp.route('', methods=['POST', 'OPTIONS'])  # Accept POST and OPTIONS
@shipment_bp.route('/', methods=['POST', 'OPTIONS'])  # Accept POST and OPTIONS
def create_shipment():
    if request.method == 'OPTIONS':
        return jsonify({'ok': True}), 200  # Handle CORS preflight

    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400

        # Debug: Print incoming data
        print(f"Received shipment data: {data}")

        # Extract shipment data from the request
        sender_name = data.get('sender_name')
        sender_email = data.get('sender_email')
        sender_phone = data.get('sender_phone')
        sender_address = data.get('sender_address')
        receiver_name = data.get('receiver_name')
        receiver_phone = data.get('receiver_phone')
        receiver_address = data.get('receiver_address')
        package_type = data.get('package_type')
        weight = data.get('weight')
        shipment_cost = data.get('shipment_cost')
        estimated_delivery_date = data.get('estimated_delivery_date')

        # Validate required fields
        required_fields = ['sender_name', 'sender_email', 'sender_phone', 'sender_address', 
                          'receiver_name', 'receiver_phone', 'receiver_address', 'package_type', 
                          'weight', 'shipment_cost']
        
        missing_fields = []
        for field in required_fields:
            value = data.get(field)
            if value is None or (isinstance(value, str) and value.strip() == ''):
                missing_fields.append(field)
        
        if missing_fields:
            return jsonify({'success': False, 'error': f'Missing required fields: {", ".join(missing_fields)}'}), 400

        # Generate a unique tracking number (simple example)
        tracking_number = f'TRK{str(uuid.uuid4())[:8].upper()}'

        # Convert estimated_delivery_date to datetime if provided
        est_delivery = None
        if estimated_delivery_date:
            try:
                est_delivery = datetime.strptime(estimated_delivery_date, '%Y-%m-%d')
            except Exception:
                est_delivery = None

        # Get current user info (if logged in)
        created_by = None
        created_by_email = None
        user_id = session.get('user_id')
        
        # Debug logging
        print(f"Session user_id: {user_id}")
        print(f"Session data: {dict(session)}")
        
        if user_id:
            # Load user data to get email
            users_file = os.path.join('data', 'users.json')
            if os.path.exists(users_file):
                try:
                    with open(users_file, 'r') as f:
                        users = json.load(f)
                        user = users.get(user_id, {})
                        created_by = user_id
                        created_by_email = user.get('email', None)
                        print(f"Found user: {user.get('name', 'Unknown')} ({user.get('email', 'No email')})")
                except Exception as e:
                    print(f"Error loading user data: {e}")
                    pass
        else:
            print("No user_id in session - shipment will be created without creator tracking")

        # Always use raw SQL to avoid issues with missing created_by columns
        from sqlalchemy import inspect, text
        use_raw_sql = True  # Always use raw SQL to be safe
        db_columns = []
        
        try:
            # Get actual table columns from database
            inspector = inspect(db.engine)
            db_columns = [col['name'] for col in inspector.get_columns('shipments')]
            print(f"Database columns found: {db_columns}")
        except Exception as inspect_error:
            print(f"Could not inspect table: {inspect_error}. Will exclude created_by columns.")
            db_columns = []
        
        # Use raw SQL to insert only existing columns
        insert_data = {
            'id': str(uuid.uuid4()),
            'tracking_number': tracking_number,
            'sender_name': sender_name,
            'sender_email': sender_email,
            'sender_phone': sender_phone,
            'sender_address': sender_address,
            'receiver_name': receiver_name,
            'receiver_phone': receiver_phone,
            'receiver_address': receiver_address,
            'package_type': package_type,
            'weight': weight,
            'shipment_cost': shipment_cost,
            'status': 'Registered',
            'date_registered': datetime.utcnow()
        }
        if est_delivery:
            insert_data['estimated_delivery_date'] = est_delivery
        
        # Filter to only columns that exist in database
        if db_columns:
            # Only include columns that actually exist in the database
            filtered_data = {k: v for k, v in insert_data.items() if k in db_columns}
        else:
            # If we can't inspect, exclude created_by fields explicitly
            filtered_data = {k: v for k, v in insert_data.items() if k not in ['created_by', 'created_by_email']}
        
        # Build SQL insert statement with proper escaping
        columns_str = ', '.join([f'"{col}"' for col in filtered_data.keys()])
        placeholders = ', '.join([':' + k for k in filtered_data.keys()])
        
        print(f"Inserting with columns: {list(filtered_data.keys())}")
        
        sql = text(f'INSERT INTO shipments ({columns_str}) VALUES ({placeholders})')
        db.session.execute(sql, filtered_data)
        db.session.commit()
        
        # Get the created shipment for PDF generation - use raw query
        result = db.session.execute(
            text('SELECT * FROM shipments WHERE tracking_number = :tracking_number'),
            {'tracking_number': tracking_number}
        ).first()
        
        if not result:
            raise Exception("Shipment was created but could not be retrieved")
        
        # Create a minimal shipment object from the result for PDF generation
        shipment = Shipment()
        shipment.id = result.id if hasattr(result, 'id') else filtered_data.get('id')
        shipment.tracking_number = tracking_number
        shipment.sender_name = result.sender_name if hasattr(result, 'sender_name') else sender_name
        shipment.sender_email = result.sender_email if hasattr(result, 'sender_email') else sender_email
        shipment.sender_phone = result.sender_phone if hasattr(result, 'sender_phone') else sender_phone
        shipment.sender_address = result.sender_address if hasattr(result, 'sender_address') else sender_address
        shipment.receiver_name = result.receiver_name if hasattr(result, 'receiver_name') else receiver_name
        shipment.receiver_phone = result.receiver_phone if hasattr(result, 'receiver_phone') else receiver_phone
        shipment.receiver_address = result.receiver_address if hasattr(result, 'receiver_address') else receiver_address
        shipment.package_type = result.package_type if hasattr(result, 'package_type') else package_type
        shipment.weight = result.weight if hasattr(result, 'weight') else weight
        shipment.shipment_cost = result.shipment_cost if hasattr(result, 'shipment_cost') else shipment_cost
        shipment.status = 'Registered'
        if hasattr(result, 'date_registered'):
            shipment.date_registered = result.date_registered
        
        print(f"Shipment created successfully using raw SQL: {tracking_number}")

        # Generate PDF receipt and save the file path
        try:
            pdf_path = generate_pdf_receipt(shipment)
            if pdf_path:
                shipment.pdf_url = pdf_path
                db.session.commit()
        except Exception as e:
            print(f"PDF generation failed: {e}")
            # Continue without PDF if generation fails

        return jsonify({
            'success': True,
            'message': 'Shipment registered successfully!',
            'tracking_number': shipment.tracking_number,
            'pdf_url': shipment.pdf_url
        }), 201

    except Exception as e:
        db.session.rollback()
        error_msg = str(e)
        print(f"Error creating shipment: {error_msg}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False, 
            'error': f'Failed to create shipment: {error_msg}'
        }), 500

@shipment_bp.route('/all', methods=['GET'])
def get_all_shipments():
    # Require admin access to view all shipments
    is_admin_user, user_info = require_admin()
    if not is_admin_user:
        return jsonify({'success': False, 'error': 'Admin access required'}), 403
    
    # Always use raw SQL to avoid ORM column issues - simplified, no role filtering
    from sqlalchemy import text
    from datetime import datetime
    
    try:
        # Use raw SQL to fetch all shipments
        result = db.session.execute(text('SELECT * FROM shipments'))
        shipments_rows = result.fetchall()
        
        # Convert rows to shipment-like dicts
        shipments = []
        if shipments_rows:
            # Get column names from result
            column_names = result.keys()
            for row in shipments_rows:
                shipment_dict = {}
                # Handle both Row objects and tuples
                if hasattr(row, '_asdict'):
                    # Row object with _asdict method
                    shipment_dict = row._asdict()
                elif hasattr(row, '_mapping'):
                    # Row object with _mapping
                    shipment_dict = dict(row._mapping)
                else:
                    # Tuple - convert using column names
                    for i, col_name in enumerate(column_names):
                        shipment_dict[col_name] = row[i] if i < len(row) else None
                shipments.append(shipment_dict)
    except Exception as query_error:
        print(f"Query error: {query_error}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'Failed to fetch shipments: {str(query_error)}'}), 500
    
    shipment_list = []
    for s in shipments:
        # Always dict from raw SQL
        date_reg = s.get('date_registered')
        est_delivery = s.get('estimated_delivery_date')
        
        shipment_dict = {
            'id': s.get('id'),
            'tracking_number': s.get('tracking_number'),
            'sender_name': s.get('sender_name'),
            'sender_email': s.get('sender_email'),
            'sender_phone': s.get('sender_phone'),
            'sender_address': s.get('sender_address'),
            'receiver_name': s.get('receiver_name'),
            'receiver_phone': s.get('receiver_phone'),
            'receiver_address': s.get('receiver_address'),
            'package_type': s.get('package_type'),
            'weight': s.get('weight'),
            'shipment_cost': s.get('shipment_cost'),
            'status': s.get('status'),
            'date_registered': date_reg.isoformat() if date_reg and isinstance(date_reg, datetime) else (date_reg if date_reg else None),
            'estimated_delivery_date': est_delivery.strftime('%Y-%m-%d') if est_delivery and isinstance(est_delivery, datetime) else (str(est_delivery) if est_delivery else None),
            'pdf_url': s.get('pdf_url')
        }
        
        shipment_list.append(shipment_dict)
    return jsonify({'shipments': shipment_list, 'success': True})

# Generate/Download PDF (by tracking number or ID) - MUST be before /<identifier> routes
@shipment_bp.route('/<identifier>/pdf', methods=['GET', 'OPTIONS'])
def get_shipment_pdf(identifier):
    if request.method == 'OPTIONS':
        # Handle CORS preflight
        origin = request.headers.get('Origin')
        allowed_origins = [
            'http://localhost:3000',
            'http://127.0.0.1:3000',
            'http://localhost:5000',
            'http://127.0.0.1:5000'
        ]
        response = jsonify({'ok': True})
        if origin in allowed_origins or origin is None:
            if origin:
                response.headers.add('Access-Control-Allow-Origin', origin)
            response.headers.add('Access-Control-Allow-Methods', 'GET, OPTIONS')
            response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Accept, Authorization')
            response.headers.add('Access-Control-Allow-Credentials', 'true')
        return response, 200
    
    try:
        from sqlalchemy import text
        
        # Get shipment data (by tracking_number or ID)
        result = db.session.execute(
            text('SELECT * FROM shipments WHERE tracking_number = :identifier OR id = :identifier'),
            {'identifier': identifier}
        ).first()
        
        if not result:
            return jsonify({'success': False, 'error': 'Shipment not found'}), 404
        
        # Convert to dict
        if hasattr(result, '_asdict'):
            shipment_dict = result._asdict()
        elif hasattr(result, '_mapping'):
            shipment_dict = dict(result._mapping)
        else:
            shipment_dict = {}
            column_names = result.keys() if hasattr(result, 'keys') else []
            for i, col_name in enumerate(column_names):
                shipment_dict[col_name] = result[i] if i < len(result) else None
        
        # Create shipment object for PDF generation
        shipment = Shipment()
        shipment.id = shipment_dict.get('id')
        shipment.tracking_number = shipment_dict.get('tracking_number') or identifier
        shipment.sender_name = shipment_dict.get('sender_name', '')
        shipment.sender_email = shipment_dict.get('sender_email', '')
        shipment.sender_phone = shipment_dict.get('sender_phone', '')
        shipment.sender_address = shipment_dict.get('sender_address', '')
        shipment.receiver_name = shipment_dict.get('receiver_name', '')
        shipment.receiver_phone = shipment_dict.get('receiver_phone', '')
        shipment.receiver_address = shipment_dict.get('receiver_address', '')
        shipment.package_type = shipment_dict.get('package_type', '')
        shipment.weight = shipment_dict.get('weight', 0)
        shipment.shipment_cost = shipment_dict.get('shipment_cost', 0)
        shipment.status = shipment_dict.get('status', 'Registered')
        shipment.date_registered = shipment_dict.get('date_registered')
        shipment.estimated_delivery_date = shipment_dict.get('estimated_delivery_date')
        
        # Get tracking number or use identifier
        tracking_num = shipment_dict.get('tracking_number') or identifier
        
        # Check if PDF already exists
        pdf_url = shipment_dict.get('pdf_url')
        if pdf_url and os.path.exists(pdf_url):
            from flask import send_file, make_response
            response = make_response(send_file(pdf_url, mimetype='application/pdf', as_attachment=True, download_name=f'receipt-{tracking_num}.pdf'))
            # Add CORS headers
            origin = request.headers.get('Origin')
            if origin:
                response.headers.add('Access-Control-Allow-Origin', origin)
            response.headers.add('Access-Control-Allow-Credentials', 'true')
            return response
        
        # Generate new PDF
        pdf_path = generate_pdf_receipt(shipment)
        if pdf_path and os.path.exists(pdf_path):
            # Update PDF URL in database
            try:
                db.session.execute(
                    text('UPDATE shipments SET pdf_url = :pdf_url WHERE tracking_number = :identifier OR id = :identifier'),
                    {'pdf_url': pdf_path, 'identifier': identifier}
                )
                db.session.commit()
            except Exception as e:
                print(f"Failed to update PDF URL: {e}")
            
            from flask import send_file, make_response
            response = make_response(send_file(pdf_path, mimetype='application/pdf', as_attachment=True, download_name=f'receipt-{tracking_num}.pdf'))
            # Add CORS headers
            origin = request.headers.get('Origin')
            if origin:
                response.headers.add('Access-Control-Allow-Origin', origin)
            response.headers.add('Access-Control-Allow-Credentials', 'true')
            return response
        
        return jsonify({'success': False, 'error': 'Failed to generate PDF'}), 500
    except Exception as e:
        print(f"Error generating PDF: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

# Update shipment status (separate endpoint for status updates) - MUST be before /<identifier> routes
@shipment_bp.route('/<identifier>/status', methods=['PUT', 'PATCH', 'OPTIONS'])
def update_shipment_status(identifier):
    if request.method == 'OPTIONS':
        # Handle CORS preflight request
        origin = request.headers.get('Origin')
        allowed_origins = [
            'https://dmllogisticsxpress.com',        # Your main domain
            'https://www.dmllogisticsxpress.com',    # With www
            'https://dmlmainlogistics.netlify.app',  # Netlify URL
            'http://localhost:3000',                  # Local development
            'http://localhost:5173',                  # Vite dev server
            'http://127.0.0.1:3000',
            'http://localhost:5000',
            'http://127.0.0.1:5000'
        ]
        
                # Also allow Netlify preview deployments (*.netlify.app)
        is_netlify_preview = origin and '.netlify.app' in origin
        
        if origin in allowed_origins or is_netlify_preview or origin is None:
            response = jsonify({'ok': True})
            if origin:
                response.headers.add('Access-Control-Allow-Origin', origin)
            response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization')
            response.headers.add('Access-Control-Allow-Methods', 'PUT, PATCH, OPTIONS')
            response.headers.add('Access-Control-Allow-Credentials', 'true')
            response.headers.add('Access-Control-Max-Age', '3600')
            return response, 200
        else:
            return jsonify({'error': 'Origin not allowed'}), 403
    
    # Require admin access
    is_admin_user, user_info = require_admin()
    if not is_admin_user:
        return jsonify({'success': False, 'error': 'Admin access required'}), 403
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        status = data.get('status')
        if not status:
            return jsonify({'success': False, 'error': 'Status is required'}), 400
        
        from sqlalchemy import text, inspect
        
        # Check if shipment exists (by tracking_number or ID)
        result = db.session.execute(
            text('SELECT id FROM shipments WHERE tracking_number = :identifier OR id = :identifier'),
            {'identifier': identifier}
        ).first()
        
        if not result:
            return jsonify({'success': False, 'error': 'Shipment not found'}), 404
        
        # Update status
        update_data = {'status': status, 'identifier': identifier}
        update_query = 'UPDATE shipments SET status = :status WHERE tracking_number = :identifier OR id = :identifier'
        
        # Check if status_log column exists and add note if provided
        inspector = inspect(db.engine)
        db_columns = [col['name'] for col in inspector.get_columns('shipments')]
        
        if 'status_log' in db_columns and data.get('note'):
            # Add status log entry (as JSON string)
            import json
            status_log = json.dumps([{
                'status': status,
                'timestamp': datetime.utcnow().isoformat(),
                'location': data.get('location'),
                'coordinates': data.get('coordinates'),
                'note': data.get('note')
            }])
            update_data['status_log'] = status_log
            update_query = 'UPDATE shipments SET status = :status, status_log = :status_log WHERE tracking_number = :identifier OR id = :identifier'
        
        db.session.execute(text(update_query), update_data)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Status updated successfully'
        })
    except Exception as e:
        db.session.rollback()
        print(f"Error updating status: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

# Get single shipment by tracking number or ID
@shipment_bp.route('/<identifier>', methods=['GET'])
def get_shipment(identifier):
    try:
        from sqlalchemy import text
        result = db.session.execute(
            text('SELECT * FROM shipments WHERE tracking_number = :identifier OR id = :identifier'),
            {'identifier': identifier}
        ).first()
        
        if not result:
            return jsonify({'success': False, 'error': 'Shipment not found'}), 404
        
        # Convert to dict
        if hasattr(result, '_asdict'):
            shipment_dict = result._asdict()
        elif hasattr(result, '_mapping'):
            shipment_dict = dict(result._mapping)
        else:
            shipment_dict = {}
            column_names = result.keys() if hasattr(result, 'keys') else []
            for i, col_name in enumerate(column_names):
                shipment_dict[col_name] = result[i] if i < len(result) else None
        
        return jsonify({'success': True, 'shipment': shipment_dict})
    except Exception as e:
        print(f"Error fetching shipment: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Delete shipment (by tracking number or ID)
@shipment_bp.route('/<identifier>', methods=['DELETE', 'OPTIONS'])
def delete_shipment(identifier):
    if request.method == 'OPTIONS':
        # Handle CORS preflight - always return 200 for OPTIONS
        # Flask-CORS is configured globally, but we need to set headers manually when handling OPTIONS
        from flask import make_response
        response = make_response('', 200)
        origin = request.headers.get('Origin')
        allowed_origins = [
            'http://localhost:3000',
            'http://127.0.0.1:3000',
            'http://localhost:5000',
            'http://127.0.0.1:5000'
        ]
        # Always return 200 for OPTIONS, but only set CORS headers for allowed origins
        if origin in allowed_origins:
            response.headers['Access-Control-Allow-Origin'] = origin
            response.headers['Access-Control-Allow-Methods'] = 'DELETE, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
            response.headers['Access-Control-Allow-Credentials'] = 'true'
            response.headers['Access-Control-Max-Age'] = '3600'
        # If origin not in list, still return 200 but without CORS headers (browser will block anyway)
        return response
    
    # Require admin access
    is_admin_user, user_info = require_admin()
    if not is_admin_user:
        return jsonify({'success': False, 'error': 'Admin access required'}), 403
    
    try:
        from sqlalchemy import text
        
        # Try to find by tracking_number first, then by ID
        result = db.session.execute(
            text('SELECT id, tracking_number FROM shipments WHERE tracking_number = :identifier OR id = :identifier'),
            {'identifier': identifier}
        ).first()
        
        if not result:
            return jsonify({'success': False, 'error': 'Shipment not found'}), 404
        
        tracking_num = result.tracking_number if hasattr(result, 'tracking_number') else (result[1] if len(result) > 1 else identifier)
        
        # Delete the shipment
        db.session.execute(
            text('DELETE FROM shipments WHERE tracking_number = :identifier OR id = :identifier'),
            {'identifier': identifier}
        )
        db.session.commit()
        
        # Add CORS headers to response
        origin = request.headers.get('Origin')
        response = jsonify({
            'success': True,
            'message': f'Shipment {tracking_num or identifier} deleted successfully'
        })
        if origin:
            response.headers.add('Access-Control-Allow-Origin', origin)
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        return response
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting shipment: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

# Update shipment (by tracking number or ID)
@shipment_bp.route('/<identifier>', methods=['PUT', 'PATCH', 'OPTIONS'])
def update_shipment(identifier):
    if request.method == 'OPTIONS':
        # Handle CORS preflight request
        origin = request.headers.get('Origin')
        allowed_origins = [
            'http://localhost:3000',
            'http://127.0.0.1:3000',
            'http://localhost:5000',
            'http://127.0.0.1:5000'
        ]
        
        if origin in allowed_origins or origin is None:
            response = jsonify({'ok': True})
            if origin:
                response.headers.add('Access-Control-Allow-Origin', origin)
            response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization')
            response.headers.add('Access-Control-Allow-Methods', 'PUT, PATCH, OPTIONS')
            response.headers.add('Access-Control-Allow-Credentials', 'true')
            response.headers.add('Access-Control-Max-Age', '3600')
            return response, 200
        else:
            return jsonify({'error': 'Origin not allowed'}), 403
    
    # Require admin access
    is_admin_user, user_info = require_admin()
    if not is_admin_user:
        return jsonify({'success': False, 'error': 'Admin access required'}), 403
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        from sqlalchemy import text, inspect
        
        # Check if shipment exists (by tracking_number or ID)
        result = db.session.execute(
            text('SELECT * FROM shipments WHERE tracking_number = :identifier OR id = :identifier'),
            {'identifier': identifier}
        ).first()
        
        if not result:
            return jsonify({'success': False, 'error': 'Shipment not found'}), 404
        
        # Get available columns
        inspector = inspect(db.engine)
        db_columns = [col['name'] for col in inspector.get_columns('shipments')]
        
        # Build update query with only allowed fields
        allowed_fields = [
            'sender_name', 'sender_email', 'sender_phone', 'sender_address',
            'receiver_name', 'receiver_phone', 'receiver_address',
            'package_type', 'weight', 'shipment_cost', 'estimated_delivery_date'
        ]
        
        update_data = {}
        update_clauses = []
        
        for field in allowed_fields:
            if field in data and field in db_columns:
                update_data[field] = data[field]
                update_clauses.append(f'"{field}" = :{field}')
        
        if not update_clauses:
            return jsonify({'success': False, 'error': 'No valid fields to update'}), 400
        
        # Add identifier to update_data for WHERE clause
        update_data['identifier'] = identifier
        
        # Build and execute update query
        update_query = f'UPDATE shipments SET {", ".join(update_clauses)} WHERE tracking_number = :identifier OR id = :identifier'
        db.session.execute(text(update_query), update_data)
        db.session.commit()
        
        # Fetch updated shipment
        updated_result = db.session.execute(
            text('SELECT * FROM shipments WHERE tracking_number = :identifier OR id = :identifier'),
            {'identifier': identifier}
        ).first()
        
        if updated_result:
            if hasattr(updated_result, '_asdict'):
                shipment_dict = updated_result._asdict()
            elif hasattr(updated_result, '_mapping'):
                shipment_dict = dict(updated_result._mapping)
            else:
                shipment_dict = {}
                column_names = updated_result.keys() if hasattr(updated_result, 'keys') else []
                for i, col_name in enumerate(column_names):
                    shipment_dict[col_name] = updated_result[i] if i < len(updated_result) else None
        else:
            shipment_dict = {}
        
        return jsonify({
            'success': True,
            'message': 'Shipment updated successfully',
            'shipment': shipment_dict
        })
    except Exception as e:
        db.session.rollback()
        print(f"Error updating shipment: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500
