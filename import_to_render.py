"""
Import data from JSON files to Render PostgreSQL database
Run this on Render Shell: python import_to_render.py
"""
import sys
import os
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models.shipment import Shipment
from models.status_log import StatusLog

def import_from_json():
    """Import data from JSON files"""
    print("=" * 60)
    print("📤 Importing Data to Render PostgreSQL")
    print("=" * 60)
    
    # JSON files location
    export_dir = os.path.join(os.path.dirname(__file__), 'data_export')
    shipments_file = os.path.join(export_dir, 'shipments.json')
    logs_file = os.path.join(export_dir, 'status_logs.json')
    
    if not os.path.exists(shipments_file):
        print(f"❌ Shipments file not found: {shipments_file}")
        return False
    
    if not os.path.exists(logs_file):
        print(f"❌ Status logs file not found: {logs_file}")
        return False
    
    with app.app_context():
        # Create tables if they don't exist
        print("   Creating tables if they don't exist...")
        db.create_all()
        
        # Load shipments
        print(f"\n   Loading shipments from {shipments_file}...")
        with open(shipments_file, 'r', encoding='utf-8') as f:
            shipments_data = json.load(f)
        
        print(f"   Found {len(shipments_data)} shipments to import")
        
        # Check existing data
        existing_shipments = Shipment.query.count()
        print(f"   Render database currently has: {existing_shipments} shipments")
        
        if existing_shipments > 0:
            print(f"\n⚠️  Render database already has {existing_shipments} shipments.")
            response = input("   Do you want to add new shipments (keep existing) or replace all? (add/replace): ")
            if response.lower() == 'replace':
                print("   Clearing existing data...")
                StatusLog.query.delete()
                Shipment.query.delete()
                db.session.commit()
                print("   ✅ Cleared existing data")
            else:
                print("   Will add new shipments (skipping duplicates)")
        
        # Import shipments
        print(f"\n   Importing {len(shipments_data)} shipments...")
        imported_shipments = 0
        skipped_shipments = 0
        shipment_id_map = {}  # Map old tracking_number to new shipment object
        
        for shipment_data in shipments_data:
            try:
                # Check if shipment already exists
                existing = Shipment.query.filter_by(tracking_number=shipment_data['tracking_number']).first()
                if existing:
                    print(f"   ⚠️  Skipping {shipment_data['tracking_number']} (already exists)")
                    shipment_id_map[shipment_data['tracking_number']] = existing
                    skipped_shipments += 1
                    continue
                
                # Parse dates
                if shipment_data.get('date_registered'):
                    shipment_data['date_registered'] = datetime.fromisoformat(shipment_data['date_registered'].replace('Z', '+00:00'))
                if shipment_data.get('estimated_delivery_date'):
                    shipment_data['estimated_delivery_date'] = datetime.fromisoformat(shipment_data['estimated_delivery_date'].replace('Z', '+00:00'))
                
                shipment = Shipment(**shipment_data)
                db.session.add(shipment)
                db.session.flush()  # Get the ID
                shipment_id_map[shipment_data['tracking_number']] = shipment
                imported_shipments += 1
                
                if imported_shipments % 10 == 0:
                    print(f"   ... imported {imported_shipments} shipments so far")
            except Exception as e:
                print(f"   ❌ Error importing {shipment_data.get('tracking_number', 'unknown')}: {e}")
                db.session.rollback()
        
        db.session.commit()
        print(f"   ✅ Imported {imported_shipments} shipments (skipped {skipped_shipments} duplicates)")
        
        # Load status logs
        print(f"\n   Loading status logs from {logs_file}...")
        with open(logs_file, 'r', encoding='utf-8') as f:
            status_logs_data = json.load(f)
        
        print(f"   Found {len(status_logs_data)} status logs to import")
        
        # Import status logs
        print(f"\n   Importing {len(status_logs_data)} status logs...")
        imported_logs = 0
        skipped_logs = 0
        
        for log_data in status_logs_data:
            try:
                tracking_number = log_data.get('tracking_number')
                if not tracking_number:
                    skipped_logs += 1
                    continue
                
                shipment = shipment_id_map.get(tracking_number)
                if not shipment:
                    # Try to find it in database
                    shipment = Shipment.query.filter_by(tracking_number=tracking_number).first()
                    if not shipment:
                        print(f"   ⚠️  Skipping log for {tracking_number} (shipment not found)")
                        skipped_logs += 1
                        continue
                
                # Parse timestamp
                if log_data.get('timestamp'):
                    timestamp = datetime.fromisoformat(log_data['timestamp'].replace('Z', '+00:00'))
                    # Convert to UTC naive
                    if timestamp.tzinfo:
                        timestamp = timestamp.astimezone(datetime.now().astimezone().tzinfo).replace(tzinfo=None)
                else:
                    timestamp = datetime.utcnow()
                
                # Check if log already exists
                existing = StatusLog.query.filter_by(
                    shipment_id=shipment.id,
                    status=log_data['status'],
                    timestamp=timestamp
                ).first()
                
                if existing:
                    skipped_logs += 1
                    continue
                
                log = StatusLog(
                    shipment_id=shipment.id,
                    status=log_data['status'],
                    timestamp=timestamp,
                    location=log_data.get('location'),
                    coordinates=log_data.get('coordinates'),
                    note=log_data.get('note')
                )
                db.session.add(log)
                imported_logs += 1
                
                if imported_logs % 50 == 0:
                    print(f"   ... imported {imported_logs} status logs so far")
            except Exception as e:
                print(f"   ❌ Error importing status log: {e}")
                db.session.rollback()
        
        db.session.commit()
        print(f"   ✅ Imported {imported_logs} status logs (skipped {skipped_logs} duplicates)")
        
        # Verify
        final_shipments = Shipment.query.count()
        final_logs = StatusLog.query.count()
        print(f"\n   ✅ Render database now has: {final_shipments} shipments, {final_logs} status logs")
    
    print("\n" + "=" * 60)
    print("✅ Import completed successfully!")
    print("=" * 60)
    return True

if __name__ == '__main__':
    try:
        if import_from_json():
            print("\n✓ Your data is now on Render!")
        else:
            print("\n❌ Import failed. Please check the errors above.")
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

