from flask import Blueprint, request, jsonify
from models.shipment import db, Shipment
from models.status_log import StatusLog
from utils.auth_utils import require_admin
from datetime import datetime

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
    # Require admin access to update shipment status
    is_admin_user, _ = require_admin()
    if not is_admin_user:
        return jsonify({'success': False, 'error': 'Admin access required'}), 403
    
    data = request.get_json()
    status = data.get('status')
    location = data.get('location')
    coordinates = data.get('coordinates')
    note = data.get('note')

    # Validate status
    if status not in ALLOWED_STATUSES:
        return jsonify({
            'success': False,
            'message': f"Invalid status. Must be one of: {', '.join(ALLOWED_STATUSES)}."
        }), 400

    # Find the shipment by tracking number
    shipment = Shipment.query.filter_by(tracking_number=tracking_number).first()
    if not shipment:
        return jsonify({'success': False, 'message': 'Shipment not found.'}), 404

    # Add a new status log
    status_log = StatusLog(
        shipment_id=shipment.id,
        status=status,
        timestamp=datetime.utcnow(),
        location=location,
        coordinates=coordinates,
        note=note
    )
    db.session.add(status_log)

    # Update the shipment's current status
    shipment.status = status
    db.session.commit()

    return jsonify({'success': True, 'message': 'Status updated.', 'status': status}), 200

@status_bp.route('/<tracking_number>/status', methods=['GET'])
def get_status_history(tracking_number):
    # Find the shipment by tracking number
    shipment = Shipment.query.filter_by(tracking_number=tracking_number).first()
    if not shipment:
        return jsonify({'success': False, 'message': 'Shipment not found.'}), 404

    # Get all status logs for this shipment, ordered by timestamp
    logs = StatusLog.query.filter_by(shipment_id=shipment.id).order_by(StatusLog.timestamp).all()
    history = []
    for log in logs:
        history.append({
            'status': log.status,
            'timestamp': log.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'location': log.location,
            'coordinates': log.coordinates,
            'note': log.note
        })
    return jsonify({'success': True, 'history': history}), 200 