"""
Migration script to add created_by and created_by_email fields to shipments table
Run this script once to update existing shipments in the database
"""
from models.shipment import db, Shipment
from app import app

def migrate():
    """Add created_by and created_by_email columns to shipments table"""
    with app.app_context():
        try:
            # Check if columns already exist by trying to query them
            try:
                db.session.execute(db.text("SELECT created_by FROM shipments LIMIT 1"))
                print("Columns already exist. Skipping migration.")
                return
            except Exception:
                # Columns don't exist, proceed with migration
                pass
            
            # For SQLite, we need to recreate the table or use ALTER TABLE
            # SQLite has limited ALTER TABLE support, so we'll use a workaround
            print("Adding created_by and created_by_email columns...")
            
            # For SQLite, we need to:
            # 1. Create a new table with the new columns
            # 2. Copy data from old table
            # 3. Drop old table
            # 4. Rename new table
            
            # Check database type
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            
            if 'shipments' in tables:
                # Get column info
                columns = [col['name'] for col in inspector.get_columns('shipments')]
                
                if 'created_by' not in columns or 'created_by_email' not in columns:
                    print("Adding columns using ALTER TABLE...")
                    try:
                        # Try ALTER TABLE (works for PostgreSQL, MySQL)
                        db.session.execute(db.text("ALTER TABLE shipments ADD COLUMN created_by VARCHAR(100)"))
                        db.session.execute(db.text("ALTER TABLE shipments ADD COLUMN created_by_email VARCHAR(100)"))
                        db.session.commit()
                        print("✅ Successfully added created_by and created_by_email columns")
                    except Exception as e:
                        # If ALTER TABLE fails (SQLite), we'll need to recreate the table
                        print(f"ALTER TABLE failed: {e}")
                        print("Attempting SQLite-compatible migration...")
                        
                        # SQLite migration strategy
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
                                pdf_url VARCHAR(200),
                                qr_url VARCHAR(200),
                                created_by VARCHAR(100),
                                created_by_email VARCHAR(100)
                            )
                        """))
                        
                        db.session.execute(db.text("""
                            INSERT INTO shipments_new 
                            SELECT id, tracking_number, sender_name, sender_email, sender_phone,
                                   sender_address, receiver_name, receiver_phone, receiver_address,
                                   package_type, weight, shipment_cost, date_registered,
                                   estimated_delivery_date, status, pdf_url, qr_url,
                                   NULL as created_by, NULL as created_by_email
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

