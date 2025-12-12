from flask import Blueprint, request, jsonify, session, current_app
from models.shipment import db, Shipment
from models.status_log import StatusLog
from utils.pdf_generator import generate_pdf_receipt
from utils.auth_utils import require_admin
from datetime import datetime
import uuid
import json
import os

# #region agent log
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
            log_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.cursor', 'debug.log')
            os.makedirs(os.path.dirname(log_path), exist_ok=True)
            with open(log_path, 'a', encoding='utf-8') as f:
                f.write(log_json + '\n')
        except: pass
    except Exception as e:
        print(f"DEBUG_LOG_ERROR: {e}")
# #endregion

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
        # shipment_cost is optional - will default to 0.0 if not provided
        shipment_cost = data.get('shipment_cost')
        estimated_delivery_date = data.get('estimated_delivery_date')

        # Validate required fields (shipment_cost is NOT in this list - it's optional)
        required_fields = ['sender_name', 'sender_email', 'sender_phone', 'sender_address', 
                          'receiver_name', 'receiver_phone', 'receiver_address', 'package_type', 
                          'weight']
        
        missing_fields = []
        for field in required_fields:
            value = data.get(field)
            if value is None or (isinstance(value, str) and value.strip() == ''):
                missing_fields.append(field)
        
        if missing_fields:
            print(f"❌ Validation failed - Missing required fields: {missing_fields}")
            print(f"📦 Received data keys: {list(data.keys())}")
            return jsonify({'success': False, 'error': f'Missing required fields: {", ".join(missing_fields)}'}), 400

        # Allow custom tracking number or generate one
        from sqlalchemy import text
        tracking_number = data.get('tracking_number')
        if not tracking_number:
            # Generate a unique tracking number if not provided
            tracking_number = f'TRK{str(uuid.uuid4())[:8].upper()}'
            print(f"📦 Auto-generated tracking number: {tracking_number}")
        else:
            # Validate custom tracking number format (optional: add format validation)
            tracking_number = str(tracking_number).strip().upper()
            if not tracking_number:
                return jsonify({
                    'success': False, 
                    'error': 'Tracking number cannot be empty'
                }), 400
            
            # Check if tracking number already exists
            existing = db.session.execute(
                text('SELECT tracking_number FROM shipments WHERE tracking_number = :tn'),
                {'tn': tracking_number}
            ).first()
            if existing:
                return jsonify({
                    'success': False, 
                    'error': f'Tracking number {tracking_number} already exists'
                }), 409
            
            print(f"📦 Using custom tracking number: {tracking_number}")

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
        # Handle optional shipment_cost - use 0.0 as default if not provided
        # shipment_cost is OPTIONAL and should NOT be in required_fields validation
        shipment_cost_value = 0.0  # Default value
        if shipment_cost is not None:
            if isinstance(shipment_cost, str):
                if shipment_cost.strip() != '':
                    try:
                        shipment_cost_value = float(shipment_cost)
                    except (ValueError, TypeError):
                        shipment_cost_value = 0.0
            else:
                try:
                    shipment_cost_value = float(shipment_cost)
                except (ValueError, TypeError):
                    shipment_cost_value = 0.0
        
        print(f"💰 Shipment cost handling: received={shipment_cost}, using={shipment_cost_value}")
        
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
            'shipment_cost': shipment_cost_value,
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
        # #region agent log
        _debug_log("D", "routes/shipments.py:162", "Before INSERT execution", {"tracking_number": tracking_number, "columns": list(filtered_data.keys())})
        # #endregion
        db.session.execute(sql, filtered_data)
        # #region agent log
        _debug_log("D", "routes/shipments.py:165", "After INSERT execution, before commit", {"tracking_number": tracking_number})
        # #endregion
        
        # 🔍 ADD VERIFICATION BEFORE COMMIT
        try:
            db.session.commit()
            # #region agent log
            _debug_log("D", "routes/shipments.py:170", "Commit successful", {"tracking_number": tracking_number})
            # #endregion
            print(f"✅ COMMIT SUCCESSFUL for {tracking_number} at {datetime.utcnow()}")
        except Exception as commit_error:
            db.session.rollback()
            # #region agent log
            _debug_log("D", "routes/shipments.py:175", "Commit failed, rolled back", {"tracking_number": tracking_number, "error": str(commit_error)})
            # #endregion
            print(f"❌ COMMIT FAILED: {commit_error}")
            raise Exception(f"Failed to save shipment to database: {commit_error}")
        
        # 🔍 VERIFY IT WAS SAVED
        # #region agent log
        _debug_log("B", "routes/shipments.py:181", "Verifying shipment exists after commit", {"tracking_number": tracking_number})
        # #endregion
        verify = db.session.execute(
            text('SELECT tracking_number FROM shipments WHERE tracking_number = :tn'),
            {'tn': tracking_number}
        ).first()
        
        if not verify:
            # #region agent log
            _debug_log("B", "routes/shipments.py:188", "VERIFICATION FAILED - shipment not found after commit", {"tracking_number": tracking_number})
            # #endregion
            raise Exception(f"Shipment {tracking_number} was not saved to database!")
        
        # #region agent log
        _debug_log("B", "routes/shipments.py:192", "Verification successful - shipment exists", {"tracking_number": tracking_number})
        # #endregion
        print(f"✅ VERIFIED: Shipment {tracking_number} exists in database")
        db_uri = current_app.config.get('SQLALCHEMY_DATABASE_URI', 'unknown')
        db_info = db_uri.split('@')[-1] if '@' in str(db_uri) else 'local'
        print(f"   Database: {db_info}")
        
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
        
        print(f"✅ SHIPMENT CREATED: {tracking_number} at {datetime.utcnow()}")
        print(f"   Shipment ID: {shipment.id}")
        print(f"   Status: {shipment.status}")

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
    # #region agent log
    _debug_log("B", "routes/shipments.py:248", "get_all_shipments called", {"method": request.method, "path": request.path})
    # #endregion
    # Require admin access to view all shipments
    is_admin_user, user_info = require_admin()
    if not is_admin_user:
        # #region agent log
        _debug_log("B", "routes/shipments.py:252", "Admin check failed", {"is_admin": False})
        # #endregion
        return jsonify({'success': False, 'error': 'Admin access required'}), 403
    
    # Always use raw SQL to avoid ORM column issues - simplified, no role filtering
    from sqlalchemy import text
    from datetime import datetime
    
    try:
        # #region agent log
        _debug_log("B", "routes/shipments.py:260", "Executing SELECT * FROM shipments query")
        # Also check count directly
        count_result = db.session.execute(text('SELECT COUNT(*) FROM shipments'))
        total_count = count_result.scalar() or 0
        _debug_log("B", "routes/shipments.py:262", "Direct COUNT query result", {"total_shipments": total_count})
        # #endregion
        # Use raw SQL to fetch all shipments
        result = db.session.execute(text('SELECT * FROM shipments'))
        # #region agent log
        # Get column names BEFORE fetchall() - critical fix for SQLAlchemy
        column_names = list(result.keys()) if hasattr(result, 'keys') else []
        _debug_log("B", "routes/shipments.py:322", "Got column names before fetchall", {"column_names": column_names, "column_count": len(column_names)})
        # #endregion
        shipments_rows = result.fetchall()
        # #region agent log
        _debug_log("B", "routes/shipments.py:325", "Query executed", {"rows_count": len(shipments_rows) if shipments_rows else 0, "count_mismatch": total_count != len(shipments_rows) if shipments_rows else False, "has_column_names": len(column_names) > 0})
        # #endregion
        
        # Convert rows to shipment-like dicts
        shipments = []
        if shipments_rows:
            # #region agent log
            _debug_log("B", "routes/shipments.py:330", "Processing shipment rows", {"total_rows": len(shipments_rows), "column_names": column_names})
            # #endregion
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
                # #region agent log
                _debug_log("B", "routes/shipments.py:281", "Processed shipment row", {"tracking_number": shipment_dict.get('tracking_number'), "id": shipment_dict.get('id')})
                # #endregion
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
    # #region agent log
    _debug_log("B", "routes/shipments.py:304", "Returning shipments list", {"count": len(shipment_list)})
    # #endregion
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

