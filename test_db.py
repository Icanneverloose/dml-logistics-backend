#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models.shipment import Shipment

def test_database():
    with app.app_context():
        try:
            # Test database connection
            print("Testing database connection...")
            db.engine.execute('SELECT 1')
            print("✅ Database connection successful")
            
            # Test Shipment model
            print("Testing Shipment model...")
            shipments = Shipment.query.all()
            print(f"✅ Found {len(shipments)} existing shipments")
            
            # Test creating a shipment
            print("Testing shipment creation...")
            test_shipment = Shipment(
                tracking_number="TEST123",
                sender_name="Test Sender",
                sender_email="test@example.com",
                sender_phone="1234567890",
                sender_address="Test Address",
                receiver_name="Test Receiver",
                receiver_phone="0987654321",
                receiver_address="Test Address",
                package_type="Test Package",
                weight=1.0,
                shipment_cost=100.0,
                status='Registered'
            )
            
            db.session.add(test_shipment)
            db.session.commit()
            print("✅ Test shipment created successfully")
            
            # Clean up
            db.session.delete(test_shipment)
            db.session.commit()
            print("✅ Test shipment cleaned up")
            
        except Exception as e:
            print(f"❌ Database test failed: {e}")
            return False
    
    return True

if __name__ == "__main__":
    test_database()
