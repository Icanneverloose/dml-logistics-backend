"""
Quick script to fix the timestamp for a specific status log entry
"""
import sys
import os
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
from models.shipment import db, Shipment
from models.status_log import StatusLog

def fix_timestamp(tracking_number, status, new_datetime_str):
    """Update the timestamp for the most recent status log with the given status"""
    with app.app_context():
        shipment = Shipment.query.filter_by(tracking_number=tracking_number).first()
        
        if not shipment:
            print(f"❌ Shipment {tracking_number} not found!")
            return False
        
        # Find the most recent status log with the given status
        logs = StatusLog.query.filter_by(
            shipment_id=shipment.id,
            status=status
        ).order_by(StatusLog.timestamp.desc()).all()
        
        if not logs:
            print(f"❌ No status log found with status '{status}'")
            return False
        
        # Update the most recent one
        log = logs[0]
        
        # Parse the datetime string
        try:
            # Try parsing "2025-11-06 22:30:00" format
            dt = datetime.strptime(new_datetime_str, "%Y-%m-%d %H:%M:%S")
            timestamp = dt.replace(tzinfo=timezone.utc).replace(tzinfo=None)
        except ValueError:
            print(f"❌ Error parsing datetime: {new_datetime_str}")
            return False
        
        print(f"📝 Updating status log:")
        print(f"   Old timestamp: {log.timestamp}")
        print(f"   New timestamp: {timestamp}")
        
        log.timestamp = timestamp
        
        try:
            db.session.commit()
            print(f"\n✅ Successfully updated timestamp!")
            return True
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error: {e}")
            return False

if __name__ == '__main__':
    if len(sys.argv) < 4:
        print("Usage: python fix_shipment_time.py TRACKING_NUMBER STATUS 'YYYY-MM-DD HH:MM:SS'")
        print('Example: python fix_shipment_time.py "TRKADDA03C7" "In Transit" "2025-11-06 22:30:00"')
        sys.exit(1)
    
    tracking_number = sys.argv[1]
    status = sys.argv[2]
    datetime_str = sys.argv[3]
    
    if fix_timestamp(tracking_number, status, datetime_str):
        print("✓ Done!")
    else:
        sys.exit(1)

