"""
Complete Data Restoration Script for Render Production
This script restores users, shipments, and status logs to production database

Usage on Render Shell:
    python restore_data.py
"""
import sys
import os
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models.shipment import Shipment
from models.status_log import StatusLog

def restore_users():
    """Restore users from users.json"""
    print("=" * 60)
    print("👥 Step 1: Restoring Users")
    print("=" * 60)
    
    users_file = os.path.join('data', 'users.json')
    
    if not os.path.exists(users_file):
        print(f"❌ Users file not found: {users_file}")
        print("   Please make sure data/users.json exists in your project")
        return False
    
    print(f"✅ Found users file: {users_file}")
    
    with open(users_file, 'r', encoding='utf-8') as f:
        users = json.load(f)
    
    print(f"✅ Loaded {len(users)} users")
    for user_id, user_data in users.items():
        email = user_data.get('email', 'Unknown')
        name = user_data.get('name', 'Unknown')
        role = user_data.get('role', 'user')
        print(f"   - {name} ({email}) - Role: {role}")
    
    print("✅ Users file is ready (users are loaded from file on each request)")
    return True

def restore_shipments():
    """Restore shipments and status logs from JSON files"""
    print("\n" + "=" * 60)
    print("📦 Step 2: Restoring Shipments and Status Logs")
    print("=" * 60)
    
    # JSON files location
    export_dir = os.path.join(os.path.dirname(__file__), 'data_export')
    shipments_file = os.path.join(export_dir, 'shipments.json')
    logs_file = os.path.join(export_dir, 'status_logs.json')
    
    if not os.path.exists(shipments_file):
        print(f"❌ Shipments file not found: {shipments_file}")
        return False
    
    if not os.path.exists(logs_file):
        print(f"⚠️  Status logs file not found: {logs_file}")
        print("   Will continue without status logs")
    
    with app.app_context():
        # Create tables if they don't exist
        print("\n   Creating tables if they don't exist...")
        db.create_all()
        
        # Load shipments
        print(f"\n   Loading shipments from {shipments_file}...")
        with open(shipments_file, 'r', encoding='utf-8') as f:
            shipments_data = json.load(f)
        
        print(f"   Found {len(shipments_data)} shipments to import")
        
        # Check existing data
        existing_shipments = Shipment.query.count()
        print(f"   Production database currently has: {existing_shipments} shipments")
        
        if existing_shipments > 0:
            print(f"\n⚠️  Production database already has {existing_shipments} shipments.")
            print("   Will add new shipments (skipping duplicates by tracking number)")
        
        # Import shipments
        print(f"\n   Importing {len(shipments_data)} shipments...")
        imported_shipments = 0
        skipped_shipments = 0
        shipment_id_map = {}  # Map tracking_number to shipment object
        
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
                date_reg = None
                if shipment_data.get('date_registered'):
                    try:
                        date_reg = datetime.fromisoformat(shipment_data['date_registered'].replace('Z', '+00:00'))
                        if date_reg.tzinfo:
                            date_reg = date_reg.replace(tzinfo=None)
                    except:
                        date_reg = datetime.utcnow()
                
                est_delivery = None
                if shipment_data.get('estimated_delivery_date'):
                    try:
                        est_delivery = datetime.fromisoformat(shipment_data['estimated_delivery_date'].replace('Z', '+00:00'))
                        if est_delivery.tzinfo:
                            est_delivery = est_delivery.replace(tzinfo=None)
                    except:
                        est_delivery = None
                
                # Create shipment object
                shipment = Shipment(
                    id=shipment_data.get('id', None),  # Use existing ID if provided
                    tracking_number=shipment_data['tracking_number'],
                    sender_name=shipment_data['sender_name'],
                    sender_email=shipment_data['sender_email'],
                    sender_phone=shipment_data['sender_phone'],
                    sender_address=shipment_data['sender_address'],
                    receiver_name=shipment_data['receiver_name'],
                    receiver_phone=shipment_data['receiver_phone'],
                    receiver_address=shipment_data['receiver_address'],
                    package_type=shipment_data['package_type'],
                    weight=shipment_data['weight'],
                    shipment_cost=shipment_data.get('shipment_cost', 0.0),
                    date_registered=date_reg or datetime.utcnow(),
                    estimated_delivery_date=est_delivery,
                    status=shipment_data.get('status', 'Registered'),
                    current_location=shipment_data.get('current_location'),
                    pdf_url=shipment_data.get('pdf_url'),
                    qr_url=shipment_data.get('qr_url'),
                    created_by=shipment_data.get('created_by'),
                    created_by_email=shipment_data.get('created_by_email'),
                )
                
                db.session.add(shipment)
                db.session.flush()  # Get the ID
                shipment_id_map[shipment_data['tracking_number']] = shipment
                imported_shipments += 1
                
                if imported_shipments % 5 == 0:
                    print(f"   ... imported {imported_shipments} shipments so far")
            except Exception as e:
                print(f"   ❌ Error importing {shipment_data.get('tracking_number', 'unknown')}: {e}")
                db.session.rollback()
        
        db.session.commit()
        print(f"   ✅ Imported {imported_shipments} shipments (skipped {skipped_shipments} duplicates)")
        
        # Import status logs if file exists
        if os.path.exists(logs_file):
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
                            skipped_logs += 1
                            continue
                    
                    # Parse timestamp
                    if log_data.get('timestamp'):
                        try:
                            timestamp = datetime.fromisoformat(log_data['timestamp'].replace('Z', '+00:00'))
                            if timestamp.tzinfo:
                                timestamp = timestamp.astimezone(datetime.now().astimezone().tzinfo).replace(tzinfo=None)
                        except:
                            timestamp = datetime.utcnow()
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
                    
                    if imported_logs % 10 == 0:
                        print(f"   ... imported {imported_logs} status logs so far")
                except Exception as e:
                    print(f"   ❌ Error importing status log: {e}")
                    db.session.rollback()
            
            db.session.commit()
            print(f"   ✅ Imported {imported_logs} status logs (skipped {skipped_logs} duplicates)")
        else:
            print("\n   ⚠️  No status logs file found, skipping status logs import")
        
        # Verify
        final_shipments = Shipment.query.count()
        final_logs = StatusLog.query.count()
        print(f"\n   ✅ Production database now has: {final_shipments} shipments, {final_logs} status logs")
    
    return True

def main():
    """Main restoration function"""
    print("\n" + "=" * 60)
    print("🚀 DATA RESTORATION FOR PRODUCTION")
    print("=" * 60)
    print("\nThis script will restore:")
    print("  1. Users (from data/users.json)")
    print("  2. Shipments (from data_export/shipments.json)")
    print("  3. Status Logs (from data_export/status_logs.json)")
    print("\n⚠️  Note: This will NOT delete existing data.")
    print("   It will only add new records (skipping duplicates).")
    print("=" * 60)
    
    try:
        # Step 1: Restore users
        if not restore_users():
            print("\n❌ Failed to restore users")
            return False
        
        # Step 2: Restore shipments and logs
        if not restore_shipments():
            print("\n❌ Failed to restore shipments")
            return False
        
        print("\n" + "=" * 60)
        print("✅ DATA RESTORATION COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print("\nYou can now:")
        print("  1. Log in with your admin credentials")
        print("  2. View all restored shipments in the admin dashboard")
        print("  3. All tracking information should be available")
        print("\n" + "=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n❌ Fatal error during restoration: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)