# ============================================================================
# STATUS ROUTES - COMMENTED OUT: These routes are now handled by routes/status.py
# status_bp is registered first in app.py, so it takes precedence
# ============================================================================

# # Get shipment status history - DUPLICATE: Now handled by routes/status.py
# @shipment_bp.route('/<identifier>/status', methods=['GET', 'OPTIONS'])
# def get_shipment_status_history(identifier):
#     """Get status history for a shipment"""
#     if request.method == 'OPTIONS':
#         # Handle CORS preflight
#         return jsonify({'ok': True}), 200
#     
#     try:
#         # Find shipment by tracking_number or ID
#         shipment = Shipment.query.filter(
#             (Shipment.tracking_number == identifier) | (Shipment.id == identifier)
#         ).first()
#         
#         if not shipment:
#             return jsonify({'success': False, 'message': 'Shipment not found'}), 404
#         
#         # Get all status logs for this shipment, ordered by timestamp (oldest first)
#         logs = StatusLog.query.filter_by(shipment_id=shipment.id).order_by(StatusLog.timestamp.asc()).all()
#         history = []
#         for log in logs:
#             history.append({
#                 'status': log.status,
#                 'timestamp': log.timestamp.isoformat() if log.timestamp else None,
#                 'location': log.location if log.location else None,
#                 'coordinates': log.coordinates,
#                 'note': log.note
#             })
#         
#         print(f"GET status: Found {len(history)} status logs for shipment {identifier}")
#         print(f"Shipment current_location: {shipment.current_location}")
#         print(f"Last history entry location: {history[-1]['location'] if history else 'No history'}")
#         
#         return jsonify({
#             'success': True, 
#             'history': history,
#             'current_location': shipment.current_location
#         }), 200
#     except Exception as e:
#         print(f"Error getting status history: {e}")
#         import traceback
#         traceback.print_exc()
#         return jsonify({'success': False, 'error': str(e)}), 500

