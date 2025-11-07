"""
Migration script to add current_location field to shipments table
Run this script once to update existing shipments in the database
"""
import sys
import os

# Add the parent directory to the path so we can import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.shipment import db, Shipment
from app import app

def migrate():
    """Add current_location column to shipments table"""
    with app.app_context():
        try:
            # Check if column already exists by trying to query it
            try:
                db.session.execute(db.text("SELECT current_location FROM shipments LIMIT 1"))
                print("Column already exists. Skipping migration.")
                return
            except Exception:
                # Column doesn't exist, proceed with migration
                pass
            
            print("Adding current_location column...")
            
            # Check database type
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            
            if 'shipments' in tables:
                # Get column info
                columns = [col['name'] for col in inspector.get_columns('shipments')]
                
                if 'current_location' not in columns:
                    print("Adding column using ALTER TABLE...")
                    try:
                        # Try ALTER TABLE (works for PostgreSQL, MySQL)
                        db.session.execute(db.text("ALTER TABLE shipments ADD COLUMN current_location VARCHAR(200)"))
                        db.session.commit()
                        print("✅ Successfully added current_location column")
                    except Exception as e:
                        # If ALTER TABLE fails (SQLite), we'll need to recreate the table
                        print(f"ALTER TABLE failed: {e}")
                        print("Attempting SQLite-compatible migration...")
                        
                        # Get all existing columns
                        existing_columns = [col['name'] for col in inspector.get_columns('shipments')]
                        
                        # SQLite migration strategy - recreate table with new column
                        # Build CREATE TABLE statement with all existing columns plus new one
                        db.session.execute(db.text("""
                            CREATE TABLE shipments_new (
                                id VARCHAR(36) PRIMARY KEY,
                                tracking_number VARCHAR(64) UNIQUE NOT NULL,
                                sender_name VARCHAR(100) NOT NULL,
                                sender_email VARCHAR(100) NOT NULL,
                                sender_phone VARCHAR(20) NOT NULL,
                                sender_address VARCHAR(200) NOT NULL,
                                receiver_name VARCHAR(100) NOT NULL,
                                receiver_phone VARCHAR(20) NOT NULL,
                                receiver_address VARCHAR(200) NOT NULL,
                                package_type VARCHAR(50) NOT NULL,
                                weight FLOAT NOT NULL,
                                shipment_cost FLOAT NOT NULL,
                                date_registered DATETIME,
                                estimated_delivery_date DATETIME,
                                status VARCHAR(50) NOT NULL DEFAULT 'Registered',
                                current_location VARCHAR(200),
                                pdf_url VARCHAR(200),
                                qr_url VARCHAR(200),
                                created_by VARCHAR(100),
                                created_by_email VARCHAR(100)
                            )
                        """))
                        
                        # Build INSERT statement with all columns
                        db.session.execute(db.text("""
                            INSERT INTO shipments_new 
                            SELECT id, tracking_number, sender_name, sender_email, sender_phone,
                                   sender_address, receiver_name, receiver_phone, receiver_address,
                                   package_type, weight, shipment_cost, date_registered,
                                   estimated_delivery_date, status,
                                   NULL as current_location,
                                   pdf_url, qr_url, created_by, created_by_email
                            FROM shipments
                        """))
                        
                        db.session.execute(db.text("DROP TABLE shipments"))
                        db.session.execute(db.text("ALTER TABLE shipments_new RENAME TO shipments"))
                        
                        # Recreate indexes
                        db.session.execute(db.text("CREATE UNIQUE INDEX IF NOT EXISTS ix_shipments_tracking_number ON shipments(tracking_number)"))
                        
                        db.session.commit()
                        print("✅ Successfully migrated shipments table with current_location column")
                else:
                    print("Column already exists. Skipping migration.")
            else:
                print("Shipments table does not exist. It will be created with the new column on first use.")
                
        except Exception as e:
            db.session.rollback()
            print(f"❌ Migration failed: {e}")
            raise

if __name__ == '__main__':
    print("Starting migration to add current_location field...")
    migrate()
    print("Migration complete!")

