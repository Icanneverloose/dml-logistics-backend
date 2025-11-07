# Migration: Add current_location Field to Shipments

## Overview
This migration adds the `current_location` field to the `shipments` table. This field stores the latest location from admin status updates, which is then displayed on the public tracking page.

## What Changed

### Backend Changes:
1. **Model Update** (`models/shipment.py`):
   - Added `current_location = db.Column(db.String(200), nullable=True)` field to Shipment model

2. **Status Update Route** (`routes/status.py`):
   - Already updates `shipment.current_location = location` when status is updated ✅
   - Already creates StatusLog entry (adds to timeline) ✅

3. **Migration Script** (`migrations/add_current_location_field.py`):
   - Adds the `current_location` column to existing databases
   - Handles both SQLite and PostgreSQL/MySQL databases

## How to Run the Migration

### Option 1: Run the migration script directly
```bash
cd backend
python migrations/add_current_location_field.py
```

### Option 2: Run from Python
```python
from migrations.add_current_location_field import migrate
from app import app

with app.app_context():
    migrate()
```

## How It Works

1. **When Admin Updates Status:**
   - Admin enters new status and location in the "Update Location / Status" modal
   - Backend receives: `{ status, location, coordinates, note, timestamp }`
   - Backend creates a new `StatusLog` entry (adds to timeline)
   - Backend updates `shipment.current_location = location`
   - Backend updates `shipment.status = status`
   - All changes are committed to database

2. **When Public User Tracks Shipment:**
   - Frontend fetches status history via `/api/shipments/{trackingNumber}/status`
   - Frontend extracts the last location from the timeline/history
   - Frontend displays it as "Current Location" on tracking page
   - Timeline shows all status updates in chronological order

## Frontend Integration

The frontend has been updated to:
- ✅ Read `current_location` from shipment data
- ✅ Extract last location from status history/timeline
- ✅ Display it in the tracking results
- ✅ Never use `sender_address` as current location

## Testing

After running the migration:
1. Update a shipment's status with a new location from admin dashboard
2. Check that `current_location` is saved in the database
3. Check that the location appears in the status history/timeline
4. View the shipment on the public tracking page
5. Verify "Current Location" shows the latest location from admin updates

## Notes

- The `current_location` field is nullable, so existing shipments without location updates will have `NULL`
- The first status update will set the `current_location`
- The location is always taken from the most recent status update, not from sender/receiver addresses