# # Update shipment status - DUPLICATE: Now handled by routes/status.py
# @shipment_bp.route('/<identifier>/status', methods=['PUT', 'PATCH', 'OPTIONS'])
# def update_shipment_status(identifier):
#     if request.method == 'OPTIONS':
#         # Handle CORS preflight request
#         origin = request.headers.get('Origin')
#         allowed_origins = [
#             'https://dmllogisticsxpress.com',        # Your main domain
#             'https://www.dmllogisticsxpress.com',    # With www
#             'https://dmlmainlogistics.netlify.app',  # Netlify URL
#             'http://localhost:3000',                  # Local development
#             'http://localhost:5173',                  # Vite dev server
#             'http://127.0.0.1:3000',
#             'http://localhost:5000',
#             'http://127.0.0.1:5000'
#         ]
#         
#         # Also allow Netlify preview deployments (*.netlify.app)
#         is_netlify_preview = origin and '.netlify.app' in origin
#         
#         if origin in allowed_origins or is_netlify_preview or origin is None:
#             response = jsonify({'ok': True})
#             if origin:
#                 response.headers.add('Access-Control-Allow-Origin', origin)
#             response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization')
#             response.headers.add('Access-Control-Allow-Methods', 'PUT, PATCH, OPTIONS')
#             response.headers.add('Access-Control-Allow-Credentials', 'true')
#             response.headers.add('Access-Control-Max-Age', '3600')
#             return response, 200
#         else:
#             return jsonify({'error': 'Origin not allowed'}), 403
#     
#     # Require admin access
#     is_admin_user, user_info = require_admin()
#     if not is_admin_user:
#         return jsonify({'success': False, 'error': 'Admin access required'}), 403
#     
#     try:
#         data = request.get_json()
#         if not data:
#             return jsonify({'success': False, 'error': 'No data provided'}), 400
#         
#         status = data.get('status')
#         location = data.get('location')
#         coordinates = data.get('coordinates')
#         note = data.get('note')
#         custom_timestamp = data.get('timestamp')
#         
#         if not status:
#             return jsonify({'success': False, 'error': 'Status is required'}), 400
#         
#         # Validate location is provided
#         if not location:
#             return jsonify({'success': False, 'error': 'Location is required for status updates'}), 400
#         
#         # Find shipment by tracking_number or ID
#         shipment = Shipment.query.filter(
#             (Shipment.tracking_number == identifier) | (Shipment.id == identifier)
#         ).first()
#         
#         if not shipment:
#             return jsonify({'success': False, 'error': 'Shipment not found'}), 404
#         
#         # Parse custom timestamp if provided, otherwise use current time
#         if custom_timestamp:
#             try:
#                 # Handle ISO format with or without timezone
#                 if custom_timestamp.endswith('Z'):
#                     custom_timestamp = custom_timestamp[:-1] + '+00:00'
#                 
#                 # Parse the timestamp
#                 timestamp = datetime.fromisoformat(custom_timestamp)
#                 
#                 # Convert to UTC naive datetime if timezone-aware
#                 if timestamp.tzinfo is not None:
#                     timestamp = timestamp.astimezone(datetime.timezone.utc).replace(tzinfo=None)
#             except (ValueError, AttributeError) as e:
#                 print(f"Error parsing timestamp: {e}, using current time")
#                 timestamp = datetime.utcnow()
#         else:
#             timestamp = datetime.utcnow()
#         
#         # Create new status log entry
#         status_log = StatusLog(
#             shipment_id=shipment.id,
#             status=status,
#             timestamp=timestamp,
#             location=location,
#             coordinates=coordinates,
#             note=note
#         )
#         db.session.add(status_log)
#         
#         # Update shipment status AND current_location
#         shipment.status = status
#         shipment.current_location = location
#         
#         db.session.commit()
#         
#         print(f"Status updated: {status} at {location} for shipment {identifier}")
#         
#         return jsonify({
#             'success': True,
#             'message': 'Status updated successfully',
#             'status': status
#         }), 200
#         
#     except Exception as e:
#         db.session.rollback()
#         print(f"Error updating status: {e}")
#         import traceback
#         traceback.print_exc()
#         return jsonify({'success': False, 'error': str(e)}), 500

