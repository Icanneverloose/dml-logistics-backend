"""
Migration script to add created_by and created_by_email fields to shipments table
Run this script once to update existing shipments in the database
"""
import sys
import os

# Add the parent directory to the path so we can import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.shipment import db, Shipment
from app import app

def migrate():
    """Add created_by and created_by_email columns to shipments table"""
    with app.app_context():
        try:
            # Check if columns already exist
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            
            if 'shipments' not in tables:
                print("Shipments table does not exist. It will be created with all columns on first use.")
                return
            
            columns = [col['name'] for col in inspector.get_columns('shipments')]
            if 'created_by' in columns and 'created_by_email' in columns and 'current_location' in columns:
                print("All columns already exist. Skipping migration.")
                return
            
            # For SQLite, we need to recreate the table or use ALTER TABLE
            # SQLite has limited ALTER TABLE support, so we'll use a workaround
            print("Adding missing columns to shipments table...")
            
            if 'shipments' in tables:
                # Get column info
                columns = [col['name'] for col in inspector.get_columns('shipments')]
                
                missing_columns = []
                if 'created_by' not in columns:
                    missing_columns.append('created_by')
                if 'created_by_email' not in columns:
                    missing_columns.append('created_by_email')
                if 'current_location' not in columns:
                    missing_columns.append('current_location')
                
                if missing_columns:
                    print(f"Adding columns using ALTER TABLE: {', '.join(missing_columns)}...")
                    try:
                        # Try ALTER TABLE (works for PostgreSQL, MySQL)
                        if 'current_location' in missing_columns:
                            db.session.execute(db.text("ALTER TABLE shipments ADD COLUMN current_location VARCHAR(200)"))
                        if 'created_by' in missing_columns:
                            db.session.execute(db.text("ALTER TABLE shipments ADD COLUMN created_by VARCHAR(100)"))
                        if 'created_by_email' in missing_columns:
                            db.session.execute(db.text("ALTER TABLE shipments ADD COLUMN created_by_email VARCHAR(100)"))
                        db.session.commit()
                        print(f"✅ Successfully added columns: {', '.join(missing_columns)}")
                    except Exception as e:
                        # If ALTER TABLE fails (SQLite), we'll need to recreate the table
                        print(f"ALTER TABLE failed: {e}")
                        print("Attempting SQLite-compatible migration...")
                        
                        # SQLite migration strategy - include all columns including current_location
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
                        
                        # Build dynamic SELECT statement based on existing columns
                        existing_columns = [col['name'] for col in inspector.get_columns('shipments')]
                        
                        # Select all existing columns, and add NULL for missing ones
                        select_parts = []
                        for col in ['id', 'tracking_number', 'sender_name', 'sender_email', 'sender_phone',
                                   'sender_address', 'receiver_name', 'receiver_phone', 'receiver_address',
                                   'package_type', 'weight', 'shipment_cost', 'date_registered',
                                   'estimated_delivery_date', 'status']:
                            if col in existing_columns:
                                select_parts.append(col)
                            else:
                                select_parts.append(f"NULL as {col}")
                        
                        # Handle optional columns
                        if 'current_location' in existing_columns:
                            select_parts.append('current_location')
                        else:
                            select_parts.append('NULL as current_location')
                        
                        if 'pdf_url' in existing_columns:
                            select_parts.append('pdf_url')
                        else:
                            select_parts.append('NULL as pdf_url')
                        
                        if 'qr_url' in existing_columns:
                            select_parts.append('qr_url')
                        else:
                            select_parts.append('NULL as qr_url')
                        
                        # Add created_by fields (will be NULL)
                        select_parts.append('NULL as created_by')
                        select_parts.append('NULL as created_by_email')
                        
                        select_statement = ', '.join(select_parts)
                        
                        db.session.execute(db.text(f"""
                            INSERT INTO shipments_new 
                            SELECT {select_statement}
                            FROM shipments
                        """))
                        
                        db.session.execute(db.text("DROP TABLE shipments"))
                        db.session.execute(db.text("ALTER TABLE shipments_new RENAME TO shipments"))
                        
                        # Recreate indexes
                        db.session.execute(db.text("CREATE UNIQUE INDEX IF NOT EXISTS ix_shipments_tracking_number ON shipments(tracking_number)"))
                        
                        db.session.commit()
                        print("✅ Successfully migrated shipments table with new columns")
                else:
                    print("Columns already exist. Skipping migration.")
            else:
                print("Shipments table does not exist. It will be created with the new columns on first use.")
                
        except Exception as e:
            db.session.rollback()
            print(f"❌ Migration failed: {e}")
            raise

if __name__ == '__main__':
    print("Starting migration...")
    migrate()
    print("Migration complete!")

