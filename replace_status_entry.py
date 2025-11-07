"""
Script to replace/update a specific status log entry
"""
import sys
import os
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
from models.shipment import db, Shipment
from models.status_log import StatusLog

def parse_date_string(date_str):
    """Parse date string in various formats"""
    date_str = date_str.strip()
    
    formats = [
        "%d/%B/%Y",      # 06/November/2025
        "%d/%b/%Y",      # 06/Nov/2025
        "%Y-%m-%d %H:%M:%S",  # 2025-11-06 19:45:00
        "%Y-%m-%d",      # 2025-11-06
        "%B, %d %Y",     # November, 6 2025
        "%B %d, %Y",     # November 6, 2025
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    
    raise ValueError(f"Could not parse date: {date_str}")

def replace_status_entry(tracking_number, old_date_str, new_status, new_location, new_date_str, new_time_str):
    """
    Replace a status log entry with new details
    
    Args:
        tracking_number: The shipment tracking number
        old_date_str: Date string to find the old entry (for matching)
        new_status: New status
        new_location: New location
        new_date_str: New date string
        new_time_str: New time string (HH:MM:SS format)
    """
    with app.app_context():
        # Find the shipment
        shipment = Shipment.query.filter_by(tracking_number=tracking_number).first()
        
        if not shipment:
            print(f"❌ Shipment {tracking_number} not found!")
            return False
        
        print(f"📦 Found shipment: {tracking_number}")
        
        # Parse old date to find the entry (approximate match)
        try:
            old_date = parse_date_string(old_date_str)
            print(f"🔍 Looking for entry around: {old_date}")
        except:
            old_date = None
        
        # Find status logs for this shipment
        logs = StatusLog.query.filter_by(shipment_id=shipment.id).order_by(StatusLog.timestamp.desc()).all()
        
        # Try to find the entry to replace
        entry_to_replace = None
        if old_date:
            for log in logs:
                # Check if timestamp is close (within 24 hours)
                if log.timestamp and abs((log.timestamp - old_date.replace(tzinfo=None)).total_seconds()) < 86400:
                    if "Yasser Arafat" in (log.location or "") or "Gaza" in (log.location or ""):
                        entry_to_replace = log
                        print(f"📝 Found entry to replace: {log.status} at {log.location} on {log.timestamp}")
                        break
        
        # If not found by date, try to find by location
        if not entry_to_replace:
            for log in logs:
                if log.location and ("Yasser Arafat" in log.location or ("Gaza" in log.location and log.status == "Registered")):
                    entry_to_replace = log
                    print(f"📝 Found entry to replace by location: {log.status} at {log.location} on {log.timestamp}")
                    break
        
        # Parse new date/time
        try:
            new_date = parse_date_string(new_date_str)
            
            # Add time
            if new_time_str:
                time_parts = new_time_str.split(':')
                if len(time_parts) >= 2:
                    new_date = new_date.replace(
                        hour=int(time_parts[0]),
                        minute=int(time_parts[1]),
                        second=int(time_parts[2]) if len(time_parts) > 2 else 0
                    )
            
            # Convert to UTC
            timestamp = new_date.replace(tzinfo=timezone.utc).replace(tzinfo=None)
            print(f"📅 New date/time: {timestamp}")
            
        except ValueError as e:
            print(f"❌ Error parsing new date/time: {e}")
            return False
        
        # Delete old entry if found
        if entry_to_replace:
            print(f"🗑️  Deleting old entry...")
            db.session.delete(entry_to_replace)
        
        # Create new entry
        new_log = StatusLog(
            shipment_id=shipment.id,
            status=new_status,
            timestamp=timestamp,
            location=new_location,
            note=None
        )
        
        # Update shipment
        shipment.status = new_status
        shipment.current_location = new_location
        
        # Save to database
        try:
            db.session.add(new_log)
            db.session.commit()
            
            print(f"\n✅ Successfully replaced status entry!")
            print(f"   Tracking Number: {tracking_number}")
            print(f"   Status: {new_status}")
            print(f"   Location: {new_location}")
            print(f"   Date/Time: {timestamp.strftime('%Y-%m-%d %H:%M:%S')} UTC")
            print(f"   Local equivalent: {new_date.strftime('%B %d, %Y at %I:%M %p')}")
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error saving to database: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == '__main__':
    if len(sys.argv) < 6:
        print("Usage: python replace_status_entry.py TRACKING_NUMBER OLD_DATE NEW_STATUS NEW_LOCATION NEW_DATE NEW_TIME")
        print('\nExample:')
        print('  python replace_status_entry.py "TRKADDA03C7" "November 7, 2025" "At Facility" "Gaza, Palestine" "November 6, 2025" "19:45:00"')
        sys.exit(1)
    
    tracking_number = sys.argv[1]
    old_date = sys.argv[2]
    new_status = sys.argv[3]
    new_location = sys.argv[4]
    new_date = sys.argv[5]
    new_time = sys.argv[6] if len(sys.argv) > 6 else "19:45:00"
    
    if replace_status_entry(tracking_number, old_date, new_status, new_location, new_date, new_time):
        print("\n✓ Done!")
    else:
        sys.exit(1)