# Get single shipment by tracking number or ID
@shipment_bp.route('/<identifier>', methods=['GET'])
def get_shipment(identifier):
    # #region agent log
    _debug_log("B", "routes/shipments.py:587", "get_shipment called", {"identifier": identifier, "method": request.method, "path": request.path})
    # #endregion
    try:
        from sqlalchemy import text
        # #region agent log
        _debug_log("B", "routes/shipments.py:591", "Executing SELECT query for shipment", {"identifier": identifier})
        # #endregion
        result = db.session.execute(
            text('SELECT * FROM shipments WHERE tracking_number = :identifier OR id = :identifier'),
            {'identifier': identifier}
        ).first()
        
        # #region agent log
        _debug_log("B", "routes/shipments.py:597", "Query result", {"found": result is not None, "identifier": identifier})
        # #endregion
        
        if not result:
            # #region agent log
            _debug_log("B", "routes/shipments.py:600", "Shipment not found - returning 404", {"identifier": identifier})
            # #endregion
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
        from datetime import datetime
        
        # Try to find by tracking_number first, then by ID
        result = db.session.execute(
            text('SELECT id, tracking_number FROM shipments WHERE tracking_number = :identifier OR id = :identifier'),
            {'identifier': identifier}
        ).first()
        
        if not result:
            return jsonify({'success': False, 'error': 'Shipment not found'}), 404
        
        tracking_num = result.tracking_number if hasattr(result, 'tracking_number') else (result[1] if len(result) > 1 else identifier)
        shipment_id = result.id if hasattr(result, 'id') else (result[0] if len(result) > 0 else identifier)
        
        # 🔍 ADD COMPREHENSIVE LOGGING - Log who is deleting what
        admin_email = user_info.get('email', 'unknown') if user_info else 'unknown'
        admin_name = user_info.get('name', 'unknown') if user_info else 'unknown'
        print(f"⚠️ DELETION ATTEMPT: User {admin_name} ({admin_email}) is deleting shipment {tracking_num} (ID: {shipment_id}) at {datetime.utcnow()}")
        print(f"   Request from: {request.remote_addr}")
        print(f"   User-Agent: {request.headers.get('User-Agent', 'unknown')}")
        print(f"   Referer: {request.headers.get('Referer', 'unknown')}")
        
        # Count status logs before deletion
        status_logs_count = db.session.execute(
            text('SELECT COUNT(*) FROM status_logs WHERE shipment_id = :shipment_id'),
            {'shipment_id': shipment_id}
        ).scalar() or 0
        
        print(f"   Associated status logs: {status_logs_count}")
        
        # Delete status logs first to avoid foreign key issues
        if status_logs_count > 0:
            db.session.execute(
                text('DELETE FROM status_logs WHERE shipment_id = :shipment_id'),
                {'shipment_id': shipment_id}
            )
            print(f"   Deleted {status_logs_count} status logs")
        
        # Delete the shipment
        db.session.execute(
            text('DELETE FROM shipments WHERE tracking_number = :identifier OR id = :identifier'),
            {'identifier': identifier}
        )
        
        try:
            db.session.commit()
            print(f"✅ DELETION SUCCESSFUL: Shipment {tracking_num} deleted by {admin_email} at {datetime.utcnow()}")
        except Exception as commit_error:
            db.session.rollback()
            print(f"❌ DELETION COMMIT FAILED: {commit_error}")
            raise
        
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
