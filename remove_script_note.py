"""
Script to remove the "Updated via script" note from status logs
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
from models.shipment import db, Shipment
from models.status_log import StatusLog

def remove_script_notes(tracking_number):
    """Remove notes containing 'Updated via script' from status logs"""
    with app.app_context():
        # Find the shipment
        shipment = Shipment.query.filter_by(tracking_number=tracking_number).first()
        
        if not shipment:
            print(f"❌ Shipment {tracking_number} not found!")
            return False
        
        # Find all status logs for this shipment with script notes
        logs = StatusLog.query.filter_by(shipment_id=shipment.id).all()
        updated_count = 0
        
        for log in logs:
            if log.note and "Updated via script" in log.note:
                print(f"📝 Removing note from log: {log.status} at {log.timestamp}")
                log.note = None
                updated_count += 1
        
        if updated_count > 0:
            try:
                db.session.commit()
                print(f"\n✅ Removed notes from {updated_count} status log(s)")
                return True
            except Exception as e:
                db.session.rollback()
                print(f"❌ Error: {e}")
                return False
        else:
            print("ℹ️  No notes found to remove")
            return True

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python remove_script_note.py TRACKING_NUMBER")
        print('Example: python remove_script_note.py "TRKC92028DE"')
        sys.exit(1)
    
    tracking_number = sys.argv[1]
    if remove_script_notes(tracking_number):
        print("✓ Done!")
    else:
        sys.exit(1)

