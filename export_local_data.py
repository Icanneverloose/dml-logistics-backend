"""
Export local SQLite data to JSON files for manual import
Usage: python export_local_data.py
"""
import sys
import os
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models.shipment import Shipment
from models.status_log import StatusLog

def export_to_json():
    """Export all data to JSON files"""
    print("=" * 60)
    print("📦 Exporting Local SQLite Data to JSON")
    print("=" * 60)
    
    local_db_path = os.path.join(os.path.dirname(__file__), 'instance', 'app.db')
    if not os.path.exists(local_db_path):
        print(f"❌ Local database not found at: {local_db_path}")
        return False
    
    print(f"   Local database found: {local_db_path}")
    
    with app.app_context():
        # Export shipments
        shipments = Shipment.query.all()
        print(f"   Found {len(shipments)} shipments")
        
        shipments_data = []
        for shipment in shipments:
            shipments_data.append({
                'tracking_number': shipment.tracking_number,
                'sender_name': shipment.sender_name,
                'sender_email': shipment.sender_email,
                'sender_phone': shipment.sender_phone,
                'sender_address': shipment.sender_address,
                'receiver_name': shipment.receiver_name,
                'receiver_phone': shipment.receiver_phone,
                'receiver_address': shipment.receiver_address,
                'package_type': shipment.package_type,
                'weight': shipment.weight,
                'shipment_cost': shipment.shipment_cost,
                'date_registered': shipment.date_registered.isoformat() if shipment.date_registered else None,
                'estimated_delivery_date': shipment.estimated_delivery_date.isoformat() if shipment.estimated_delivery_date else None,
                'status': shipment.status,
                'current_location': shipment.current_location,
                'pdf_url': shipment.pdf_url,
                'qr_url': shipment.qr_url,
                'created_by': shipment.created_by,
                'created_by_email': shipment.created_by_email,
            })
        
        # Export status logs
        status_logs = StatusLog.query.all()
        print(f"   Found {len(status_logs)} status logs")
        
        status_logs_data = []
        for log in status_logs:
            # Find shipment tracking number
            shipment = Shipment.query.get(log.shipment_id)
            status_logs_data.append({
                'tracking_number': shipment.tracking_number if shipment else None,
                'status': log.status,
                'timestamp': log.timestamp.isoformat() if log.timestamp else None,
                'location': log.location,
                'coordinates': log.coordinates,
                'note': log.note,
            })
        
        # Save to JSON files
        export_dir = os.path.join(os.path.dirname(__file__), 'data_export')
        os.makedirs(export_dir, exist_ok=True)
        
        shipments_file = os.path.join(export_dir, 'shipments.json')
        logs_file = os.path.join(export_dir, 'status_logs.json')
        
        with open(shipments_file, 'w', encoding='utf-8') as f:
            json.dump(shipments_data, f, indent=2, ensure_ascii=False)
        
        with open(logs_file, 'w', encoding='utf-8') as f:
            json.dump(status_logs_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ Data exported successfully!")
        print(f"   📄 Shipments: {shipments_file}")
        print(f"   📄 Status Logs: {logs_file}")
        print(f"\n   You can now:")
        print(f"   1. Upload these files to Render")
        print(f"   2. Run the import script on Render to import the data")
        
        return True

if __name__ == '__main__':
    try:
        export_to_json()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)



