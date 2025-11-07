from flask import Blueprint, request, jsonify
from models.shipment import db, Shipment
from models.status_log import StatusLog
from utils.auth_utils import require_admin
from datetime import datetime, timezone

status_bp = Blueprint('status_bp', __name__)

# List of allowed statuses
ALLOWED_STATUSES = [
    'Registered',
    'At Facility',
    'In Transit',
    'Out for Delivery',
    'Delivered',
    'Delayed',
    'Cancelled'
]

@status_bp.route('/<tracking_number>/status', methods=['PUT'])
def update_status(tracking_number):
    try:
        # Require admin access to update shipment status
        is_admin_user, _ = require_admin()
        if not is_admin_user:
            return jsonify({'success': False, 'error': 'Admin access required'}), 403
        
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        status = data.get('status')
        location = data.get('location')
        coordinates = data.get('coordinates')
        note = data.get('note')
        custom_timestamp = data.get('timestamp')  # Accept custom timestamp from frontend

        # Validate status
        if not status:
            return jsonify({
                'success': False,
                'message': 'Status is required.'
            }), 400
        
        if status not in ALLOWED_STATUSES:
            return jsonify({
                'success': False,
                'message': f"Invalid status. Must be one of: {', '.join(ALLOWED_STATUSES)}."
            }), 400

        # Validate location is provided
        if not location:
            return jsonify({
                'success': False,
                'message': 'Location is required for status updates.'
            }), 400

        # Find the shipment by tracking number
        shipment = Shipment.query.filter_by(tracking_number=tracking_number).first()
        if not shipment:
            return jsonify({'success': False, 'message': 'Shipment not found.'}), 404

        # Parse custom timestamp if provided, otherwise use current time
        if custom_timestamp:
            try:
                print(f"📅 Received custom timestamp: {custom_timestamp}")
                # Handle ISO format with or without timezone
                if custom_timestamp.endswith('Z'):
                    custom_timestamp = custom_timestamp[:-1] + '+00:00'
                
                # Parse the timestamp
                timestamp = datetime.fromisoformat(custom_timestamp)
                print(f"📅 Parsed timestamp (timezone-aware): {timestamp}")
                
                # Convert to UTC naive datetime if timezone-aware
                if timestamp.tzinfo is not None:
                    timestamp = timestamp.astimezone(timezone.utc).replace(tzinfo=None)
                    print(f"📅 Converted to UTC (naive): {timestamp}")
                else:
                    print(f"📅 Timestamp is already naive, treating as UTC: {timestamp}")
            except (ValueError, AttributeError) as e:
                print(f"❌ Error parsing timestamp: {e}, using current time")
                timestamp = datetime.utcnow()
        else:
            timestamp = datetime.utcnow()
            print(f"📅 No custom timestamp provided, using current time: {timestamp}")

        # Add a new status log
        status_log = StatusLog(
            shipment_id=shipment.id,
            status=status,
            timestamp=timestamp,
            location=location,
            coordinates=coordinates,
            note=note
        )
        db.session.add(status_log)

        # Update the shipment's current status and location
        shipment.status = status
        shipment.current_location = location
        
        db.session.commit()

        print(f"✅ Status updated successfully: {status} at {location} for shipment {tracking_number}")
        return jsonify({'success': True, 'message': 'Status updated.', 'status': status}), 200
    
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error updating status for {tracking_number}: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False, 
            'error': f'Failed to update status: {str(e)}'
        }), 500

@status_bp.route('/<tracking_number>/status', methods=['GET'])
def get_status_history(tracking_number):
    # Find the shipment by tracking number
    shipment = Shipment.query.filter_by(tracking_number=tracking_number).first()
    if not shipment:
        return jsonify({'success': False, 'message': 'Shipment not found.'}), 404

    # Get all status logs for this shipment, ordered by timestamp (oldest first)
    logs = StatusLog.query.filter_by(shipment_id=shipment.id).order_by(StatusLog.timestamp.asc()).all()
    history = []
    for log in logs:
        timestamp_str = log.timestamp.strftime('%Y-%m-%dT%H:%M:%SZ') if log.timestamp else None
        history.append({
            'status': log.status,
            'timestamp': timestamp_str,
            'location': log.location if log.location else None,  # Ensure location is included even if None
            'coordinates': log.coordinates,
            'note': log.note
        })
        if log.timestamp:
            print(f"📅 Returning timestamp: {timestamp_str} (from stored: {log.timestamp})")
    
    print(f"Found {len(history)} status logs for shipment {tracking_number}")
    print(f"Shipment current_location: {shipment.current_location}")
    print(f"Last history entry location: {history[-1]['location'] if history else 'No history'}")
    if history:
        print(f"Last history entry timestamp: {history[-1]['timestamp']}")
    
    # Also return the shipment's current_location in the response for easier access
    return jsonify({
        'success': True, 
        'history': history,
        'current_location': shipment.current_location  # Include current_location in response
    }), 200