"""
Script to update a shipment's status with custom date/time
Usage: python update_shipment_date.py TRACKING_NUMBER "YYYY-MM-DD HH:MM:SS" "Location Name" [Status]
"""
import sys
import os
from datetime import datetime, timezone

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
from models.shipment import db, Shipment
from models.status_log import StatusLog

def parse_date_string(date_str):
    """
    Parse various date formats and return datetime object
    Supports:
    - "06/November/2025" or "06/Nov/2025"
    - "2025-11-06"
    - "2025-11-06 09:00:00"
    """
    date_str = date_str.strip()
    
    # Try parsing different formats
    formats = [
        "%d/%B/%Y",      # 06/November/2025
        "%d/%b/%Y",      # 06/Nov/2025
        "%Y-%m-%d %H:%M:%S",  # 2025-11-06 09:00:00
        "%Y-%m-%d",      # 2025-11-06
        "%d/%m/%Y",      # 06/11/2025
        "%m/%d/%Y",      # 11/06/2025
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    
    raise ValueError(f"Could not parse date: {date_str}")

def update_shipment_date(tracking_number, date_time_str, location, status="Registered", time_str="09:00:00"):
    """
    Update shipment status with custom date/time
    
    Args:
        tracking_number: The shipment tracking number
        date_time_str: Date string (various formats supported)
        location: Location name
        status: Status (default: "Registered")
        time_str: Time string in format "HH:MM:SS" (default: "09:00:00")
    """
    with app.app_context():
        # Find the shipment
        shipment = Shipment.query.filter_by(tracking_number=tracking_number).first()
        
        if not shipment:
            print(f"❌ Shipment {tracking_number} not found!")
            return False
        
        print(f"📦 Found shipment: {tracking_number}")
        print(f"   Current status: {shipment.status}")
        print(f"   Current location: {shipment.current_location}")
        
        # Parse the date
        try:
            date_obj = parse_date_string(date_time_str)
            
            # If time is provided separately, combine them
            if time_str:
                time_parts = time_str.split(':')
                if len(time_parts) >= 2:
                    date_obj = date_obj.replace(
                        hour=int(time_parts[0]),
                        minute=int(time_parts[1]),
                        second=int(time_parts[2]) if len(time_parts) > 2 else 0
                    )
            
            # Convert to UTC (treating input as local time, then convert to UTC)
            # For simplicity, we'll treat it as UTC since the backend expects UTC
            timestamp = date_obj.replace(tzinfo=timezone.utc).replace(tzinfo=None)
            
            print(f"📅 Parsed date/time: {date_obj}")
            print(f"📅 Storing as UTC: {timestamp}")
            
        except ValueError as e:
            print(f"❌ Error parsing date/time: {e}")
            print("   Supported formats:")
            print("   - 06/November/2025")
            print("   - 2025-11-06")
            print("   - 2025-11-06 09:00:00")
            return False
        
        # Create new status log entry
        status_log = StatusLog(
            shipment_id=shipment.id,
            status=status,
            timestamp=timestamp,
            location=location,
            note=None  # No note added
        )
        
        # Update shipment
        shipment.status = status
        shipment.current_location = location
        
        # Save to database
        try:
            db.session.add(status_log)
            db.session.commit()
            
            print(f"\n✅ Successfully updated shipment!")
            print(f"   Tracking Number: {tracking_number}")
            print(f"   Status: {status}")
            print(f"   Location: {location}")
            print(f"   Date/Time: {timestamp.strftime('%Y-%m-%d %H:%M:%S')} UTC")
            print(f"   Local equivalent: {date_obj.strftime('%B %d, %Y at %I:%M %p')}")
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error saving to database: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == '__main__':
    if len(sys.argv) < 4:
        print("Usage: python update_shipment_date.py TRACKING_NUMBER 'DATE' 'Location Name' [Status] [Time]")
        print("\nExamples:")
        print('  python update_shipment_date.py "TRKC92028DE" "06/November/2025" "Home" "Registered"')
        print('  python update_shipment_date.py "TRKC92028DE" "2025-11-06" "Home" "Registered" "09:00:00"')
        print('\nDate formats supported:')
        print('  - 06/November/2025')
        print('  - 2025-11-06')
        print('  - 2025-11-06 09:00:00')
        sys.exit(1)
    
    tracking_number = sys.argv[1]
    date_str = sys.argv[2]
    location = sys.argv[3]
    status = sys.argv[4] if len(sys.argv) > 4 else "Registered"
    time_str = sys.argv[5] if len(sys.argv) > 5 else "09:00:00"
    
    if update_shipment_date(tracking_number, date_str, location, status, time_str):
        print("\n✓ Done! The shipment has been updated.")
    else:
        sys.exit(1)

