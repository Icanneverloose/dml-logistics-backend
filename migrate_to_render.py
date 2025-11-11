"""
Script to migrate data from local SQLite database to Render PostgreSQL database
Usage: python migrate_to_render.py
"""
import sys
import os
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models.shipment import Shipment
from models.status_log import StatusLog

def migrate_to_render():
    """
    Migrate data from local SQLite to Render PostgreSQL
    """
    print("=" * 60)
    print("🚀 Starting Migration: Local SQLite → Render PostgreSQL")
    print("=" * 60)
    
    # Step 1: Connect to LOCAL database and export data
    print("\n📦 Step 1: Exporting data from LOCAL SQLite database...")
    
    # Local database path
    local_db_path = os.path.join(os.path.dirname(__file__), 'instance', 'app.db')
    if not os.path.exists(local_db_path):
        print(f"❌ Local database not found at: {local_db_path}")
        return False
    
    print(f"   Local database found: {local_db_path}")
    
    # Create SQLAlchemy engine for local database
    local_engine = create_engine(f'sqlite:///{local_db_path}')
    LocalSession = sessionmaker(bind=local_engine)
    local_session = LocalSession()
    
    try:
        # Export shipments
        local_shipments = local_session.query(Shipment).all()
        print(f"   Found {len(local_shipments)} shipments in local database")
        
        shipments_data = []
        for shipment in local_shipments:
            shipments_data.append({
                'id': shipment.id,
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
                'date_registered': shipment.date_registered,
                'estimated_delivery_date': shipment.estimated_delivery_date,
                'status': shipment.status,
                'current_location': shipment.current_location,
                'pdf_url': shipment.pdf_url,
                'qr_url': shipment.qr_url,
                'created_by': shipment.created_by,
                'created_by_email': shipment.created_by_email,
            })
        
        # Export status logs
        local_status_logs = local_session.query(StatusLog).all()
        print(f"   Found {len(local_status_logs)} status logs in local database")
        
        status_logs_data = []
        for log in local_status_logs:
            status_logs_data.append({
                'id': log.id,
                'shipment_id': log.shipment_id,
                'status': log.status,
                'timestamp': log.timestamp,
                'location': log.location,
                'coordinates': log.coordinates,
                'note': log.note,
            })
    finally:
        local_session.close()
        local_engine.dispose()
    
    # Step 2: Connect to RENDER PostgreSQL and import data
    print("\n📤 Step 2: Importing data to RENDER PostgreSQL database...")
    
    # Your Render database External Connection String
    # Add SSL mode for secure connection
    render_db_url = 'postgresql://dml_main_logistics_db_user:DDl1NZxAmJ7r9Ac05kTxE0TD8ISDdF5Z@dpg-d45lqoeuk2gs73cl5140-a.oregon-postgres.render.com/dml_main_logistics_db?sslmode=require'
    
    print(f"   Connecting to Render database...")
    
    # Create SQLAlchemy engine for Render database with connection pool settings
    render_engine = create_engine(
        render_db_url,
        pool_pre_ping=True,  # Verify connections before using
        connect_args={
            "sslmode": "require",
            "connect_timeout": 10
        }
    )
    RenderSession = sessionmaker(bind=render_engine)
    render_session = RenderSession()
    
    try:
        # Create tables if they don't exist
        print("   Creating tables if they don't exist...")
        Shipment.metadata.create_all(render_engine)
        StatusLog.metadata.create_all(render_engine)
        
        # Check existing data
        existing_shipments = render_session.query(Shipment).count()
        existing_logs = render_session.query(StatusLog).count()
        print(f"   Render database currently has: {existing_shipments} shipments, {existing_logs} status logs")
        
        if existing_shipments > 0:
            print(f"\n⚠️  Render database already has {existing_shipments} shipments.")
            response = input("   Do you want to add new shipments (keep existing) or replace all? (add/replace): ")
            if response.lower() == 'replace':
                print("   Clearing existing data...")
                render_session.query(StatusLog).delete()
                render_session.query(Shipment).delete()
                render_session.commit()
                print("   ✅ Cleared existing data")
            else:
                print("   Will add new shipments (skipping duplicates)")
        
        # Import shipments
        print(f"\n   Importing {len(shipments_data)} shipments...")
        imported_shipments = 0
        skipped_shipments = 0
        for shipment_data in shipments_data:
            try:
                # Check if shipment already exists
                existing = render_session.query(Shipment).filter_by(tracking_number=shipment_data['tracking_number']).first()
                if existing:
                    print(f"   ⚠️  Skipping {shipment_data['tracking_number']} (already exists)")
                    skipped_shipments += 1
                    continue
                
                shipment = Shipment(**shipment_data)
                render_session.add(shipment)
                imported_shipments += 1
                if imported_shipments % 10 == 0:
                    print(f"   ... imported {imported_shipments} shipments so far")
            except Exception as e:
                print(f"   ❌ Error importing {shipment_data.get('tracking_number', 'unknown')}: {e}")
                render_session.rollback()
        
        render_session.commit()
        print(f"   ✅ Imported {imported_shipments} shipments (skipped {skipped_shipments} duplicates)")
        
        # Import status logs
        print(f"\n   Importing {len(status_logs_data)} status logs...")
        imported_logs = 0
        skipped_logs = 0
        for log_data in status_logs_data:
            try:
                # Check if log already exists
                existing = render_session.query(StatusLog).filter_by(id=log_data['id']).first()
                if existing:
                    skipped_logs += 1
                    continue
                
                log = StatusLog(**log_data)
                render_session.add(log)
                imported_logs += 1
                if imported_logs % 50 == 0:
                    print(f"   ... imported {imported_logs} status logs so far")
            except Exception as e:
                print(f"   ❌ Error importing status log {log_data.get('id', 'unknown')}: {e}")
                render_session.rollback()
        
        render_session.commit()
        print(f"   ✅ Imported {imported_logs} status logs (skipped {skipped_logs} duplicates)")
        
        # Verify
        final_shipments = render_session.query(Shipment).count()
        final_logs = render_session.query(StatusLog).count()
        print(f"\n   ✅ Render database now has: {final_shipments} shipments, {final_logs} status logs")
    finally:
        render_session.close()
        render_engine.dispose()
    
    print("\n" + "=" * 60)
    print("✅ Migration completed successfully!")
    print("=" * 60)
    return True

if __name__ == '__main__':
    try:
        if migrate_to_render():
            print("\n✓ Your data is now on Render!")
            print("   You can now log in and see your shipments on your live site.")
        else:
            print("\n❌ Migration failed. Please check the errors above.")
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
