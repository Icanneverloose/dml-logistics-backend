"""
Add soft delete functionality to shipments
Run this script to add deleted_at column for soft deletes
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db
from sqlalchemy import text

def migrate():
    """Add deleted_at column to shipments table"""
    print("=" * 60)
    print("🔄 Adding Soft Delete Support to Shipments")
    print("=" * 60)
    
    with app.app_context():
        try:
            # Check if column already exists
            result = db.session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='shipments' AND column_name='deleted_at'
            """))
            
            if result.fetchone():
                print("✅ Column 'deleted_at' already exists")
                return True
            
            # Add deleted_at column
            print("   Adding 'deleted_at' column to shipments table...")
            db.session.execute(text("""
                ALTER TABLE shipments 
                ADD COLUMN deleted_at TIMESTAMP NULL
            """))
            db.session.commit()
            print("✅ Added 'deleted_at' column to shipments table")
            print("\n💡 Note: To use soft delete, update your delete endpoint")
            print("   to set deleted_at instead of deleting the record.")
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == '__main__':
    migrate()

