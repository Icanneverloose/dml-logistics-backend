"""
Simple script to run the migration
Usage: python run_migration.py
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from migrations.add_created_by_fields import migrate
from app import app

if __name__ == '__main__':
    print("=" * 50)
    print("Migration: Add created_by fields to shipments")
    print("=" * 50)
    try:
        migrate()
        print("\n✅ Migration completed successfully!")
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

